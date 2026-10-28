"""Persistenza SQLite: eventi, fonti, prezzi, analisi, sintesi IA, sessioni e spesa.

Ogni operazione apre una connessione breve: il modulo è sicuro da usare da più thread
(richieste HTTP e job in background). I risultati delle analisi sono salvati come JSON
immutabile, così riaprire un'analisi restituisce esattamente lo stesso risultato.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path

from ..domain.events import Event, Source
from ..domain.sessions import PriceBar
from ..errors import NotFound, PersistenceError

SCHEMA_VERSION = 3

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    tags TEXT NOT NULL,
    occurred_on TEXT NOT NULL,
    occurred_at TEXT,
    time_precision TEXT NOT NULL,
    origin TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_by_date ON events(occurred_on);
CREATE TABLE IF NOT EXISTS sources (
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    url TEXT NOT NULL,
    publisher TEXT NOT NULL,
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    accessed_on TEXT,
    PRIMARY KEY (event_id, position)
);
CREATE TABLE IF NOT EXISTS prices (
    market TEXT NOT NULL,
    date TEXT NOT NULL,
    open REAL, high REAL, low REAL, close REAL, volume REAL,
    PRIMARY KEY (market, date)
);
CREATE TABLE IF NOT EXISTS price_sync (
    market TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    first_date TEXT NOT NULL,
    last_date TEXT NOT NULL,
    fetched_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    method_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error_code TEXT,
    error_message TEXT,
    result TEXT
);
CREATE INDEX IF NOT EXISTS analyses_by_event ON analyses(event_id, created_at);
CREATE TABLE IF NOT EXISTS summaries (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    model TEXT,
    prompt_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    content TEXT,
    usage TEXT,
    error_code TEXT,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS summaries_by_analysis ON summaries(analysis_id, created_at);
CREATE TABLE IF NOT EXISTS operator_sessions (
    token_hash TEXT PRIMARY KEY,
    csrf_token TEXT NOT NULL,
    epoch TEXT NOT NULL,
    credential TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_attempts (
    id INTEGER PRIMARY KEY,
    client TEXT NOT NULL,
    success INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS login_attempts_by_time ON login_attempts(created_at);
CREATE TABLE IF NOT EXISTS spend_ledger (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    purpose TEXT NOT NULL,
    ref_id TEXT,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL,
    reserved_micros INTEGER NOT NULL,
    actual_micros INTEGER,
    usage TEXT,
    note TEXT,
    created_at TEXT NOT NULL,
    settled_at TEXT
);
CREATE INDEX IF NOT EXISTS spend_by_time ON spend_ledger(created_at);
CREATE TABLE IF NOT EXISTS budget_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS news_searches (
    id TEXT PRIMARY KEY,
    params TEXT NOT NULL,
    cache_key TEXT NOT NULL,
    normalization_version TEXT NOT NULL,
    status TEXT NOT NULL,
    stage TEXT,
    requests TEXT,
    warnings TEXT,
    excluded TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS news_searches_by_key ON news_searches(cache_key, created_at);
CREATE TABLE IF NOT EXISTS news_results (
    search_id TEXT NOT NULL REFERENCES news_searches(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    data TEXT NOT NULL,
    PRIMARY KEY (search_id, idx)
);
CREATE TABLE IF NOT EXISTS news_events (
    search_id TEXT NOT NULL REFERENCES news_searches(id) ON DELETE CASCADE,
    idx INTEGER NOT NULL,
    data TEXT NOT NULL,
    event_id TEXT,
    analysis_id TEXT,
    PRIMARY KEY (search_id, idx)
);
"""

# Importo che una voce di spesa impegna nel budget: il costo confermato quando noto,
# altrimenti l'intera riserva (anche quando l'esito della chiamata è incerto).
SPEND_COMMITTED = """CASE status WHEN 'released' THEN 0
                     WHEN 'confirmed' THEN COALESCE(actual_micros, reserved_micros)
                     ELSE reserved_micros END"""

ACTIVE_STATUSES = ("queued", "running")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _event_from_rows(row: sqlite3.Row, sources: list[sqlite3.Row]) -> Event:
    return Event(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        category=row["category"],
        tags=tuple(json.loads(row["tags"])),
        occurred_on=date.fromisoformat(row["occurred_on"]),
        occurred_at=datetime.fromisoformat(row["occurred_at"]) if row["occurred_at"] else None,
        time_precision=row["time_precision"],
        origin=row["origin"],
        public=bool(row["public"]),
        sources=tuple(
            Source(
                url=s["url"], publisher=s["publisher"], title=s["title"], kind=s["kind"],
                accessed_on=date.fromisoformat(s["accessed_on"]) if s["accessed_on"] else None,
                published_on=date.fromisoformat(s["published_on"]) if s["published_on"] else None,
            )
            for s in sources
        ),
    )


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        try:
            conn = sqlite3.connect(self.path, timeout=15)
        except sqlite3.Error as exc:
            raise PersistenceError("Archivio non accessibile") from exc
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        except sqlite3.Error as exc:
            raise PersistenceError("Errore dell'archivio") from exc
        finally:
            conn.close()

    @contextmanager
    def immediate(self) -> Iterator[sqlite3.Connection]:
        """Transazione con lock di scrittura acquisito subito: serializza le decisioni
        "controlla e poi scrivi" tra thread e processi che usano lo stesso file."""
        with self.connect() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.Error as exc:
                raise PersistenceError("Archivio non accessibile") from exc
            yield conn

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
            row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
            columns = {r["name"] for r in conn.execute("PRAGMA table_info(events)")}
            if "public" not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN public INTEGER NOT NULL DEFAULT 0")
                # Migrazione da v1: il catalogo curato era già l'insieme dei casi dimostrativi;
                # gli eventi inseriti dagli utenti restano privati.
                conn.execute("UPDATE events SET public = 1 WHERE origin = 'curated'")
            source_columns = {r["name"] for r in conn.execute("PRAGMA table_info(sources)")}
            if "published_on" not in source_columns:
                conn.execute("ALTER TABLE sources ADD COLUMN published_on TEXT")
            if row is None:
                conn.execute("INSERT INTO meta(key, value) VALUES ('schema_version', ?)",
                             (str(SCHEMA_VERSION),))
            elif int(row["value"]) < SCHEMA_VERSION:
                conn.execute("UPDATE meta SET value = ? WHERE key = 'schema_version'",
                             (str(SCHEMA_VERSION),))

    def instance_secret(self) -> str:
        """Segreto casuale dell'istanza, generato una volta e conservato nel volume."""
        with self.immediate() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'instance_secret'").fetchone()
            if row:
                return row["value"]
            value = secrets.token_hex(32)
            conn.execute("INSERT INTO meta(key, value) VALUES ('instance_secret', ?)", (value,))
            return value

    def check(self) -> None:
        with self.connect() as conn:
            conn.execute("SELECT 1 FROM meta LIMIT 1").fetchone()

    # --- Eventi ---------------------------------------------------------------------------

    def upsert_event(self, event: Event) -> None:
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO events (id, title, description, category, tags, occurred_on,
                                       occurred_at, time_precision, origin, created_at, public)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET title=excluded.title,
                     description=excluded.description, category=excluded.category,
                     tags=excluded.tags, occurred_on=excluded.occurred_on,
                     occurred_at=excluded.occurred_at, time_precision=excluded.time_precision,
                     public=excluded.public""",
                (event.id, event.title, event.description, event.category, json.dumps(event.tags),
                 event.occurred_on.isoformat(),
                 event.occurred_at.isoformat() if event.occurred_at else None,
                 event.time_precision, event.origin, utc_now(), int(event.public)),
            )
            conn.execute("DELETE FROM sources WHERE event_id = ?", (event.id,))
            conn.executemany(
                "INSERT INTO sources (event_id, position, url, publisher, title, kind, accessed_on, "
                "published_on) VALUES (?,?,?,?,?,?,?,?)",
                [(event.id, i, s.url, s.publisher, s.title, s.kind,
                  s.accessed_on.isoformat() if s.accessed_on else None,
                  s.published_on.isoformat() if s.published_on else None)
                 for i, s in enumerate(event.sources)],
            )

    def event_exists(self, event_id: str) -> bool:
        with self.connect() as conn:
            return conn.execute("SELECT 1 FROM events WHERE id = ?", (event_id,)).fetchone() is not None

    def get_event(self, event_id: str) -> Event:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
            if row is None:
                raise NotFound("Evento non trovato")
            sources = conn.execute(
                "SELECT * FROM sources WHERE event_id = ? ORDER BY position", (event_id,)
            ).fetchall()
        return _event_from_rows(row, sources)

    def set_event_public(self, event_id: str, public: bool) -> None:
        with self.connect() as conn:
            if conn.execute("UPDATE events SET public = ? WHERE id = ?",
                            (int(public), event_id)).rowcount == 0:
                raise NotFound("Evento non trovato")

    def all_events(self, *, public_only: bool = False) -> list[Event]:
        where = " WHERE public = 1" if public_only else ""
        with self.connect() as conn:
            rows = conn.execute(f"SELECT * FROM events{where} ORDER BY occurred_on").fetchall()
            sources = conn.execute("SELECT * FROM sources ORDER BY event_id, position").fetchall()
        by_event: dict[str, list] = {}
        for s in sources:
            by_event.setdefault(s["event_id"], []).append(s)
        return [_event_from_rows(r, by_event.get(r["id"], [])) for r in rows]

    # --- Prezzi ---------------------------------------------------------------------------

    def save_prices(self, market: str, bars: list[PriceBar], *, provider: str) -> None:
        if not bars:
            return
        with self.connect() as conn:
            conn.executemany(
                """INSERT INTO prices VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(market, date) DO UPDATE SET open=excluded.open,
                     high=excluded.high, low=excluded.low, close=excluded.close,
                     volume=excluded.volume""",
                [(market, b.date.isoformat(), b.open, b.high, b.low, b.close, b.volume)
                 for b in bars],
            )
            first = conn.execute("SELECT MIN(date), MAX(date) FROM prices WHERE market = ?",
                                 (market,)).fetchone()
            conn.execute(
                """INSERT INTO price_sync VALUES (?,?,?,?,?)
                   ON CONFLICT(market) DO UPDATE SET provider=excluded.provider,
                     first_date=excluded.first_date, last_date=excluded.last_date,
                     fetched_at=excluded.fetched_at""",
                (market, provider, first[0], first[1], utc_now()),
            )

    def price_sync(self, market: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM price_sync WHERE market = ?", (market,)).fetchone()
        return dict(row) if row else None

    def get_prices(self, market: str, start: date | None = None, end: date | None = None) -> list[PriceBar]:
        query, params = "SELECT * FROM prices WHERE market = ?", [market]
        if start:
            query += " AND date >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND date <= ?"
            params.append(end.isoformat())
        with self.connect() as conn:
            rows = conn.execute(query + " ORDER BY date", params).fetchall()
        return [PriceBar(date.fromisoformat(r["date"]), r["open"], r["high"], r["low"], r["close"],
                         r["volume"]) for r in rows]

    # --- Analisi --------------------------------------------------------------------------

    @staticmethod
    def _active_job_count(conn: sqlite3.Connection) -> int:
        analyses = conn.execute(
            "SELECT COUNT(*) FROM analyses WHERE status IN ('queued','running')").fetchone()[0]
        summaries = conn.execute(
            "SELECT COUNT(*) FROM summaries WHERE status IN ('queued','running')").fetchone()[0]
        searches = conn.execute(
            "SELECT COUNT(*) FROM news_searches WHERE status IN ('queued','running')").fetchone()[0]
        return analyses + summaries + searches

    def active_job_count(self) -> int:
        with self.connect() as conn:
            return self._active_job_count(conn)

    def create_analysis(self, event_id: str, method_version: str, *,
                        exclusive: bool = False) -> str | None:
        """Con `exclusive` crea il job solo se nessun altro job esterno è in coda o in corso
        (controllo e inserimento nella stessa transazione). Restituisce None se occupato."""
        analysis_id = uuid.uuid4().hex
        with self.immediate() as conn:
            if exclusive and self._active_job_count(conn):
                return None
            conn.execute(
                "INSERT INTO analyses (id, event_id, status, method_version, created_at) "
                "VALUES (?,?,?,?,?)",
                (analysis_id, event_id, "queued", method_version, utc_now()),
            )
        return analysis_id

    def mark_analysis_running(self, analysis_id: str) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE analyses SET status='running', started_at=? WHERE id=?",
                         (utc_now(), analysis_id))

    def finish_analysis(self, analysis_id: str, result: dict) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE analyses SET status='succeeded', finished_at=?, result=?, "
                "error_code=NULL, error_message=NULL WHERE id=?",
                (utc_now(), json.dumps(result, separators=(",", ":")), analysis_id),
            )

    def fail_analysis(self, analysis_id: str, code: str, message: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE analyses SET status='failed', finished_at=?, error_code=?, error_message=? "
                "WHERE id=?",
                (utc_now(), code, message, analysis_id),
            )

    def fail_interrupted_jobs(self) -> int:
        """Al riavvio, i job rimasti in coda o in esecuzione non hanno più un esecutore."""
        message = "Interrotta da un riavvio del server: avviare di nuovo l'analisi."
        with self.connect() as conn:
            n = conn.execute(
                "UPDATE analyses SET status='failed', finished_at=?, error_code='interrupted', "
                "error_message=? WHERE status IN ('queued','running')", (utc_now(), message),
            ).rowcount
            n += conn.execute(
                "UPDATE summaries SET status='failed', finished_at=?, error_code='interrupted', "
                "error_message=? WHERE status IN ('queued','running')", (utc_now(), message),
            ).rowcount
            n += conn.execute(
                "UPDATE news_searches SET status='failed', finished_at=?, error_code='interrupted', "
                "error_message='Ricerca interrotta da un riavvio del server: avviarla di nuovo.' "
                "WHERE status IN ('queued','running')", (utc_now(),),
            ).rowcount
        return n

    def get_analysis(self, analysis_id: str) -> dict:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        if row is None:
            raise NotFound("Analisi non trovata")
        data = dict(row)
        data["result"] = json.loads(data["result"]) if data["result"] else None
        return data

    def latest_analysis_for_event(self, event_id: str, *, succeeded_only: bool = False) -> dict | None:
        query = "SELECT id FROM analyses WHERE event_id = ?"
        if succeeded_only:
            query += " AND status = 'succeeded'"
        with self.connect() as conn:
            row = conn.execute(query + " ORDER BY created_at DESC, rowid DESC LIMIT 1",
                               (event_id,)).fetchone()
        return self.get_analysis(row["id"]) if row else None

    def list_analyses(self, *, q: str | None, category: str | None, status: str | None,
                      date_from: date | None, date_to: date | None, page: int,
                      page_size: int, public_only: bool = True) -> tuple[list[dict], int]:
        where, params = ["1=1"], []
        if public_only:
            where.append("e.public = 1")
        if q:
            where.append("(e.title LIKE ? OR e.description LIKE ? OR e.tags LIKE ?)")
            like = f"%{q}%"
            params += [like, like, like]
        if category:
            where.append("e.category = ?")
            params.append(category)
        if status:
            where.append("a.status = ?")
            params.append(status)
        if date_from:
            where.append("e.occurred_on >= ?")
            params.append(date_from.isoformat())
        if date_to:
            where.append("e.occurred_on <= ?")
            params.append(date_to.isoformat())
        clause = " AND ".join(where)
        base = f"FROM analyses a JOIN events e ON e.id = a.event_id WHERE {clause}"
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
            rows = conn.execute(
                f"""SELECT a.id, a.status, a.method_version, a.created_at, a.finished_at,
                           a.error_code, a.error_message, e.id AS event_id, e.title, e.category,
                           e.occurred_on, e.time_precision, e.public,
                           (SELECT COUNT(*) FROM sources s WHERE s.event_id = e.id) AS source_count
                    {base} ORDER BY e.occurred_on DESC, a.created_at DESC LIMIT ? OFFSET ?""",
                params + [page_size, (page - 1) * page_size],
            ).fetchall()
        items = [dict(r) for r in rows]
        for item in items:
            item["public"] = bool(item["public"])
        return items, total

    def list_events_with_latest(self, *, q: str | None, category: str | None, page: int,
                                page_size: int, public_only: bool = True) -> tuple[list[dict], int]:
        """Eventi con l'analisi da mostrare: l'ultima completata, altrimenti la più recente."""
        where, params = ["1=1"], []
        if public_only:
            where.append("public = 1")
        if q:
            where.append("(title LIKE ? OR description LIKE ? OR tags LIKE ?)")
            params += [f"%{q}%"] * 3
        if category:
            where.append("category = ?")
            params.append(category)
        clause = " AND ".join(where)
        with self.connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM events WHERE {clause}", params).fetchone()[0]
            rows = conn.execute(
                f"""SELECT e.id, e.title, e.category, e.tags, e.occurred_on, e.time_precision,
                           e.origin, e.public,
                           (SELECT COUNT(*) FROM sources s WHERE s.event_id = e.id) AS source_count,
                           (SELECT a.id FROM analyses a WHERE a.event_id = e.id
                              ORDER BY a.status = 'succeeded' DESC, a.created_at DESC, a.rowid DESC
                              LIMIT 1) AS analysis_id,
                           (SELECT a.status FROM analyses a WHERE a.event_id = e.id
                              ORDER BY a.status = 'succeeded' DESC, a.created_at DESC, a.rowid DESC
                              LIMIT 1) AS analysis_status
                    FROM events e WHERE {clause}
                    ORDER BY e.occurred_on DESC LIMIT ? OFFSET ?""",
                params + [page_size, (page - 1) * page_size],
            ).fetchall()
        items = []
        for r in rows:
            item = dict(r)
            item["tags"] = json.loads(item["tags"])
            item["public"] = bool(item["public"])
            items.append(item)
        return items, total

    # --- Sintesi IA -----------------------------------------------------------------------

    def create_summary(self, analysis_id: str, prompt_version: str, *,
                       exclusive: bool = False) -> str | None:
        summary_id = uuid.uuid4().hex
        with self.immediate() as conn:
            if exclusive and self._active_job_count(conn):
                return None
            conn.execute(
                "INSERT INTO summaries (id, analysis_id, status, prompt_version, created_at) "
                "VALUES (?,?,?,?,?)",
                (summary_id, analysis_id, "queued", prompt_version, utc_now()),
            )
        return summary_id

    def update_summary(self, summary_id: str, **fields) -> None:
        allowed = {"status", "model", "finished_at", "content", "usage", "error_code",
                   "error_message"}
        assert set(fields) <= allowed, set(fields) - allowed
        for key in ("content", "usage"):
            if key in fields and fields[key] is not None:
                fields[key] = json.dumps(fields[key])
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self.connect() as conn:
            conn.execute(f"UPDATE summaries SET {sets} WHERE id = ?", [*fields.values(), summary_id])

    def latest_summary(self, analysis_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM summaries WHERE analysis_id = ? ORDER BY created_at DESC, rowid DESC "
                "LIMIT 1", (analysis_id,)).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["content"] = json.loads(data["content"]) if data["content"] else None
        data.pop("usage", None)
        return data

    def summaries_created_since(self, since_iso: str) -> int:
        with self.connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM summaries WHERE created_at >= ? AND status != 'failed'",
                (since_iso,)).fetchone()[0]

    # --- Sessioni dell'operatore ----------------------------------------------------------

    def create_session(self, *, token_hash: str, csrf_token: str, epoch: str, credential: str,
                       created_at: str, expires_at: str) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO operator_sessions VALUES (?,?,?,?,?,?)",
                         (token_hash, csrf_token, epoch, credential, created_at, expires_at))

    def get_session(self, token_hash: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM operator_sessions WHERE token_hash = ?",
                               (token_hash,)).fetchone()
        return dict(row) if row else None

    def delete_session(self, token_hash: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM operator_sessions WHERE token_hash = ?", (token_hash,))

    def delete_all_sessions(self) -> int:
        with self.connect() as conn:
            return conn.execute("DELETE FROM operator_sessions").rowcount

    def purge_expired_sessions(self, now_iso: str) -> int:
        with self.connect() as conn:
            return conn.execute("DELETE FROM operator_sessions WHERE expires_at <= ?",
                                (now_iso,)).rowcount

    def record_login_attempt(self, client: str, success: bool, now_iso: str) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO login_attempts (client, success, created_at) VALUES (?,?,?)",
                         (client, int(success), now_iso))

    def login_failures_since(self, since_iso: str, client: str | None = None) -> tuple[int, str | None]:
        """Tentativi falliti dopo `since_iso` (di un client o di tutti) e il più vecchio tra questi."""
        query = ("SELECT COUNT(*), MIN(created_at) FROM login_attempts "
                 "WHERE success = 0 AND created_at > ?")
        params: list = [since_iso]
        if client is not None:
            query += " AND client = ?"
            params.append(client)
        with self.connect() as conn:
            count, oldest = conn.execute(query, params).fetchone()
        return count, oldest

    def purge_login_attempts(self, before_iso: str) -> int:
        with self.connect() as conn:
            return conn.execute("DELETE FROM login_attempts WHERE created_at < ?",
                                (before_iso,)).rowcount

    # --- Contabilità della spesa ----------------------------------------------------------

    def reserve_spend(self, *, entry: dict, budget_micros: int, window_start: str, now: str,
                      block_until: str) -> dict:
        """Prenota `entry["reserved_micros"]` se il budget residuo della finestra lo consente.

        Controllo e inserimento avvengono nella stessa transazione IMMEDIATE: due richieste
        simultanee non possono leggere lo stesso residuo. Se il budget non basta registra il
        blocco fino a `block_until`. Restituisce {"ok", "committed", "blocked_until"}.
        """
        with self.immediate() as conn:
            row = conn.execute("SELECT value FROM budget_state WHERE key = 'blocked_until'").fetchone()
            blocked_until = row["value"] if row else None
            committed = conn.execute(
                f"SELECT COALESCE(SUM({SPEND_COMMITTED}), 0) FROM spend_ledger WHERE created_at > ?",
                (window_start,)).fetchone()[0]
            if blocked_until and blocked_until > now:
                return {"ok": False, "committed": committed, "blocked_until": blocked_until}
            if committed + entry["reserved_micros"] > budget_micros:
                conn.execute("INSERT INTO budget_state VALUES ('blocked_until', ?) "
                             "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (block_until,))
                return {"ok": False, "committed": committed, "blocked_until": block_until}
            conn.execute(
                "INSERT INTO spend_ledger (id, provider, model, purpose, ref_id, attempt, status, "
                "reserved_micros, created_at) VALUES (?,?,?,?,?,?,'reserved',?,?)",
                (entry["id"], entry["provider"], entry["model"], entry["purpose"], entry.get("ref_id"),
                 entry.get("attempt", 1), entry["reserved_micros"], now))
            return {"ok": True, "committed": committed + entry["reserved_micros"],
                    "blocked_until": blocked_until}

    def settle_spend(self, entry_id: str, *, status: str, now: str, actual_micros: int | None = None,
                     usage: dict | None = None, note: str | None = None) -> None:
        assert status in ("confirmed", "uncertain", "released"), status
        with self.connect() as conn:
            conn.execute(
                "UPDATE spend_ledger SET status = ?, actual_micros = ?, usage = ?, note = ?, "
                "settled_at = ? WHERE id = ? AND status = 'reserved'",
                (status, actual_micros, json.dumps(usage) if usage is not None else None, note, now,
                 entry_id))

    def mark_open_spend_uncertain(self, now: str) -> int:
        """Dopo un riavvio le riserve ancora aperte hanno esito sconosciuto: restano impegnate."""
        with self.connect() as conn:
            return conn.execute(
                "UPDATE spend_ledger SET status = 'uncertain', settled_at = ?, "
                "note = 'interrotta da un riavvio' WHERE status = 'reserved'", (now,)).rowcount

    def spend_entries_since(self, since_iso: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT id, provider, model, purpose, attempt, status, reserved_micros, "
                f"actual_micros, created_at, settled_at, {SPEND_COMMITTED} AS committed_micros "
                f"FROM spend_ledger WHERE created_at > ? ORDER BY created_at", (since_iso,)).fetchall()
        return [dict(r) for r in rows]

    def budget_blocked_until(self) -> str | None:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM budget_state WHERE key = 'blocked_until'").fetchone()
        return row["value"] if row else None

    def set_budget_blocked_until(self, value: str) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO budget_state VALUES ('blocked_until', ?) "
                         "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (value,))

    # --- Copia di sicurezza ---------------------------------------------------------------

    def backup_to(self, target: Path) -> None:
        """Copia coerente del database (API di backup di SQLite, sicura con il server attivo)."""
        target = Path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        try:
            src = sqlite3.connect(self.path, timeout=15)
            dst = sqlite3.connect(tmp)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
            tmp.replace(target)
        except (sqlite3.Error, OSError) as exc:
            tmp.unlink(missing_ok=True)
            raise PersistenceError("Copia di sicurezza non riuscita") from exc

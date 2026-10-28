"""Persistenza delle ricerche di notizie: parametri, avanzamento, risultati normalizzati, eventi.

Si conservano solo i dati necessari a ricostruire la ricerca (parametri, richieste al provider,
URL, titolo, editore, date ed estratto breve), mai il testo integrale degli articoli.
"""

from __future__ import annotations

import json
import uuid

from ..errors import NotFound
from .store import Store, utc_now

ACTIVE = ("queued", "running")


class NewsStore:
    def __init__(self, store: Store):
        self.store = store

    def create_search(self, params: dict, cache_key: str, version: str) -> str | None:
        """Crea la ricerca solo se nessun job esterno è attivo (controllo e scrittura atomici)."""
        search_id = uuid.uuid4().hex
        with self.store.immediate() as conn:
            if self.store._active_job_count(conn):
                return None
            conn.execute(
                "INSERT INTO news_searches (id, params, cache_key, normalization_version, status, stage, "
                "created_at) VALUES (?,?,?,?,'queued','queued',?)",
                (search_id, json.dumps(params), cache_key, version, utc_now()))
        return search_id

    def find_reusable(self, cache_key: str, *, succeeded_since: str) -> dict | None:
        """Ricerca identica già in corso, oppure riuscita dopo `succeeded_since` (cache)."""
        with self.store.connect() as conn:
            row = conn.execute(
                "SELECT id, status FROM news_searches WHERE cache_key = ? "
                "AND (status IN ('queued','running') "
                "OR (status IN ('succeeded','partial','empty') AND created_at > ?)) "
                "ORDER BY created_at DESC LIMIT 1", (cache_key, succeeded_since)).fetchone()
        return dict(row) if row else None

    def update(self, search_id: str, **fields) -> None:
        allowed = {"status", "stage", "requests", "warnings", "excluded", "error_code", "error_message",
                   "started_at", "finished_at"}
        assert set(fields) <= allowed, set(fields) - allowed
        for key in ("requests", "warnings", "excluded"):
            if key in fields and fields[key] is not None:
                fields[key] = json.dumps(fields[key])
        sets = ", ".join(f"{k} = ?" for k in fields)
        with self.store.connect() as conn:
            conn.execute(f"UPDATE news_searches SET {sets} WHERE id = ?", [*fields.values(), search_id])

    def save_results(self, search_id: str, results: list[dict], events: list[dict]) -> None:
        with self.store.connect() as conn:
            conn.execute("DELETE FROM news_results WHERE search_id = ?", (search_id,))
            conn.execute("DELETE FROM news_events WHERE search_id = ?", (search_id,))
            conn.executemany("INSERT INTO news_results (search_id, idx, data) VALUES (?,?,?)",
                             [(search_id, r["idx"], json.dumps(r)) for r in results])
            conn.executemany("INSERT INTO news_events (search_id, idx, data) VALUES (?,?,?)",
                             [(search_id, i, json.dumps(e)) for i, e in enumerate(events)])

    def get(self, search_id: str) -> dict:
        with self.store.connect() as conn:
            row = conn.execute("SELECT * FROM news_searches WHERE id = ?", (search_id,)).fetchone()
            if row is None:
                raise NotFound("Ricerca non trovata")
            results = conn.execute("SELECT data FROM news_results WHERE search_id = ? ORDER BY idx",
                                   (search_id,)).fetchall()
            events = conn.execute(
                "SELECT idx, data, event_id, analysis_id FROM news_events WHERE search_id = ? ORDER BY idx",
                (search_id,)).fetchall()
        data = dict(row)
        for key in ("params", "requests", "warnings", "excluded"):
            data[key] = json.loads(data[key]) if data[key] else None
        data["results"] = [json.loads(r["data"]) for r in results]
        data["events"] = [{**json.loads(e["data"]), "idx": e["idx"], "event_id": e["event_id"],
                           "analysis_id": e["analysis_id"]} for e in events]
        return data

    def list_recent(self, limit: int = 10) -> list[dict]:
        with self.store.connect() as conn:
            rows = conn.execute(
                "SELECT s.id, s.params, s.status, s.created_at, s.finished_at, s.error_code, "
                "(SELECT COUNT(*) FROM news_events e WHERE e.search_id = s.id) AS event_count "
                "FROM news_searches s ORDER BY s.created_at DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "params": json.loads(r["params"])} for r in rows]

    def link_event(self, search_id: str, idx: int, event_id: str, analysis_id: str) -> None:
        with self.store.connect() as conn:
            conn.execute("UPDATE news_events SET event_id = ?, analysis_id = ? "
                         "WHERE search_id = ? AND idx = ?", (event_id, analysis_id, search_id, idx))

    def purge_older_than(self, before_iso: str) -> int:
        """Elimina ricerche concluse più vecchie della soglia, se nessun loro evento è stato analizzato."""
        with self.store.connect() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            return conn.execute(
                "DELETE FROM news_searches WHERE created_at < ? AND status NOT IN ('queued','running') "
                "AND NOT EXISTS (SELECT 1 FROM news_events e WHERE e.search_id = news_searches.id "
                "AND e.event_id IS NOT NULL)", (before_iso,)).rowcount

"""Riga di comando: usa gli stessi servizi dell'API.

    python -m linkedia init            schema, catalogo e analisi mancanti (all'avvio del server)
    python -m linkedia seed            importa il catalogo e calcola le analisi (prezzi gratuiti)
    python -m linkedia analyze ID      ricalcola l'analisi di un evento
    python -m linkedia events          elenca gli eventi in archivio
    python -m linkedia set-public ID   pubblica (o con --off nasconde) un caso
    python -m linkedia hash-password   genera l'hash per LIA_OPERATOR_PASSWORD_HASH
    python -m linkedia revoke-sessions chiude tutte le sessioni dell'operatore
    python -m linkedia backup          copia coerente del database
    python -m linkedia serve           server di sviluppo (127.0.0.1:5000)

Nessun comando chiama servizi IA a pagamento. Nessun comando cancella eventi o analisi.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from datetime import UTC, datetime
from pathlib import Path

from .config import Settings, configure_logging
from .domain.markets import MARKETS
from .errors import LiaError
from .providers.market_data import YahooChartProvider
from .services.analysis import AnalysisService
from .services.jobs import InlineRunner
from .storage.store import Store

BACKUPS_KEPT = 7


def _store(settings: Settings) -> Store:
    store = Store(settings.database_path)
    store.initialize()
    return store


def _service(settings: Settings) -> AnalysisService:
    return AnalysisService(_store(settings), YahooChartProvider(timeout=settings.http_timeout_seconds),
                           InlineRunner())


def _report(service: AnalysisService, analysis_id: str) -> bool:
    analysis = service.store.get_analysis(analysis_id)
    if analysis["status"] == "succeeded":
        markets = analysis["result"]["markets"]
        ok = sum(1 for m in markets.values() if m["status"] == "ok")
        print(f"  OK     {analysis['event_id']}: {ok}/{len(markets)} mercati, analisi {analysis_id}")
        return True
    print(f"  ERRORE {analysis['event_id']}: {analysis['error_message']}")
    return False


def _seed(service: AnalysisService, ids: list[str] | None, *, missing_only: bool) -> int:
    n = service.import_catalogue()
    print(f"Catalogo importato: {n} eventi")
    curated = [e.id for e in service.store.all_events() if e.origin == "curated"]
    targets = ids or curated
    if missing_only:
        targets = [i for i in targets
                   if service.store.latest_analysis_for_event(i, succeeded_only=True) is None]
        if not targets:
            print("Tutti i casi dimostrativi hanno già un'analisi: nessun download.")
            return 0
    errors = service.sync_all_prices()
    for market_id, message in errors.items():
        print(f"  ERRORE prezzi {market_id}: {message}")
    if len(errors) == len(MARKETS):
        print("Nessun mercato aggiornato: analisi non calcolate.", file=sys.stderr)
        return 2
    results = [_report(service, service.request_analysis(i)) for i in targets]
    return 0 if all(results) else 1


def backup(settings: Settings, target_dir: Path | None = None) -> Path:
    store = _store(settings)
    folder = target_dir or settings.database_path.parent / "backups"
    target = folder / f"lia-{datetime.now(UTC):%Y%m%dT%H%M%SZ}.sqlite3"
    store.backup_to(target)
    for old in sorted(folder.glob("lia-*.sqlite3"))[:-BACKUPS_KEPT]:
        old.unlink()
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linkedia", description="LiA - Linked Intelligent Analyst")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="schema, catalogo e analisi mancanti; non cancella nulla")
    seed = sub.add_parser("seed", help="importa il catalogo curato e calcola le analisi")
    seed.add_argument("--only", nargs="*", help="limita a questi id evento")
    analyze = sub.add_parser("analyze", help="ricalcola l'analisi di un evento")
    analyze.add_argument("event_id")
    sub.add_parser("events", help="elenca gli eventi")
    public = sub.add_parser("set-public", help="rende pubblico (o privato con --off) un caso")
    public.add_argument("event_id")
    public.add_argument("--off", action="store_true")
    sub.add_parser("hash-password", help="legge una password da tastiera e stampa l'hash Argon2id")
    sub.add_parser("revoke-sessions", help="chiude tutte le sessioni dell'operatore")
    bk = sub.add_parser("backup", help="copia coerente del database in <dir db>/backups")
    bk.add_argument("--dir", type=Path)
    serve = sub.add_parser("serve", help="server di sviluppo")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=5000)
    args = parser.parse_args(argv)

    if args.command == "hash-password":
        from .services.auth import hash_password

        # La password non passa da argomenti, variabili d'ambiente o file: solo da tastiera o stdin.
        if sys.stdin.isatty():
            first = getpass.getpass("Nuova password: ")
            if first != getpass.getpass("Ripeti: "):
                print("Le password non coincidono.", file=sys.stderr)
                return 2
        else:
            first = sys.stdin.readline().rstrip("\r\n")
        if len(first) < 12:
            print("Password troppo corta: almeno 12 caratteri.", file=sys.stderr)
            return 2
        print(hash_password(first))
        return 0

    settings = Settings.from_env()
    configure_logging(settings.log_level)
    try:
        if args.command == "serve":
            from .api import create_app

            create_app(settings).run(host=args.host, port=args.port, debug=settings.debug)
            return 0
        if args.command == "revoke-sessions":
            print(f"Sessioni chiuse: {_store(settings).delete_all_sessions()}")
            return 0
        if args.command == "backup":
            print(f"Copia salvata: {backup(settings, args.dir)}")
            return 0
        service = _service(settings)
        if args.command == "init":
            # Idempotente: lo schema si aggiorna senza perdite, il catalogo si reimporta,
            # le analisi si calcolano solo per i casi che non ne hanno una riuscita.
            backup(settings)
            return _seed(service, None, missing_only=True)
        if args.command == "seed":
            return _seed(service, args.only, missing_only=False)
        if args.command == "analyze":
            return 0 if _report(service, service.request_analysis(args.event_id)) else 1
        if args.command == "set-public":
            service.store.set_event_public(args.event_id, not args.off)
            print(f"{args.event_id}: {'privato' if args.off else 'pubblico'}")
            return 0
        if args.command == "events":
            for e in service.store.all_events():
                flag = "pubblico" if e.public else "privato "
                print(f"{e.occurred_on}  {flag}  {e.id:40}  {e.title}")
            return 0
    except LiaError as exc:
        print(f"Errore: {exc.message}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

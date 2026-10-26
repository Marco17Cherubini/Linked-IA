"""Riga di comando: usa gli stessi servizi dell'API.

    python -m linkedia seed            importa il catalogo e calcola le analisi (prezzi gratuiti)
    python -m linkedia analyze ID      ricalcola l'analisi di un evento
    python -m linkedia events          elenca gli eventi in archivio
    python -m linkedia serve           server di sviluppo (127.0.0.1:5000)

Nessun comando chiama servizi IA a pagamento.
"""

from __future__ import annotations

import argparse
import sys

from .config import Settings, configure_logging
from .domain.markets import MARKETS
from .errors import LiaError
from .providers.market_data import YahooChartProvider
from .services.analysis import AnalysisService
from .services.jobs import InlineRunner
from .storage.store import Store


def _service(settings: Settings) -> AnalysisService:
    store = Store(settings.database_path)
    store.initialize()
    store.fail_interrupted_jobs()
    return AnalysisService(store, YahooChartProvider(timeout=settings.http_timeout_seconds),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linkedia", description="LiA - Linked Intelligent Analyst")
    sub = parser.add_subparsers(dest="command", required=True)
    seed = sub.add_parser("seed", help="importa il catalogo curato e calcola le analisi")
    seed.add_argument("--only", nargs="*", help="limita a questi id evento")
    analyze = sub.add_parser("analyze", help="ricalcola l'analisi di un evento")
    analyze.add_argument("event_id")
    sub.add_parser("events", help="elenca gli eventi")
    serve = sub.add_parser("serve", help="server di sviluppo")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=5000)
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    configure_logging(settings.log_level)
    try:
        if args.command == "serve":
            from .api import create_app

            create_app(settings).run(host=args.host, port=args.port, debug=settings.debug)
            return 0
        service = _service(settings)
        if args.command == "seed":
            n = service.import_catalogue()
            print(f"Catalogo importato: {n} eventi")
            errors = service.sync_all_prices()
            for market_id, message in errors.items():
                print(f"  ERRORE prezzi {market_id}: {message}")
            if len(errors) == len(MARKETS):
                print("Nessun mercato aggiornato: analisi non calcolate.", file=sys.stderr)
                return 2
            ids = args.only or [e.id for e in service.store.all_events() if e.origin == "curated"]
            results = [_report(service, service.request_analysis(i)) for i in ids]
            return 0 if all(results) else 1
        if args.command == "analyze":
            return 0 if _report(service, service.request_analysis(args.event_id)) else 1
        if args.command == "events":
            for e in service.store.all_events():
                print(f"{e.occurred_on}  {e.id:40}  {e.title}")
            return 0
    except LiaError as exc:
        print(f"Errore: {exc.message}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

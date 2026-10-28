"""Creazione ed esecuzione delle analisi (stesso codice per API e CLI)."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import date, timedelta
from importlib import resources

from .. import METHOD_VERSION
from ..domain.analysis import build_market_analysis
from ..domain.events import Event, parse_event
from ..domain.markets import MARKETS
from ..errors import Conflict, InvalidInput, LiaError, ProviderUnavailable, RetryLater, Unauthorized
from ..providers.market_data import MarketDataProvider
from ..storage.store import Store, utc_now

log = logging.getLogger(__name__)

# Margini in giorni di calendario per coprire 60 sedute prima e dopo ogni evento.
PRICE_MARGIN_BEFORE = timedelta(days=150)
PRICE_MARGIN_AFTER = timedelta(days=120)
FETCH_COOLDOWN_SECONDS = 600


def load_catalogue() -> list[Event]:
    """Catalogo curato distribuito con il package (`linkedia/data/events.json`)."""
    raw = json.loads(resources.files("linkedia.data").joinpath("events.json").read_text("utf-8"))
    events = []
    for item in raw["events"]:
        event, errors = parse_event(item, origin="curated")
        if errors:
            raise InvalidInput(f"Catalogo non valido ({item.get('id')}): {'; '.join(errors)}")
        events.append(event)
    return events


class AnalysisService:
    def __init__(self, store: Store, market_data: MarketDataProvider, runner, *, today=date.today,
                 authorize: Callable[[str], bool] = lambda session_id: True):
        self.store = store
        self.market_data = market_data
        self.runner = runner
        self._today = today
        self.authorize = authorize
        self._failed_fetches: dict[str, float] = {}
        # Inizio dell'intervallo già richiesto al provider, per mercato, con la data della richiesta.
        self._requested: dict[str, tuple[str, str]] = {}

    # --- Eventi ---------------------------------------------------------------------------

    def import_catalogue(self) -> int:
        events = load_catalogue()
        for event in events:
            self.store.upsert_event(event)
        return len(events)

    def create_event(self, payload: dict, *, session_id: str | None = None,
                     origin: str = "user") -> tuple[Event, str]:
        event, errors = parse_event(payload, origin=origin)
        if errors:
            raise InvalidInput("Dati dell'evento non validi: " + "; ".join(errors))
        if event.occurred_on > self._today():
            raise InvalidInput("La data dell'evento non può essere futura")
        if self.store.event_exists(event.id):
            raise Conflict("Esiste già un evento con questo identificativo")
        if session_id is not None and self.store.active_job_count():
            # Rifiuto prima di salvare: l'evento non resta orfano senza analisi.
            raise RetryLater("Un'altra operazione esterna è in corso: riprova tra qualche minuto.",
                             code="busy", retry_after=60)
        self.store.upsert_event(event)
        return event, self.request_analysis(event.id, session_id=session_id)

    # --- Analisi --------------------------------------------------------------------------

    def request_analysis(self, event_id: str, *, session_id: str | None = None) -> str:
        """Accoda il calcolo. Con `session_id` (richiesta dall'API) il job parte solo se nessun
        altro job esterno è attivo e, al momento dell'esecuzione, la sessione è ancora valida."""
        self.store.get_event(event_id)  # NotFound se non esiste
        latest = self.store.latest_analysis_for_event(event_id)
        if latest and latest["status"] in ("queued", "running"):
            return latest["id"]
        analysis_id = self.store.create_analysis(event_id, METHOD_VERSION,
                                                 exclusive=session_id is not None)
        if analysis_id is None:
            raise RetryLater("Un'altra operazione esterna è in corso: riprova tra qualche minuto.",
                             code="busy", retry_after=60)
        self.runner.submit(self.run_analysis, analysis_id, session_id)
        return analysis_id

    def _price_range(self, events: list[Event]) -> tuple[date, date]:
        first = min(e.occurred_on for e in events) - PRICE_MARGIN_BEFORE
        last = min(self._today(), max(e.occurred_on for e in events) + PRICE_MARGIN_AFTER)
        return first, last

    def ensure_prices(self, market_id: str, start: date, end: date) -> None:
        """Scarica i prezzi solo se l'archivio non copre l'intervallo o non è aggiornato a oggi."""
        sync = self.store.price_sync(market_id)
        today = utc_now()[:10]
        if sync:
            # Se il provider non ha sedute fino a `start` (serie che inizia più tardi), la
            # copertura non sarà mai completa: basta averla già richiesta oggi da questo processo.
            requested = self._requested.get(market_id)
            covered = (sync["first_date"] <= start.isoformat()
                       or (requested is not None and requested[1] == today
                           and requested[0] <= start.isoformat()))
            fresh = sync["last_date"] >= end.isoformat() or sync["fetched_at"][:10] == today
            if covered and fresh:
                return
        failed_at = self._failed_fetches.get(market_id)
        if failed_at is not None and time.monotonic() - failed_at < FETCH_COOLDOWN_SECONDS:
            # Dopo un guasto non si ripete la richiesta a ogni analisi: si evita di
            # sovraccaricare il provider (e di farsi limitare con HTTP 429).
            raise ProviderUnavailable(
                f"Prezzi di {MARKETS[market_id].name} temporaneamente non disponibili"
            )
        try:
            bars = self.market_data.daily_bars(MARKETS[market_id], start, end)
        except ProviderUnavailable:
            self._failed_fetches[market_id] = time.monotonic()
            raise
        self._failed_fetches.pop(market_id, None)
        self._requested[market_id] = (start.isoformat(), today)
        if not bars:
            raise ProviderUnavailable(f"Nessun prezzo restituito per {MARKETS[market_id].name}")
        self.store.save_prices(market_id, bars, provider=self.market_data.name)
        log.info("Prezzi %s aggiornati: %s sedute", market_id, len(bars))

    def sync_all_prices(self) -> dict[str, str]:
        """Aggiorna i prezzi di tutti i mercati per l'intero catalogo. Restituisce gli errori."""
        start, end = self._price_range(self.store.all_events())
        errors = {}
        for market_id in MARKETS:
            try:
                self.ensure_prices(market_id, start, end)
            except ProviderUnavailable as exc:
                errors[market_id] = exc.message
        return errors

    def run_analysis(self, analysis_id: str, session_id: str | None = None) -> None:
        analysis = self.store.get_analysis(analysis_id)
        self.store.mark_analysis_running(analysis_id)
        try:
            if session_id is not None and not self.authorize(session_id):
                raise Unauthorized("Sessione scaduta o revocata prima dell'esecuzione")
            result = self._compute(analysis["event_id"])
        except LiaError as exc:
            self.store.fail_analysis(analysis_id, exc.code, exc.message)
            return
        except Exception:
            log.exception("Analisi %s fallita", analysis_id)
            self.store.fail_analysis(analysis_id, "internal_error",
                                     "Errore interno durante il calcolo dell'analisi.")
            return
        self.store.finish_analysis(analysis_id, result)

    def _compute(self, event_id: str) -> dict:
        event = self.store.get_event(event_id)
        # Un caso pubblico usa come precedenti solo casi pubblici: i suoi risultati, visibili
        # a tutti, non devono contenere eventi privati dell'operatore.
        catalogue = self.store.all_events(public_only=event.public)
        start, end = self._price_range(catalogue + [event])
        markets, market_errors, providers = {}, {}, {}
        for market_id, market in MARKETS.items():
            try:
                self.ensure_prices(market_id, start, end)
            except ProviderUnavailable as exc:
                # Il guasto resta visibile: il mercato non viene mostrato come "senza movimento".
                market_errors[market_id] = {"code": exc.code, "message": exc.message}
                if not self.store.price_sync(market_id):
                    continue
            bars = self.store.get_prices(market_id)
            if not bars:
                market_errors.setdefault(market_id, {"code": "insufficient_data",
                                                     "message": "Nessun prezzo in archivio."})
                continue
            markets[market_id] = build_market_analysis(
                event, market, bars, catalogue
            )
            providers[market_id] = self.store.price_sync(market_id)
        if not markets:
            raise ProviderUnavailable(
                "Dati di mercato non disponibili per nessun indice: riprovare più tardi."
            )
        return {
            "method_version": METHOD_VERSION,
            "computed_at": utc_now(),
            "event": event.to_dict(),
            "markets": markets,
            "market_errors": market_errors,
            "price_sources": {
                m: {"provider": p["provider"], "fetched_at": p["fetched_at"],
                    "first_date": p["first_date"], "last_date": p["last_date"]}
                for m, p in providers.items()
            },
        }

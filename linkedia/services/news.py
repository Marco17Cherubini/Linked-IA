"""Ricerca automatica delle notizie per data: capacità centrale di LiA.

Percorso: parametri validati → (cache) → job esterno esclusivo → richieste al provider, ognuna
con la propria riserva di budget → normalizzazione e controllo temporale lato server →
raggruppamento deterministico → estrazione strutturata facoltativa → schede evento salvate.
Dalla scheda scelta si crea un evento privato e si avvia l'analisi finanziaria esistente.

Gli errori restano errori: provider non configurato, credenziali rifiutate, timeout, limiti,
budget esaurito non diventano mai «nessun evento». Le ricerche riuscite senza risultati hanno
uno stato proprio (`empty`).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from ..domain.events import CATEGORIES
from ..domain.news import (
    NORMALIZATION_VERSION,
    SearchParams,
    accept_result,
    build_requests,
    cluster,
    dedupe,
    draft_event,
    event_slug,
    parse_search_params,
    rank_drafts,
)
from ..errors import (
    ConfigurationError,
    Conflict,
    InvalidInput,
    LiaError,
    ProviderUnavailable,
    RetryLater,
    Unauthorized,
)
from ..providers.news_search import NewsSearchClient
from ..storage.news_store import NewsStore
from ..storage.store import Store, utc_now
from . import news_extraction
from .analysis import AnalysisService
from .budget import BudgetService, actual_cost_micros, max_cost_micros, price_for
from .paid_calls import run_paid

log = logging.getLogger(__name__)

CACHE_TTL_HISTORICAL = timedelta(days=30)
CACHE_TTL_RECENT = timedelta(hours=6)
RECENT_DAYS = 30
RETENTION = timedelta(days=90)
MAX_SOURCES_PER_EVENT = 8
SEARCH_ATTEMPTS = 2
EXTRACTION_ATTEMPTS = 1


class NewsSearchService:
    def __init__(self, store: Store, settings, runner, budget: BudgetService, analysis: AnalysisService,
                 search_factory: Callable[[], NewsSearchClient], llm_factory: Callable, *,
                 authorize: Callable[[str], bool] = lambda session_id: True,
                 today: Callable[[], date] = lambda: datetime.now(UTC).date(),
                 sleep: Callable[[float], None] = time.sleep):
        self.store = store
        self.news = NewsStore(store)
        self.settings = settings
        self.runner = runner
        self.budget = budget
        self.analysis = analysis
        self.search_factory = search_factory
        self.llm_factory = llm_factory
        self.authorize = authorize
        self.today = today
        self.sleep = sleep

    # --- Costi -----------------------------------------------------------------------------------

    def _search_price(self):
        price = price_for("perplexity", "search")
        if price is None:
            raise ConfigurationError("Ricerca disabilitata: prezzo del provider non verificato",
                                     code="provider_not_configured")
        return price

    def _extraction_price(self):
        return price_for("deepseek", self.settings.deepseek_model) if self.settings.ai_enabled else None

    def planned_max(self, params: SearchParams) -> int:
        """Costo massimo di una ricerca: tutti i tentativi possibili di ricerca ed estrazione."""
        total = len(build_requests(params)) * SEARCH_ATTEMPTS * self._search_price().per_request
        price = self._extraction_price()
        if price is not None:
            total += EXTRACTION_ATTEMPTS * max_cost_micros(
                price, prompt_bytes=news_extraction.MAX_PROMPT_BYTES + len(news_extraction.SYSTEM_PROMPT) * 4,
                max_output_tokens=news_extraction.MAX_OUTPUT_TOKENS)
        return total

    # --- Richiesta -------------------------------------------------------------------------------

    def request(self, payload: dict, *, session_id: str) -> dict:
        if not self.settings.news_search_enabled:
            raise ConfigurationError("Ricerca automatica non configurata su questo server",
                                     code="provider_not_configured")
        params, errors = parse_search_params(payload, today=self.today())
        if errors:
            raise InvalidInput("Parametri di ricerca non validi: " + "; ".join(errors))
        ttl = CACHE_TTL_RECENT if (self.today() - params.end).days < RECENT_DAYS else CACHE_TTL_HISTORICAL
        since = (datetime.now(UTC) - ttl).isoformat(timespec="seconds")
        existing = self.news.find_reusable(params.cache_key(), succeeded_since=since)
        if existing:
            # Doppio clic, ricarica o richiesta identica recente: nessuna nuova spesa.
            return {"search_id": existing["id"], "reused": True,
                    "cached": existing["status"] not in ("queued", "running")}
        planned = self.planned_max(params)
        if planned > self.settings.news_search_max_micros:
            raise Conflict("Il costo massimo della ricerca supera il limite configurato per singola ricerca")
        self.budget.ensure_available(planned)
        search_id = self.news.create_search(params.to_dict(), params.cache_key(), NORMALIZATION_VERSION)
        if search_id is None:
            raise RetryLater("Un'altra operazione esterna è in corso: riprova tra qualche minuto.",
                             code="busy", retry_after=60)
        self.runner.submit(self.run, search_id, session_id)
        return {"search_id": search_id, "reused": False, "cached": False}

    # --- Esecuzione -----------------------------------------------------------------------------

    def _fail(self, search_id: str, code: str, message: str) -> None:
        self.news.update(search_id, status="failed", stage="failed", error_code=code, error_message=message,
                         finished_at=utc_now())

    def run(self, search_id: str, session_id: str = "") -> None:
        self.news.update(search_id, status="running", stage="searching", started_at=utc_now())
        try:
            if not self.authorize(session_id):
                raise Unauthorized("Sessione scaduta o revocata prima dell'esecuzione")
            if not self.settings.news_search_enabled:
                raise ConfigurationError("Ricerca automatica non configurata", code="provider_not_configured")
            self._execute(search_id)
        except LiaError as exc:
            self._fail(search_id, exc.code, exc.message)
        except Exception:
            log.exception("Ricerca %s fallita", search_id)
            self._fail(search_id, "internal_error", "Errore interno durante la ricerca.")

    def _execute(self, search_id: str) -> None:
        stored = self.news.get(search_id)
        params, _ = parse_search_params(stored["params"], today=self.today())
        if params is None:
            raise InvalidInput("Parametri della ricerca non più validi")
        price = self._search_price()
        client = self.search_factory()
        retrieved_on = self.today()
        request_log, raw_by_kind, failures = [], [], []
        for spec in build_requests(params):
            entry = {"kind": spec.kind, "queries": list(spec.queries),
                     "published_after": spec.published_after.isoformat(),
                     "published_before": spec.published_before.isoformat() if spec.published_before else None,
                     "provider": client.provider, "retrieved_at": utc_now()}
            try:
                raw = run_paid(
                    self.budget, provider=client.provider, model=client.model, purpose="news_search",
                    ref_id=search_id, amount=price.per_request,
                    call=lambda spec=spec: (client.search(list(spec.queries),
                                                          published_after=spec.published_after,
                                                          published_before=spec.published_before), None),
                    cost_of=lambda usage: price.per_request, attempts=SEARCH_ATTEMPTS, sleep=self.sleep)
            except (ProviderUnavailable, RetryLater) as exc:
                entry.update(status="failed", error_code=exc.code)
                failures.append(exc)
                request_log.append(entry)
                continue
            entry.update(status="ok", result_count=len(raw))
            request_log.append(entry)
            raw_by_kind.append((spec.kind, raw))
        self.news.update(search_id, requests=request_log)
        if not raw_by_kind:
            first = failures[0]
            raise first if isinstance(first, LiaError) else ProviderUnavailable(str(first))

        results, excluded = self._normalize(raw_by_kind, params, retrieved_on)
        groups = cluster(results)
        drafts = [draft_event(g, params) for g in groups]
        warnings = [{"code": "partial", "message": f"Una richiesta non è riuscita: {f.message}"}
                    for f in failures]
        if drafts:
            self.news.update(search_id, stage="extracting")
            drafts, warning = self._extract(search_id, groups, drafts, params)
            if warning:
                warnings.append(warning)
        drafts = rank_drafts(drafts)
        status = "empty" if not drafts else ("partial" if failures else "succeeded")
        self.news.save_results(search_id, [r.to_dict() for r in results], [d.to_dict() for d in drafts])
        self.news.update(search_id, status=status, stage="done", warnings=warnings, excluded=excluded,
                         finished_at=utc_now())

    @staticmethod
    def _normalize(raw_by_kind, params: SearchParams, retrieved_on: date):
        accepted, excluded, idx = [], {}, 0
        for kind, raw in raw_by_kind:
            for rank, item in enumerate(raw):
                result, reason = accept_result(item if isinstance(item, dict) else {}, kind=kind, rank=rank,
                                               idx=idx, params=params, retrieved_on=retrieved_on)
                if result is None:
                    excluded[reason] = excluded.get(reason, 0) + 1
                    continue
                accepted.append(result)
                idx += 1
        unique = dedupe(accepted)
        if len(unique) < len(accepted):
            excluded["duplicate_url"] = len(accepted) - len(unique)
        return unique, excluded

    def _extract(self, search_id, groups, drafts, params):
        """Estrazione con il modello se configurato; in ogni altro caso restano le schede deterministiche."""
        price = self._extraction_price()
        if price is None:
            return drafts, None
        try:
            client = self.llm_factory()
            prompt = news_extraction.build_prompt(groups, params)
            size = len(news_extraction.SYSTEM_PROMPT.encode()) + len(prompt.encode())
            text = run_paid(
                self.budget, provider=client.provider, model=client.model, purpose="news_extraction",
                ref_id=search_id, amount=max_cost_micros(price, prompt_bytes=size,
                                                          max_output_tokens=news_extraction.MAX_OUTPUT_TOKENS),
                call=lambda: client.chat(news_extraction.SYSTEM_PROMPT, prompt,
                                         max_tokens=news_extraction.MAX_OUTPUT_TOKENS),
                cost_of=lambda usage: actual_cost_micros(price, usage) if usage else None,
                attempts=EXTRACTION_ATTEMPTS, sleep=self.sleep)
        except (ProviderUnavailable, RetryLater, ConfigurationError) as exc:
            return drafts, {"code": "extraction_skipped",
                            "message": f"Schede costruite senza modello linguistico: {exc.message}"}
        except Exception:
            # La riserva è già stata trattenuta come incerta da run_paid: si prosegue senza modello.
            log.exception("Estrazione degli eventi non riuscita (ricerca %s)", search_id)
            return drafts, {"code": "extraction_skipped",
                            "message": "Schede costruite senza modello linguistico: errore interno."}
        refined, discarded = news_extraction.apply_extraction(text, groups, drafts, params)
        warning = ({"code": "model_discarded",
                    "message": f"{discarded} gruppi indicati dal modello come non eventi: esclusi."}
                   if discarded else None)
        return refined, warning

    # --- Lettura e analisi -------------------------------------------------------------------------

    def get(self, search_id: str) -> dict:
        return self.news.get(search_id)

    def recent(self) -> list[dict]:
        return self.news.list_recent()

    def purge(self) -> int:
        cutoff = (datetime.now(UTC) - RETENTION).isoformat(timespec="seconds")
        return self.news.purge_older_than(cutoff)

    def _unique_event_id(self, title: str, day: date) -> str:
        base = event_slug(title, day)
        candidate, n = base, 2
        while self.store.event_exists(candidate):
            candidate = f"{base[:75]}-{n}"
            n += 1
        return candidate

    def analyze_event(self, search_id: str, idx: int, *, session_id: str) -> dict:
        search = self.news.get(search_id)
        if search["status"] not in ("succeeded", "partial"):
            raise Conflict("La ricerca non è conclusa o non ha prodotto eventi")
        events = {e["idx"]: e for e in search["events"]}
        if idx not in events:
            raise InvalidInput("Evento non presente in questa ricerca")
        event = events[idx]
        if event.get("analysis_id"):
            return {"event_id": event["event_id"], "analysis_id": event["analysis_id"], "reused": True}
        results = {r["idx"]: r for r in search["results"]}
        accessed = (search["finished_at"] or utc_now())[:10]
        sources = [{"url": results[i]["url"], "publisher": results[i]["publisher"][:80],
                    "title": results[i]["title"][:200], "kind": "news", "accessed_on": accessed,
                    "published_on": results[i]["published_on"]}
                   for i in event["result_idx"][:MAX_SOURCES_PER_EVENT] if i in results]
        if not sources:
            raise Conflict("L'evento non ha fonti utilizzabili")
        day = date.fromisoformat(event["event_date"])
        payload = {
            "id": self._unique_event_id(event["title"], day),
            "title": event["title"][:160],
            "description": event["description"][:1200] or event["title"],
            "category": event["category"] if event["category"] in CATEGORIES else "political",
            "tags": event["tags"][:12],
            "occurred_on": day.isoformat(),
            # Dalla ricerca si conosce solo il giorno: nessun orario inventato. Vale la regola
            # prudente della seduta base (ultima seduta chiusa prima del giorno dell'evento).
            "time_precision": "unknown",
            "sources": sources,
        }
        created, analysis_id = self.analysis.create_event(payload, session_id=session_id, origin="search")
        self.news.link_event(search_id, idx, created.id, analysis_id)
        return {"event_id": created.id, "analysis_id": analysis_id, "reused": False}

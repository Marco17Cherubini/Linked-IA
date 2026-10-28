"""Sintesi IA di un'analisi già calcolata.

La sintesi è un servizio a pagamento: parte solo su richiesta esplicita dell'operatore
autenticato, una volta per analisi (salvo rigenerazione esplicita), entro un limite di
numero e un budget monetario globale controllato prima di ogni tentativo (vedi `budget`).
Il modello riceve esclusivamente i dati strutturati dell'analisi e deve restituire JSON
con uno schema fisso, validato prima del salvataggio.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from ..config import Settings
from ..errors import (
    ConfigurationError,
    Conflict,
    InvalidInput,
    LiaError,
    ProviderUnavailable,
    RetryLater,
    Unauthorized,
)
from ..providers.llm import BilledResponseError, LLMClient
from ..storage.store import Store, utc_now
from .budget import BudgetService, actual_cost_micros, max_cost_micros, price_for

log = logging.getLogger(__name__)

PROMPT_VERSION = "summary-v1"
MAX_OUTPUT_TOKENS = 900
# Limite al testo inviato al modello: oltre questa dimensione la sintesi non parte.
MAX_PROMPT_BYTES = 48_000
# Tentativi complessivi per sintesi: si ripete solo se il precedente è certamente non fatturato.
MAX_ATTEMPTS = 2
RETRY_DELAY_SECONDS = 2.0

SYSTEM_PROMPT = """Sei un analista che commenta dati di mercato già calcolati.
Regole vincolanti:
- Usa solo i numeri presenti nei dati forniti; non inventare valori, date o eventi.
- Le frequenze dei precedenti sono frequenze osservate in un piccolo campione:
  non chiamarle probabilità e non fare previsioni.
- Distingui ciò che i dati mostrano da ciò che è interpretazione.
- Cita la numerosità del campione e i limiti dei dati.
- Scrivi in italiano, in modo sobrio.
Rispondi con un oggetto JSON con esattamente queste chiavi:
{"headline": string (max 140 caratteri),
 "observations": array di 2-4 stringhe (fatti presenti nei dati),
 "interpretation": string (max 600 caratteri, chiaramente interpretativa),
 "limitations": array di 2-4 stringhe}"""


def _compact_market(m: dict, include_outcomes: bool) -> dict:
    data = {
        "base_date": m.get("base", {}).get("date"),
        "base_rule": m.get("base", {}).get("rule"),
        "indicators_at_cutoff": {
            i["id"]: {"value": i["value"], "unit": i["unit"]}
            for i in m.get("observed", {}).get("indicators", [])
        },
        "precedents": [
            {"title": p["title"], "date": p["occurred_on"], "returns_pct": p["returns"]}
            for p in m.get("precedents", {}).get("items", [])
        ],
        "sample_stats_pct": {
            h: {k: s[k] for k in ("n", "median", "q1", "q3", "min", "max", "up_count")}
            for h, s in m.get("stats", {}).items()
        },
        "warnings": [w["code"] for w in m.get("warnings", [])],
    }
    if include_outcomes:
        data["event_outcomes_pct"] = {
            str(r["h"]): r["value"] for r in m.get("outcomes", {}).get("returns", [])
        }
    return data


def build_user_prompt(result: dict) -> str:
    event = result["event"]
    payload = {
        "event": {k: event[k] for k in ("title", "description", "category", "occurred_on",
                                         "occurred_at", "time_precision")},
        "source_count": len(event.get("sources", [])),
        "method_version": result["method_version"],
        "markets": {mid: _compact_market(m, include_outcomes=True)
                    for mid, m in result["markets"].items() if m.get("status") == "ok"},
        "units": "rendimenti e indicatori in punti percentuali, vol_20 in % annua, zscore in σ",
    }
    return "Dati dell'analisi (JSON):\n" + json.dumps(payload, ensure_ascii=False)


def parse_summary(content: str) -> dict:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ProviderUnavailable("Il modello IA ha restituito una risposta non valida") from exc
    if not isinstance(data, dict):
        raise ProviderUnavailable("Il modello IA non ha restituito un oggetto JSON")
    return validate_summary(data)


def validate_summary(data: dict) -> dict:
    def text(value, max_len: int) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ProviderUnavailable("Sintesi IA non conforme allo schema richiesto")
        return value.strip()[:max_len]

    def items(value, lo: int, hi: int, max_len: int) -> list[str]:
        if not isinstance(value, list) or not lo <= len(value) <= hi + 2:
            raise ProviderUnavailable("Sintesi IA non conforme allo schema richiesto")
        return [text(v, max_len) for v in value[:hi]]

    return {
        "headline": text(data.get("headline"), 160),
        "observations": items(data.get("observations"), 1, 4, 400),
        "interpretation": text(data.get("interpretation"), 800),
        "limitations": items(data.get("limitations"), 1, 4, 400),
    }


class SummaryService:
    def __init__(self, store: Store, settings: Settings, runner,
                 llm_factory: Callable[[], LLMClient], budget: BudgetService, *,
                 authorize: Callable[[str], bool] = lambda session_id: True,
                 sleep: Callable[[float], None] = time.sleep):
        self.store = store
        self.settings = settings
        self.runner = runner
        self.llm_factory = llm_factory
        self.budget = budget
        self.authorize = authorize
        self.sleep = sleep

    def _price(self):
        price = price_for("deepseek", self.settings.deepseek_model)
        if price is None:
            # Senza un prezzo verificato non si può stimare il costo massimo: nessuna chiamata.
            raise ConfigurationError("Sintesi IA disabilitata: prezzo del modello non verificato")
        return price

    def _prompt(self, analysis_id: str) -> str:
        prompt = build_user_prompt(self.store.get_analysis(analysis_id)["result"])
        if len(prompt.encode("utf-8")) + len(SYSTEM_PROMPT.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise InvalidInput("Analisi troppo estesa per la sintesi IA")
        return prompt

    def _max_cost(self, prompt: str) -> int:
        size = len(SYSTEM_PROMPT.encode("utf-8")) + len(prompt.encode("utf-8"))
        return max_cost_micros(self._price(), prompt_bytes=size, max_output_tokens=MAX_OUTPUT_TOKENS)

    def typical_reservation(self) -> int | None:
        """Riserva massima di una sintesi: usata per indicare quando sarà di nuovo possibile."""
        try:
            return max_cost_micros(self._price(), prompt_bytes=MAX_PROMPT_BYTES,
                                   max_output_tokens=MAX_OUTPUT_TOKENS)
        except ConfigurationError:
            return None

    def request(self, analysis_id: str, *, confirm_cost: bool, regenerate: bool = False,
                session_id: str = "") -> str:
        if not self.settings.ai_enabled:
            raise ConfigurationError("Sintesi IA non abilitata su questo server")
        if not confirm_cost:
            raise InvalidInput("Conferma esplicita richiesta: la sintesi IA ha un costo")
        analysis = self.store.get_analysis(analysis_id)
        if analysis["status"] != "succeeded":
            raise Conflict("L'analisi non è ancora completata")
        latest = self.store.latest_summary(analysis_id)
        if latest and latest["status"] in ("queued", "running"):
            return latest["id"]
        if latest and latest["status"] == "succeeded" and not regenerate:
            raise Conflict("Esiste già una sintesi per questa analisi")
        since = (datetime.now(UTC) - timedelta(days=1)).isoformat(timespec="seconds")
        if self.store.summaries_created_since(since) >= self.settings.ai_daily_limit:
            raise RetryLater("Limite giornaliero di sintesi IA raggiunto", code="daily_limit",
                             retry_after=3600)
        # Primo controllo all'accodamento; la prenotazione vera avviene prima di ogni chiamata.
        self.budget.ensure_available(self._max_cost(self._prompt(analysis_id)))
        summary_id = self.store.create_summary(analysis_id, PROMPT_VERSION, exclusive=True)
        if summary_id is None:
            raise RetryLater("Un'altra operazione esterna è in corso: riprova tra qualche minuto.",
                             code="busy", retry_after=60)
        self.runner.submit(self.run, summary_id, analysis_id, session_id)
        return summary_id

    def _fail(self, summary_id: str, code: str, message: str) -> None:
        self.store.update_summary(summary_id, status="failed", finished_at=utc_now(),
                                  error_code=code, error_message=message)

    def _call(self, client: LLMClient, price, prompt: str, summary_id: str) -> tuple[dict, dict | None]:
        """Ogni tentativo prenota la propria riserva prima di partire e la riconcilia dopo."""
        reserve = self._max_cost(prompt)
        for attempt in range(1, MAX_ATTEMPTS + 1):
            entry = self.budget.reserve(provider=client.provider, model=client.model,
                                        purpose="summary", ref_id=summary_id, amount=reserve,
                                        attempt=attempt)
            try:
                text, usage = client.chat(SYSTEM_PROMPT, prompt, max_tokens=MAX_OUTPUT_TOKENS)
            except BilledResponseError as exc:
                self.budget.confirm(entry, reserved=reserve, usage=exc.usage,
                                    actual=actual_cost_micros(price, exc.usage) if exc.usage else None)
                raise
            except ProviderUnavailable as exc:
                if exc.billing != "not_billed":
                    # Esito sconosciuto: la riserva resta impegnata e non si ripete la chiamata.
                    self.budget.mark_uncertain(entry, f"esito incerto: {exc.code}")
                    raise
                self.budget.release(entry, f"non fatturata: {exc.code}")
                if attempt == MAX_ATTEMPTS:
                    raise
                log.info("Sintesi %s: nuovo tentativo dopo un errore non fatturato", summary_id)
                self.sleep(RETRY_DELAY_SECONDS)
                continue
            except BaseException:
                self.budget.mark_uncertain(entry, "errore inatteso durante la chiamata")
                raise
            self.budget.confirm(entry, reserved=reserve, usage=usage,
                                actual=actual_cost_micros(price, usage) if usage else None)
            return parse_summary(text), usage
        raise AssertionError("unreachable")

    def run(self, summary_id: str, analysis_id: str, session_id: str = "") -> None:
        self.store.update_summary(summary_id, status="running")
        try:
            # Ricontrollo al momento dell'esecuzione: sessione, configurazione e budget.
            if not self.authorize(session_id):
                raise Unauthorized("Sessione scaduta o revocata prima dell'esecuzione")
            if not self.settings.ai_enabled:
                raise ConfigurationError("Sintesi IA non abilitata su questo server")
            client = self.llm_factory()
            content, usage = self._call(client, self._price(), self._prompt(analysis_id), summary_id)
        except LiaError as exc:
            self._fail(summary_id, exc.code, exc.message)
            return
        except Exception:
            log.exception("Sintesi %s fallita", summary_id)
            self._fail(summary_id, "internal_error", "Errore interno durante la sintesi.")
            return
        self.store.update_summary(summary_id, status="succeeded", finished_at=utc_now(),
                                  model=client.model, content=content, usage=usage)

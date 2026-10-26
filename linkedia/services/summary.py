"""Sintesi IA di un'analisi già calcolata.

La sintesi è un servizio a pagamento: parte solo su richiesta esplicita di un analista,
una volta per analisi (salvo rigenerazione esplicita), entro un limite giornaliero.
Il modello riceve esclusivamente i dati strutturati dell'analisi e deve restituire JSON
con uno schema fisso, validato prima del salvataggio.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from ..config import Settings
from ..errors import ConfigurationError, Conflict, InvalidInput, LiaError, ProviderUnavailable
from ..providers.llm import LLMClient
from ..storage.store import Store, utc_now

log = logging.getLogger(__name__)

PROMPT_VERSION = "summary-v1"

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
                 llm_factory: Callable[[], LLMClient]):
        self.store = store
        self.settings = settings
        self.runner = runner
        self.llm_factory = llm_factory

    def request(self, analysis_id: str, *, confirm_cost: bool, regenerate: bool = False) -> str:
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
            raise Conflict("Limite giornaliero di sintesi IA raggiunto")
        summary_id = self.store.create_summary(analysis_id, PROMPT_VERSION)
        self.runner.submit(self.run, summary_id, analysis_id)
        return summary_id

    def run(self, summary_id: str, analysis_id: str) -> None:
        self.store.update_summary(summary_id, status="running")
        try:
            client = self.llm_factory()
            result = self.store.get_analysis(analysis_id)["result"]
            data, usage = client.complete_json(SYSTEM_PROMPT, build_user_prompt(result),
                                               max_tokens=900)
            content = validate_summary(data)
        except LiaError as exc:
            self.store.update_summary(summary_id, status="failed", finished_at=utc_now(),
                                      error_code=exc.code, error_message=exc.message)
            return
        except Exception:
            log.exception("Sintesi %s fallita", summary_id)
            self.store.update_summary(summary_id, status="failed", finished_at=utc_now(),
                                      error_code="internal_error",
                                      error_message="Errore interno durante la sintesi.")
            return
        self.store.update_summary(summary_id, status="succeeded", finished_at=utc_now(),
                                  model=client.model, content=content, usage=usage)

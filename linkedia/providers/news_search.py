"""Ricerca web delle notizie: Perplexity Search API (`POST /search`).

Restituisce risultati grezzi (titolo, URL, estratto, data di pubblicazione dichiarata) senza testo
generato. Un solo tentativo per chiamata: i retry, ciascuno con la propria riserva di budget,
sono decisi dal servizio. Gli errori distinguono configurazione, autenticazione, limiti,
timeout e indisponibilità, e dichiarano se la richiesta può essere stata fatturata.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Protocol

import requests

from ..domain.news import LANGUAGES
from ..errors import ProviderUnavailable
from .http import new_session
from .llm import _never_sent

log = logging.getLogger(__name__)

# Il provider applica max_results all'intera richiesta (verificato in produzione): si usa il
# massimo documentato, a parità di costo perché la tariffa è per richiesta.
MAX_RESULTS_PER_QUERY = 20
MAX_TOKENS_PER_PAGE = 256
MAX_RESULTS_PER_RESPONSE = 60


class NewsSearchClient(Protocol):
    provider: str
    model: str

    def search(self, queries: list[str], *, published_after: date,
               published_before: date | None) -> list[dict]:
        """Risultati grezzi: dizionari con title, url, snippet, date, last_updated."""
        ...


def _us_date(d: date) -> str:
    return f"{d.month}/{d.day}/{d.year}"


class PerplexitySearchClient:
    provider = "perplexity"
    model = "search"

    def __init__(self, api_key: str, *, base_url: str = "https://api.perplexity.ai", timeout: float = 30,
                 session: requests.Session | None = None):
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or new_session()

    def search(self, queries: list[str], *, published_after: date,
               published_before: date | None) -> list[dict]:
        body = {
            "query": list(queries),
            "max_results": MAX_RESULTS_PER_QUERY,
            "max_tokens_per_page": MAX_TOKENS_PER_PAGE,
            "search_language_filter": list(LANGUAGES),
            "search_after_date_filter": _us_date(published_after),
        }
        if published_before is not None:
            body["search_before_date_filter"] = _us_date(published_before)
        try:
            response = self.session.post(
                f"{self.base_url}/search", json=body, timeout=(10, self.timeout),
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
        except requests.ConnectionError as exc:
            billing = "not_billed" if _never_sent(exc) else "uncertain"
            log.warning("Perplexity non raggiungibile (%s)", type(exc).__name__)
            raise ProviderUnavailable("Servizio di ricerca non raggiungibile", code="provider_unavailable",
                                      billing=billing) from exc
        except requests.RequestException as exc:
            log.warning("Perplexity: richiesta senza esito (%s)", type(exc).__name__)
            raise ProviderUnavailable("Il servizio di ricerca non ha risposto in tempo",
                                      code="provider_timeout", billing="uncertain") from exc

        status = response.status_code
        if status in (401, 403):
            log.warning("Perplexity: credenziali rifiutate (HTTP %s)", status)
            raise ProviderUnavailable("Credenziali del servizio di ricerca non valide",
                                      code="provider_auth", billing="not_billed")
        if status == 429:
            raise ProviderUnavailable("Limite di richieste del servizio di ricerca raggiunto",
                                      code="provider_rate_limited", billing="not_billed")
        if status == 402:
            raise ProviderUnavailable("Credito del servizio di ricerca esaurito",
                                      code="provider_no_credit", billing="not_billed")
        if 400 <= status < 500:
            log.warning("Perplexity: richiesta rifiutata (HTTP %s)", status)
            raise ProviderUnavailable(f"Il servizio di ricerca ha rifiutato la richiesta (HTTP {status})",
                                      code="provider_rejected", billing="not_billed")
        if status != 200:
            log.warning("Perplexity: HTTP %s", status)
            raise ProviderUnavailable(f"Servizio di ricerca non disponibile (HTTP {status})",
                                      code="provider_unavailable", billing="uncertain")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderUnavailable("Risposta del servizio di ricerca non leggibile",
                                      code="provider_invalid_response", billing="billed") from exc
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise ProviderUnavailable("Risposta del servizio di ricerca non conforme",
                                      code="provider_invalid_response", billing="billed")
        # Con più query il provider può restituire una lista per query: si appiattisce.
        flat: list[dict] = []
        for item in results:
            if isinstance(item, list):
                flat.extend(x for x in item if isinstance(x, dict))
            elif isinstance(item, dict):
                flat.append(item)
        return flat[:MAX_RESULTS_PER_RESPONSE]

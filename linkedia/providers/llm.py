"""Modelli linguistici. DeepSeek espone un'API compatibile con OpenAI Chat Completions.

Il client esegue un solo tentativo per chiamata: i retry, ciascuno con la propria riserva di
budget, sono decisi dal servizio chiamante. Ogni errore indica se la richiesta può essere
stata fatturata (`billing`): "not_billed" solo quando è certo che il provider non l'ha
elaborata, "uncertain" in tutti gli altri casi.
"""

from __future__ import annotations

import logging
from typing import Protocol

import requests
from urllib3.exceptions import NameResolutionError, NewConnectionError

from ..errors import ProviderUnavailable
from .http import new_session

log = logging.getLogger(__name__)


class LLMClient(Protocol):
    provider: str
    model: str

    def chat(self, system: str, user: str, *, max_tokens: int) -> tuple[str, dict | None]:
        """Restituisce (testo prodotto dal modello, utilizzo dichiarato dal provider o None)."""
        ...


def _never_sent(exc: requests.ConnectionError) -> bool:
    """Vero se la connessione non è mai stata stabilita (DNS, rifiuto, timeout di connessione)."""
    if isinstance(exc, requests.ConnectTimeout):
        return True
    reason = getattr(exc.args[0], "reason", None) if exc.args else None
    return isinstance(reason, NewConnectionError | NameResolutionError)


class DeepSeekClient:
    provider = "deepseek"

    def __init__(self, api_key: str, *, base_url: str, model: str, timeout: float = 60,
                 session: requests.Session | None = None):
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.session = session or new_session()

    def chat(self, system: str, user: str, *, max_tokens: int) -> tuple[str, dict | None]:
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                timeout=(10, self.timeout),
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}],
                    "response_format": {"type": "json_object"},
                    # Modalità di ragionamento disattivata: nessun token nascosto da pagare.
                    "thinking": {"type": "disabled"},
                    "temperature": 0.2,
                    "max_tokens": max_tokens,
                    "stream": False,
                },
            )
        except requests.ConnectionError as exc:
            billing = "not_billed" if _never_sent(exc) else "uncertain"
            log.warning("DeepSeek non raggiungibile (%s, %s)", type(exc).__name__, billing)
            raise ProviderUnavailable("DeepSeek non raggiungibile", billing=billing) from exc
        except requests.RequestException as exc:  # ReadTimeout e simili: esito sconosciuto
            log.warning("DeepSeek: richiesta senza esito (%s)", type(exc).__name__)
            raise ProviderUnavailable("DeepSeek non ha risposto in tempo", billing="uncertain") from exc

        status = response.status_code
        if 400 <= status < 500:
            # Errori di richiesta, autenticazione, credito o frequenza: non elaborati né fatturati.
            log.warning("DeepSeek: HTTP %s", status)
            raise ProviderUnavailable(f"DeepSeek ha rifiutato la richiesta (HTTP {status})",
                                      code="provider_rejected" if status != 429 else "provider_rate_limited",
                                      billing="not_billed")
        if status >= 500 or status != 200:
            log.warning("DeepSeek: HTTP %s", status)
            raise ProviderUnavailable(f"DeepSeek non disponibile (HTTP {status})", billing="uncertain")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderUnavailable("DeepSeek ha restituito una risposta non JSON",
                                      billing="uncertain") from exc
        usage = payload.get("usage") if isinstance(payload, dict) else None
        usage = usage if isinstance(usage, dict) else None
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BilledResponseError("Il modello IA ha restituito una risposta non valida", usage) from exc
        if not isinstance(content, str):
            raise BilledResponseError("Il modello IA ha restituito una risposta non valida", usage)
        return content, usage


class BilledResponseError(ProviderUnavailable):
    """Risposta HTTP 200 inutilizzabile: la richiesta è stata elaborata e va contabilizzata."""

    def __init__(self, message: str, usage: dict | None):
        super().__init__(message, billing="billed")
        self.usage = usage

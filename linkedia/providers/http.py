"""Richieste HTTP con timeout obbligatorio e retry limitati ai guasti transitori."""

from __future__ import annotations

import logging
import ssl
import time

import requests
import truststore
from requests.adapters import HTTPAdapter

from ..errors import ProviderUnavailable

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}


class _SystemTrustAdapter(HTTPAdapter):
    """Verifica TLS con l'archivio certificati del sistema operativo invece del bundle certifi.

    Serve dove un proxy o un antivirus installa una propria radice attendibile nel sistema:
    la verifica resta attiva, cambia solo l'elenco delle autorità riconosciute.
    """

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return super().init_poolmanager(*args, **kwargs)


def new_session() -> requests.Session:
    session = requests.Session()
    session.mount("https://", _SystemTrustAdapter())
    return session


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    provider: str,
    timeout: float,
    retries: int = 2,
    backoff: float = 1.0,
    **kwargs,
) -> dict:
    """Esegue la richiesta e restituisce il JSON. Solleva ProviderUnavailable in ogni caso di guasto."""
    last_error = ""
    for attempt in range(retries + 1):
        try:
            response = session.request(method, url, timeout=timeout, **kwargs)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = type(exc).__name__
        else:
            if response.status_code in RETRY_STATUS:
                last_error = f"HTTP {response.status_code}"
            elif response.status_code >= 400:
                log.warning("%s: HTTP %s su %s", provider, response.status_code, url)
                raise ProviderUnavailable(
                    f"{provider} ha rifiutato la richiesta (HTTP {response.status_code})"
                )
            else:
                try:
                    return response.json()
                except ValueError as exc:
                    raise ProviderUnavailable(f"{provider} ha restituito una risposta non JSON") from exc
        if attempt < retries:
            time.sleep(backoff * (2**attempt))
    log.warning("%s non disponibile dopo %s tentativi: %s", provider, retries + 1, last_error)
    raise ProviderUnavailable(f"{provider} non disponibile ({last_error})")

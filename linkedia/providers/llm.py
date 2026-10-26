"""Modelli linguistici. DeepSeek espone un'API compatibile con OpenAI Chat Completions."""

from __future__ import annotations

import json
from typing import Protocol

import requests

from ..errors import ProviderUnavailable
from .http import new_session, request_json


class LLMClient(Protocol):
    model: str

    def complete_json(self, system: str, user: str, *, max_tokens: int) -> tuple[dict, dict]:
        """Restituisce (oggetto JSON prodotto dal modello, metadati di utilizzo)."""
        ...


class DeepSeekClient:
    def __init__(self, api_key: str, *, base_url: str, model: str, timeout: float = 60,
                 session: requests.Session | None = None):
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.session = session or new_session()

    def complete_json(self, system: str, user: str, *, max_tokens: int) -> tuple[dict, dict]:
        payload = request_json(
            self.session,
            "POST",
            f"{self.base_url}/chat/completions",
            provider="DeepSeek",
            timeout=self.timeout,
            # Una sola ripetizione: la richiesta è a pagamento.
            retries=1,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": max_tokens,
            },
        )
        try:
            content = payload["choices"][0]["message"]["content"]
            data = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderUnavailable("Il modello IA ha restituito una risposta non valida") from exc
        if not isinstance(data, dict):
            raise ProviderUnavailable("Il modello IA non ha restituito un oggetto JSON")
        return data, payload.get("usage") or {}

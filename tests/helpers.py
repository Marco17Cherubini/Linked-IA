"""Utilità condivise dai test API: provider finti, orologio controllabile, accesso operatore."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from conftest import PASSWORD, fixture_bars
from flask.testing import FlaskClient

from linkedia.api import create_app
from linkedia.config import Settings
from linkedia.errors import ProviderUnavailable
from linkedia.services.jobs import InlineRunner

ORIGIN = "https://localhost"


class FakeMarketData:
    name = "FIXTURE provider"

    def __init__(self, fail=()):
        self.fail = set(fail)
        self.calls = 0

    def daily_bars(self, market, start, end):
        self.calls += 1
        if market.id in self.fail:
            raise ProviderUnavailable("FIXTURE guasto")
        return [b for b in fixture_bars(date(2000, 1, 1), date(2026, 1, 1)) if start <= b.date <= end]


VALID_SUMMARY_TEXT = ('{"headline": "Titolo", "observations": ["a", "b"], "interpretation": "i", '
                      '"limitations": ["campione piccolo", "fonti"]}')
USAGE = {"prompt_tokens": 1000, "completion_tokens": 200, "prompt_cache_hit_tokens": 0,
         "prompt_cache_miss_tokens": 1000}


class FakeLLM:
    """Modello finto: ogni elemento di `script` è un testo da restituire o un'eccezione."""

    provider = "deepseek"
    model = "deepseek-flash"

    def __init__(self, *script, usage=USAGE):
        self.script = list(script) or [VALID_SUMMARY_TEXT]
        self.usage = usage
        self.calls = 0

    def chat(self, system, user, *, max_tokens):
        self.calls += 1
        assert "probabilità" in system  # il prompt vieta di presentare frequenze come probabilità
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, Exception):
            raise item
        return item, self.usage


class Clock:
    def __init__(self, start=datetime(2026, 10, 28, 12, 0, tzinfo=UTC)):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, **delta):
        self.now += timedelta(**delta)


def make_app(settings, market_data=None, llm=None, clock=None, store=None, **overrides):
    if overrides:
        settings = Settings(**{**settings.__dict__, **overrides})
    app = create_app(settings, market_data=market_data or FakeMarketData(), runner=InlineRunner(),
                     llm_factory=(lambda: llm) if llm else None, clock=clock, store=store)
    app.extensions["lia"]["summary"].sleep = lambda seconds: None
    return app


class HttpsClient(FlaskClient):
    """Client di test che parla HTTPS: i cookie Secure vengono conservati e reinviati."""

    def open(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            kwargs.setdefault("base_url", ORIGIN)
        return super().open(*args, **kwargs)


def client_for(app):
    app.test_client_class = HttpsClient
    return app.test_client()


class Operator:
    """Client autenticato che invia Origin e token CSRF come il frontend."""

    def __init__(self, client, password=PASSWORD):
        self.client = client
        r = client.post("/api/auth/login", json={"password": password}, headers={"Origin": ORIGIN})
        assert r.status_code == 200, r.get_json()
        self.csrf = r.get_json()["csrf_token"]
        self.login_response = r

    def post(self, url, json=None, **headers):
        return self.client.post(url, json=json if json is not None else {},
                                headers={"Origin": ORIGIN, "X-CSRF-Token": self.csrf, **headers})

    def get(self, url):
        return self.client.get(url)


def event_payload(event_id="new-event", on="2020-06-10", **extra):
    return {"id": event_id, "title": "Evento di prova", "description": "Descrizione",
            "category": "geopolitical_conflict", "tags": ["war"], "occurred_on": on,
            "sources": [{"url": "https://example.org/a", "publisher": "Example", "title": "A"}],
            **extra}

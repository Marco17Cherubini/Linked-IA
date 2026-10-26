"""API end-to-end con provider finti (nessuna rete, nessun costo)."""

from __future__ import annotations

import importlib
import subprocess
import sys
from datetime import date

import pytest
from conftest import fixture_bars

from linkedia.api import create_app
from linkedia.config import Settings
from linkedia.domain.markets import MARKETS
from linkedia.errors import ProviderUnavailable
from linkedia.services.jobs import InlineRunner

AUTH = {"Authorization": "Bearer test-token"}


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


class FakeLLM:
    model = "fixture-model"

    def __init__(self, data):
        self.data = data
        self.calls = 0

    def complete_json(self, system, user, *, max_tokens):
        self.calls += 1
        assert "probabilità" in system  # il prompt vieta di presentare frequenze come probabilità
        return self.data, {"total_tokens": 1}


VALID_SUMMARY = {"headline": "Titolo", "observations": ["a", "b"], "interpretation": "i",
                 "limitations": ["campione piccolo", "fonti"]}


def make_app(settings, market_data=None, llm=None, **overrides):
    if overrides:
        settings = Settings(**{**settings.__dict__, **overrides})
    return create_app(settings, market_data=market_data or FakeMarketData(), runner=InlineRunner(),
                      llm_factory=(lambda: llm) if llm else None)


def event_payload(event_id="new-event", on="2020-06-10", **extra):
    return {"id": event_id, "title": "Evento di prova", "description": "Descrizione",
            "category": "geopolitical_conflict", "tags": ["war"], "occurred_on": on,
            "sources": [{"url": "https://example.org/a", "publisher": "Example", "title": "A"}],
            **extra}


@pytest.fixture
def client(settings):
    return make_app(settings).test_client()


def test_import_has_no_side_effects_and_needs_no_keys():
    code = ("import socket\n"
            "def boom(*a, **k): raise SystemExit('rete usata')\n"
            "socket.create_connection = boom\n"
            "import linkedia, linkedia.api, linkedia.cli, linkedia.services.summary\n")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            env={"PATH": ""})
    assert result.returncode == 0, result.stderr


def test_meta_and_health(client):
    assert client.get("/api/health").get_json()["status"] == "ok"
    meta = client.get("/api/meta").get_json()
    assert [m["id"] for m in meta["markets"]] == list(MARKETS)
    assert meta["features"] == {"create": True, "ai_summary": False}


def test_create_requires_token(client):
    assert client.post("/api/events", json=event_payload()).status_code == 403
    r = client.post("/api/events", json=event_payload(), headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 403


def test_create_disabled_without_configured_token(settings):
    client = make_app(settings, admin_token=None).test_client()
    r = client.post("/api/events", json=event_payload(), headers=AUTH)
    assert r.status_code == 403 and "disabilitata" in r.get_json()["error"]["message"]


def test_validation_errors_are_readable(client):
    r = client.post("/api/events", json={"id": "Bad Id"}, headers=AUTH)
    assert r.status_code == 400
    body = r.get_json()["error"]
    assert body["code"] == "invalid_input" and "obbligatorio" in body["message"]
    assert "trace" not in r.get_data(as_text=True)


def test_full_flow_create_reopen_identical(client):
    r = client.post("/api/events", json=event_payload(), headers=AUTH)
    assert r.status_code == 202
    analysis_id = r.get_json()["analysis_id"]
    first = client.get(f"/api/analyses/{analysis_id}?market=DAX")
    assert first.status_code == 200
    body = first.get_json()
    assert body["status"] == "succeeded" and body["data"]["market"] == "DAX"
    assert body["event"]["id"] == "new-event"
    again = client.get(f"/api/analyses/{analysis_id}?market=DAX")
    assert again.get_json() == body
    cached = client.get(f"/api/analyses/{analysis_id}?market=DAX",
                        headers={"If-None-Match": first.headers["ETag"]})
    assert cached.status_code == 304


def test_as_of_view_hides_outcomes(client):
    analysis_id = client.post("/api/events", json=event_payload(), headers=AUTH).get_json()["analysis_id"]
    data = client.get(f"/api/analyses/{analysis_id}?view=as_of").get_json()["data"]
    assert "outcomes" not in data
    assert max(p["s"] for p in data["target_path"]) == 0


def test_invalid_query_params(client):
    analysis_id = client.post("/api/events", json=event_payload(), headers=AUTH).get_json()["analysis_id"]
    assert client.get(f"/api/analyses/{analysis_id}?market=XYZ").status_code == 400
    assert client.get(f"/api/analyses/{analysis_id}?view=future").status_code == 400
    assert client.get("/api/analyses?page_size=500").status_code == 400
    assert client.get("/api/analyses?from=ieri").status_code == 400


def test_duplicate_and_future_events_are_rejected(client):
    client.post("/api/events", json=event_payload(), headers=AUTH)
    assert client.post("/api/events", json=event_payload(), headers=AUTH).status_code == 409
    future = event_payload("future-event", on="2999-01-01")
    assert client.post("/api/events", json=future, headers=AUTH).status_code == 400


def test_provider_failure_is_visible_not_empty(settings):
    client = make_app(settings, market_data=FakeMarketData(fail=set(MARKETS))).test_client()
    analysis_id = client.post("/api/events", json=event_payload(), headers=AUTH).get_json()["analysis_id"]
    body = client.get(f"/api/analyses/{analysis_id}").get_json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "provider_unavailable"
    assert body["data"] is None


def test_partial_provider_failure_marks_market(settings):
    client = make_app(settings, market_data=FakeMarketData(fail={"NIKKEI"})).test_client()
    analysis_id = client.post("/api/events", json=event_payload(), headers=AUTH).get_json()["analysis_id"]
    body = client.get(f"/api/analyses/{analysis_id}?market=NIKKEI").get_json()
    assert body["status"] == "succeeded"
    nikkei = next(m for m in body["markets"] if m["id"] == "NIKKEI")
    assert nikkei["status"] == "unavailable" and nikkei["error"]["code"] == "provider_unavailable"
    assert body["data"] is None


def test_archive_filters_and_pagination(client):
    for i in range(3):
        client.post("/api/events", json=event_payload(f"e{i}", on=f"2020-0{i + 4}-10"), headers=AUTH)
    page = client.get("/api/analyses?page_size=2&page=2").get_json()
    assert page["total"] == 3 and page["pages"] == 2 and len(page["items"]) == 1
    assert client.get("/api/analyses?from=2020-05-01").get_json()["total"] == 2
    assert client.get("/api/analyses?status=failed").get_json()["total"] == 0
    assert client.get("/api/events?q=prova").get_json()["total"] == 3


def test_summary_requires_ai_configuration_and_confirmation(settings):
    llm = FakeLLM(VALID_SUMMARY)
    client = make_app(settings, llm=llm).test_client()
    analysis_id = client.post("/api/events", json=event_payload(), headers=AUTH).get_json()["analysis_id"]
    r = client.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True}, headers=AUTH)
    assert r.status_code == 503  # chiave IA non configurata
    assert llm.calls == 0

    client = make_app(settings, llm=llm, deepseek_api_key="k").test_client()
    assert client.post(f"/api/analyses/{analysis_id}/summary", json={}, headers=AUTH).status_code == 400
    assert client.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True}).status_code == 403
    r = client.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True}, headers=AUTH)
    assert r.status_code == 202 and llm.calls == 1
    summary = client.get(f"/api/analyses/{analysis_id}").get_json()["summary"]
    assert summary["status"] == "succeeded" and summary["content"]["headline"] == "Titolo"
    # ripetere la richiesta non genera un'altra chiamata a pagamento
    assert client.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True},
                       headers=AUTH).status_code == 409
    assert llm.calls == 1
    # consultare l'analisi non chiama il modello
    for market in MARKETS:
        client.get(f"/api/analyses/{analysis_id}?market={market}")
    assert llm.calls == 1


def test_invalid_summary_is_stored_as_failure(settings):
    llm = FakeLLM({"headline": "solo titolo"})
    client = make_app(settings, llm=llm, deepseek_api_key="k").test_client()
    analysis_id = client.post("/api/events", json=event_payload(), headers=AUTH).get_json()["analysis_id"]
    client.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True}, headers=AUTH)
    summary = client.get(f"/api/analyses/{analysis_id}").get_json()["summary"]
    assert summary["status"] == "failed" and summary["content"] is None


def test_interrupted_jobs_fail_on_restart(settings):
    app = make_app(settings)
    store = app.extensions["lia"]["store"]
    app.test_client().post("/api/events", json=event_payload(), headers=AUTH)
    stuck = store.create_analysis("new-event", "2.0.0")
    make_app(settings)  # riavvio
    assert store.get_analysis(stuck)["status"] == "failed"
    assert store.get_analysis(stuck)["error_code"] == "interrupted"


def test_unknown_api_route_is_json(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "http_404"


def test_catalogue_is_valid():
    module = importlib.import_module("linkedia.services.analysis")
    events = module.load_catalogue()
    assert len(events) >= 30
    assert len({e.id for e in events}) == len(events)
    assert all(e.sources for e in events)

"""API end-to-end con provider finti (nessuna rete, nessun costo)."""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest
from helpers import FakeLLM, FakeMarketData, Operator, client_for, event_payload, make_app

from linkedia.domain.markets import MARKETS


@pytest.fixture
def client(settings):
    return client_for(make_app(settings))


@pytest.fixture
def op(client):
    return Operator(client)


def test_import_has_no_side_effects_and_needs_no_keys():
    code = ("import socket\n"
            "def boom(*a, **k): raise SystemExit('rete usata')\n"
            "socket.create_connection = boom\n"
            "import linkedia, linkedia.api, linkedia.cli, linkedia.services.summary\n")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            env={"PATH": ""})
    assert result.returncode == 0, result.stderr


def test_meta_and_health(client):
    health = client.get("/api/health")
    assert health.get_json() == {"status": "ok"}  # nessuna versione o dettaglio interno
    meta = client.get("/api/meta").get_json()
    assert [m["id"] for m in meta["markets"]] == list(MARKETS)
    assert meta["features"] == {"create": True, "ai_summary": False, "login": True, "news_search": False}
    assert "operator_password_hash" not in str(meta)


def test_validation_errors_are_readable(op):
    r = op.post("/api/events", json={"id": "Bad Id"})
    assert r.status_code == 400
    body = r.get_json()["error"]
    assert body["code"] == "invalid_input" and "obbligatorio" in body["message"]
    assert "Traceback" not in r.get_data(as_text=True)


def test_body_must_be_json_and_bounded(op):
    r = op.client.post("/api/events", data="id=x", headers={"Origin": "https://localhost",
                                                           "X-CSRF-Token": op.csrf,
                                                           "Content-Type": "text/plain"})
    assert r.status_code == 400
    big = event_payload(description="x" * 70_000)
    assert op.post("/api/events", json=big).status_code == 413


def test_full_flow_create_reopen_identical(op):
    r = op.post("/api/events", json=event_payload())
    assert r.status_code == 202
    analysis_id = r.get_json()["analysis_id"]
    first = op.get(f"/api/analyses/{analysis_id}?market=DAX")
    assert first.status_code == 200
    body = first.get_json()
    assert body["status"] == "succeeded" and body["data"]["market"] == "DAX"
    assert body["event"]["id"] == "new-event" and body["public"] is False
    assert op.get(f"/api/analyses/{analysis_id}?market=DAX").get_json() == body
    cached = op.client.get(f"/api/analyses/{analysis_id}?market=DAX",
                           headers={"If-None-Match": first.headers["ETag"]})
    assert cached.status_code == 304
    assert "private" in first.headers["Cache-Control"]


def test_as_of_view_hides_outcomes(op):
    analysis_id = op.post("/api/events", json=event_payload()).get_json()["analysis_id"]
    data = op.get(f"/api/analyses/{analysis_id}?view=as_of").get_json()["data"]
    assert "outcomes" not in data
    assert max(p["s"] for p in data["target_path"]) == 0


def test_invalid_query_params(op):
    analysis_id = op.post("/api/events", json=event_payload()).get_json()["analysis_id"]
    assert op.get(f"/api/analyses/{analysis_id}?market=XYZ").status_code == 400
    assert op.get(f"/api/analyses/{analysis_id}?view=future").status_code == 400
    assert op.get("/api/analyses?page_size=500").status_code == 400
    assert op.get("/api/analyses?from=ieri").status_code == 400
    assert op.get("/api/events?page=999999").status_code == 400


def test_duplicate_and_future_events_are_rejected(op):
    op.post("/api/events", json=event_payload())
    assert op.post("/api/events", json=event_payload()).status_code == 409
    assert op.post("/api/events", json=event_payload("future-event", on="2999-01-01")).status_code == 400


def test_source_urls_must_be_http(op):
    bad = event_payload(sources=[{"url": "javascript:alert(1)"}])
    assert op.post("/api/events", json=bad).status_code == 400


def test_provider_failure_is_visible_not_empty(settings):
    op = Operator(client_for(make_app(settings, market_data=FakeMarketData(fail=set(MARKETS)))))
    analysis_id = op.post("/api/events", json=event_payload()).get_json()["analysis_id"]
    body = op.get(f"/api/analyses/{analysis_id}").get_json()
    assert body["status"] == "failed"
    assert body["error"]["code"] == "provider_unavailable"
    assert body["data"] is None


def test_partial_provider_failure_marks_market(settings):
    op = Operator(client_for(make_app(settings, market_data=FakeMarketData(fail={"NIKKEI"}))))
    analysis_id = op.post("/api/events", json=event_payload()).get_json()["analysis_id"]
    body = op.get(f"/api/analyses/{analysis_id}?market=NIKKEI").get_json()
    assert body["status"] == "succeeded"
    nikkei = next(m for m in body["markets"] if m["id"] == "NIKKEI")
    assert nikkei["status"] == "unavailable" and nikkei["error"]["code"] == "provider_unavailable"
    assert body["data"] is None


def test_archive_filters_and_pagination(op):
    for i in range(3):
        op.post("/api/events", json=event_payload(f"e{i}", on=f"2020-0{i + 4}-10"))
    page = op.get("/api/analyses?page_size=2&page=2").get_json()
    assert page["total"] == 3 and page["pages"] == 2 and len(page["items"]) == 1
    assert op.get("/api/analyses?from=2020-05-01").get_json()["total"] == 2
    assert op.get("/api/analyses?status=failed").get_json()["total"] == 0
    assert op.get("/api/events?q=prova").get_json()["total"] == 3


def test_summary_requires_ai_configuration_and_confirmation(settings):
    llm = FakeLLM()
    op = Operator(client_for(make_app(settings, llm=llm)))
    analysis_id = op.post("/api/events", json=event_payload()).get_json()["analysis_id"]
    r = op.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True})
    assert r.status_code == 503  # chiave IA non configurata
    assert llm.calls == 0

    op = Operator(client_for(make_app(settings, llm=llm, deepseek_api_key="k")))
    assert op.post(f"/api/analyses/{analysis_id}/summary", json={}).status_code == 400
    r = op.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True})
    assert r.status_code == 202 and llm.calls == 1
    summary = op.get(f"/api/analyses/{analysis_id}").get_json()["summary"]
    assert summary["status"] == "succeeded" and summary["content"]["headline"] == "Titolo"
    # ripetere la richiesta non genera un'altra chiamata a pagamento
    assert op.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True}).status_code == 409
    assert llm.calls == 1
    # consultare l'analisi non chiama il modello
    for market in MARKETS:
        op.get(f"/api/analyses/{analysis_id}?market={market}")
    assert llm.calls == 1


def test_invalid_summary_is_stored_as_failure_and_still_accounted(settings):
    llm = FakeLLM('{"headline": "solo titolo"}')
    app = make_app(settings, llm=llm, deepseek_api_key="k")
    op = Operator(client_for(app))
    analysis_id = op.post("/api/events", json=event_payload()).get_json()["analysis_id"]
    op.post(f"/api/analyses/{analysis_id}/summary", json={"confirm_cost": True})
    summary = op.get(f"/api/analyses/{analysis_id}").get_json()["summary"]
    assert summary["status"] == "failed" and summary["content"] is None
    entries = app.extensions["lia"]["store"].spend_entries_since("2000-01-01")
    assert [e["status"] for e in entries] == ["confirmed"]  # la risposta è stata pagata


def test_interrupted_jobs_fail_on_restart(settings):
    app = make_app(settings)
    store = app.extensions["lia"]["store"]
    Operator(client_for(app)).post("/api/events", json=event_payload())
    stuck = store.create_analysis("new-event", "2.0.0")
    make_app(settings)  # riavvio
    assert store.get_analysis(stuck)["status"] == "failed"
    assert store.get_analysis(stuck)["error_code"] == "interrupted"


def test_one_external_job_at_a_time(settings):
    app = make_app(settings)
    store = app.extensions["lia"]["store"]
    op = Operator(client_for(app))
    op.post("/api/events", json=event_payload("first"))
    store.create_analysis("first", "2.0.0")  # job ancora in coda
    r = op.post("/api/events", json=event_payload("second"))
    assert r.status_code == 429 and r.get_json()["error"]["code"] == "busy"
    assert r.headers["Retry-After"] == "60"
    assert not store.event_exists("second")  # rifiutato prima di salvare


def test_event_list_links_latest_succeeded_analysis(settings):
    app = make_app(settings)
    op = Operator(client_for(app))
    good = op.post("/api/events", json=event_payload()).get_json()["analysis_id"]
    store = app.extensions["lia"]["store"]
    failed = store.create_analysis("new-event", "2.0.0")
    store.fail_analysis(failed, "provider_unavailable", "FIXTURE")
    item = op.get("/api/events").get_json()["items"][0]
    assert item["analysis_id"] == good and item["analysis_status"] == "succeeded"


def test_unknown_api_route_is_json(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.get_json()["error"]["code"] == "http_404"


def test_security_headers_and_https_only_hsts(client, settings):
    r = client.get("/api/meta")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Strict-Transport-Security"].startswith("max-age=")
    assert "Cookie" in r.headers["Vary"]
    plain = make_app(settings).test_client().get("/api/meta")
    assert "Strict-Transport-Security" not in plain.headers
    assert "Access-Control-Allow-Origin" not in r.headers


def test_www_redirects_to_canonical_host(settings):
    client = make_app(settings, canonical_host="example.test").test_client()
    r = client.get("/archive?q=1", base_url="https://www.example.test")
    assert r.status_code == 301 and r.headers["Location"] == "https://example.test/archive?q=1"
    assert client.get("/api/health", base_url="https://example.test").status_code == 200


def test_proxy_headers_trusted_only_when_configured(settings):
    app = make_app(settings, proxy_hops=1)
    client = app.test_client()
    r = client.get("/api/meta", headers={"X-Forwarded-Proto": "https"})
    assert "Strict-Transport-Security" in r.headers
    untrusted = make_app(settings).test_client().get("/api/meta", headers={"X-Forwarded-Proto": "https"})
    assert "Strict-Transport-Security" not in untrusted.headers


def test_catalogue_is_valid_and_public():
    module = importlib.import_module("linkedia.services.analysis")
    events = module.load_catalogue()
    assert len(events) >= 30
    assert len({e.id for e in events}) == len(events)
    assert all(e.sources for e in events)
    assert all(e.public for e in events)


class LateStartMarketData(FakeMarketData):
    """Serie che inizia dopo la data richiesta: la copertura non è mai completa."""

    def daily_bars(self, market, start, end):
        return [b for b in super().daily_bars(market, start, end) if b.date.year >= 2019]


def test_prices_are_not_downloaded_again_for_every_analysis(settings):
    market = LateStartMarketData()
    app = make_app(settings, market_data=market)
    analysis = app.extensions["lia"]["analysis"]
    analysis.import_catalogue()
    for event_id in ("sept11-attacks-2001", "iraq-invasion-2003", "lehman-bankruptcy-2008"):
        analysis.request_analysis(event_id)
    assert market.calls == len(MARKETS)

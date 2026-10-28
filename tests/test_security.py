"""Accesso operatore, CSRF, percorsi legacy e isolamento dei dati privati (offline, senza costi)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest
from conftest import PASSWORD, make_event
from helpers import (
    ORIGIN,
    Clock,
    FakeLLM,
    FakeMarketData,
    Operator,
    client_for,
    event_payload,
    make_app,
)

from linkedia.services.auth import MAX_FAILURES_PER_CLIENT, hash_password

PROTECTED = [
    ("/api/events", event_payload()),
    ("/api/events/new-event/analyses", {}),
    ("/api/analyses/x/summary", {"confirm_cost": True}),
    ("/api/auth/logout", {}),
]


def login(client, password=PASSWORD, origin=ORIGIN):
    return client.post("/api/auth/login", json={"password": password}, headers={"Origin": origin})


# 1. Un anonimo non può avviare una ricerca con una chiamata HTTP diretta.
@pytest.mark.parametrize("url, body", PROTECTED)
def test_anonymous_cannot_start_external_work(settings, url, body):
    market, llm = FakeMarketData(), FakeLLM()
    client = client_for(make_app(settings, market_data=market, llm=llm, deepseek_api_key="k"))
    r = client.post(url, json=body, headers={"Origin": ORIGIN})
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "unauthorized"
    assert market.calls == 0 and llm.calls == 0
    assert client.get("/api/operator/budget").status_code == 401


# 2. Password errata rifiutata e tentativi limitati, anche dopo un riavvio.
def test_wrong_password_rejected_and_attempts_limited(settings):
    client = client_for(make_app(settings))
    r = login(client, "sbagliata")
    assert r.status_code == 401 and r.get_json()["error"]["code"] == "invalid_credentials"
    assert "argon" not in r.get_data(as_text=True).lower()
    assert "Set-Cookie" not in r.headers
    for _ in range(MAX_FAILURES_PER_CLIENT - 1):
        login(client, "sbagliata")
    blocked = login(client)  # anche la password giusta è respinta durante il blocco
    assert blocked.status_code == 429 and int(blocked.headers["Retry-After"]) > 0
    restarted = client_for(make_app(settings))
    assert login(restarted).status_code == 429


def test_global_attempt_limit_does_not_depend_on_ip(settings):
    app = make_app(settings, proxy_hops=1)
    client = app.test_client()
    for i in range(20):
        client.post("/api/auth/login", json={"password": "x"},
                    headers={"X-Forwarded-For": f"10.0.0.{i}", "X-Forwarded-Proto": "https"})
    r = client.post("/api/auth/login", json={"password": PASSWORD},
                    headers={"X-Forwarded-For": "10.9.9.9", "X-Forwarded-Proto": "https"})
    assert r.status_code == 429


def test_attempts_store_no_raw_ip(settings):
    app = make_app(settings, proxy_hops=1)
    app.test_client().post("/api/auth/login", json={"password": "x"},
                           headers={"X-Forwarded-For": "203.0.113.7", "X-Forwarded-Proto": "https"})
    with app.extensions["lia"]["store"].connect() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM login_attempts")]
    assert rows and "203.0.113.7" not in str(rows)


# 3. Password corretta: sessione valida con cookie sicuro.
def test_correct_password_creates_secure_session(settings):
    client = client_for(make_app(settings))
    op = Operator(client)
    cookie = op.login_response.headers["Set-Cookie"]
    assert cookie.startswith("__Host-lia_session=")
    for attribute in ("Secure", "HttpOnly", "SameSite=Strict", "Path=/", "Max-Age=28800"):
        assert attribute in cookie
    assert "Domain" not in cookie
    session = client.get("/api/auth/session").get_json()
    assert session["authenticated"] is True and session["csrf_token"] == op.csrf
    # il token di sessione non compare nel corpo della risposta
    token = cookie.split(";")[0].split("=", 1)[1]
    assert token not in op.login_response.get_data(as_text=True)
    assert client.get("/api/operator/budget").status_code == 200


# 4. Logout e scadenza invalidano l'accesso.
def test_logout_invalidates_session_server_side(settings):
    app = make_app(settings)
    client = client_for(app)
    op = Operator(client)
    stolen = op.login_response.headers["Set-Cookie"].split(";")[0].split("=", 1)[1]
    assert op.post("/api/auth/logout").status_code == 200
    other = client_for(app)
    other.set_cookie("__Host-lia_session", stolen, domain="localhost")
    assert other.get("/api/auth/session").get_json() == {"authenticated": False}
    assert other.post("/api/events", json=event_payload(),
                      headers={"Origin": ORIGIN, "X-CSRF-Token": op.csrf}).status_code == 401


def test_session_expires_after_eight_hours(settings):
    clock = Clock()
    op = Operator(client_for(make_app(settings, clock=clock)))
    clock.advance(hours=7, minutes=59)
    assert op.get("/api/operator/budget").status_code == 200
    clock.advance(minutes=2)
    assert op.get("/api/operator/budget").status_code == 401


def test_sessions_revoked_by_epoch_or_password_change(settings):
    op = Operator(client_for(make_app(settings)))
    cookie = op.login_response.headers["Set-Cookie"].split(";")[0].split("=", 1)[1]
    for change in ({"session_epoch": "2"}, {"operator_password_hash": hash_password("altra-password-99")}):
        client = client_for(make_app(settings, **change))
        client.set_cookie("__Host-lia_session", cookie, domain="localhost")
        assert client.get("/api/auth/session").get_json()["authenticated"] is False


# 5. Richieste mutative senza protezione CSRF rifiutate.
def test_mutations_without_csrf_are_rejected(settings):
    market = FakeMarketData()
    op = Operator(client_for(make_app(settings, market_data=market)))
    no_token = op.client.post("/api/events", json=event_payload(), headers={"Origin": ORIGIN})
    wrong = op.client.post("/api/events", json=event_payload(),
                           headers={"Origin": ORIGIN, "X-CSRF-Token": "x" * 43})
    cross = op.client.post("/api/events", json=event_payload(),
                           headers={"Origin": "https://evil.example", "X-CSRF-Token": op.csrf})
    for r in (no_token, wrong, cross):
        assert r.status_code == 403 and r.get_json()["error"]["code"] == "csrf"
    assert market.calls == 0
    assert login(op.client, origin="https://evil.example").status_code == 403


# 6. Nessun percorso legacy aggira l'autorizzazione.
def test_legacy_bearer_token_is_ignored(settings, monkeypatch):
    monkeypatch.setenv("LIA_ADMIN_TOKEN", "legacy-token")
    client = client_for(make_app(settings))
    r = client.post("/api/events", json=event_payload(),
                    headers={"Authorization": "Bearer legacy-token", "Origin": ORIGIN})
    assert r.status_code == 401


def test_every_mutating_api_route_requires_a_session(settings):
    app = make_app(settings)
    client = client_for(app)
    rules = [r for r in app.url_map.iter_rules()
             if r.rule.startswith("/api/") and r.methods - {"GET", "HEAD", "OPTIONS"}]
    assert {r.rule for r in rules} == {"/api/auth/login", "/api/auth/logout", "/api/events",
                                       "/api/events/<event_id>/analyses",
                                       "/api/analyses/<analysis_id>/summary", "/api/news/searches",
                                       "/api/news/searches/<search_id>/events/<int:idx>/analyze"}
    for rule in rules:
        if rule.rule == "/api/auth/login":
            continue
        url = (rule.rule.replace("<event_id>", "x").replace("<analysis_id>", "x")
               .replace("<search_id>", "x").replace("<int:idx>", "0"))
        assert client.post(url, json={}, headers={"Origin": ORIGIN}).status_code == 401, url


# 13. I dati privati non compaiono negli endpoint pubblici.
def test_private_data_hidden_from_public_endpoints(settings):
    app = make_app(settings)
    store = app.extensions["lia"]["store"]
    store.upsert_event(replace(make_event("public-case"), public=True))
    op = Operator(client_for(app))
    created = op.post("/api/events", json=event_payload("private-case", on="2021-06-10"))
    private_id = created.get_json()["analysis_id"]
    anon = client_for(app)
    assert [e["id"] for e in anon.get("/api/events").get_json()["items"]] == ["public-case"]
    assert all(a["event_id"] != "private-case" for a in anon.get("/api/analyses").get_json()["items"])
    assert anon.get("/api/events/private-case").status_code == 404
    assert anon.get(f"/api/analyses/{private_id}").status_code == 404
    assert "private-case" not in anon.get("/api/events?q=prova").get_data(as_text=True)
    # l'operatore vede entrambi
    assert op.get("/api/events").get_json()["total"] == 2


def test_public_case_never_uses_private_events_as_precedents(settings):
    app = make_app(settings)
    store, analysis = app.extensions["lia"]["store"], app.extensions["lia"]["analysis"]
    store.upsert_event(replace(make_event("public-case", on=date(2022, 6, 10)), public=True))
    Operator(client_for(app)).post("/api/events", json=event_payload("private-old", on="2015-06-10"))
    analysis_id = analysis.request_analysis("public-case")
    result = store.get_analysis(analysis_id)["result"]
    ids = {p["event_id"] for m in result["markets"].values() for p in m["precedents"]["items"]}
    assert "private-old" not in ids


# 14. Mancanza di segreti o del database del budget disabilita le funzioni a pagamento.
def test_missing_password_hash_disables_reserved_features(settings):
    market, llm = FakeMarketData(), FakeLLM()
    client = client_for(make_app(settings, market_data=market, llm=llm, deepseek_api_key="k",
                                 operator_password_hash=None))
    meta = client.get("/api/meta").get_json()
    assert meta["features"] == {"create": False, "ai_summary": False, "login": False,
                                "news_search": False}
    assert login(client).status_code == 503
    r = client.post("/api/events", json=event_payload(), headers={"Origin": ORIGIN})
    assert r.status_code == 503 and market.calls == 0 and llm.calls == 0


def test_unpriced_model_disables_ai(settings):
    client = client_for(make_app(settings, deepseek_api_key="k", deepseek_model="modello-ignoto"))
    assert client.get("/api/meta").get_json()["features"]["ai_summary"] is False


def test_unavailable_budget_database_blocks_paid_call(settings, tmp_path):
    from linkedia.errors import PersistenceError
    from linkedia.services.budget import BudgetService
    from linkedia.storage.store import Store

    folder = tmp_path / "not-a-db"
    folder.mkdir()
    budget = BudgetService(Store(folder), settings)
    with pytest.raises(PersistenceError):
        budget.reserve(provider="deepseek", model="deepseek-flash", purpose="summary", ref_id=None,
                       amount=10)


def test_health_reports_database_failure_without_details(settings, tmp_path):
    app = make_app(settings)
    app.extensions["lia"]["store"].path = tmp_path / "missing-dir" / "x.sqlite3"
    r = app.test_client().get("/api/health")
    assert r.status_code == 503 and r.get_json() == {"status": "unavailable"}


def test_job_rechecks_session_when_it_runs(settings):
    """Una sessione chiusa tra accodamento ed esecuzione blocca il job prima del provider."""
    llm = FakeLLM()
    app = make_app(settings, llm=llm, deepseek_api_key="k")
    services = app.extensions["lia"]
    services["store"].upsert_event(replace(make_event("public-case"), public=True))
    analysis_id = services["analysis"].request_analysis("public-case")
    op = Operator(client_for(app))
    token = op.login_response.headers["Set-Cookie"].split(";")[0].split("=", 1)[1]
    session_id = services["auth"].session(token)["id"]
    summary_id = services["store"].create_summary(analysis_id, "summary-v1")
    services["auth"].logout(session_id)
    services["summary"].run(summary_id, analysis_id, session_id)
    assert llm.calls == 0
    assert services["store"].latest_summary(analysis_id)["error_code"] == "unauthorized"

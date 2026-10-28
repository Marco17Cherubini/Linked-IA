"""Contabilità della spesa: prenotazione atomica, retry, esiti incerti, blocco e persistenza."""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import timedelta

import pytest
from conftest import make_event
from helpers import Clock, FakeLLM, Operator, client_for, make_app

from linkedia.errors import ProviderUnavailable, RetryLater
from linkedia.services.budget import (
    PRICING,
    BudgetService,
    actual_cost_micros,
    max_cost_micros,
    usd,
)
from linkedia.services.summary import MAX_OUTPUT_TOKENS
from linkedia.storage.store import Store

FLASH = PRICING[("deepseek", "deepseek-flash")]


def test_costs_are_integer_micro_usd_rounded_up():
    assert max_cost_micros(FLASH, prompt_bytes=1000, max_output_tokens=900) == (
        -(-(1064 * 300_000) // 1_000_000) + 900 * 1_200_000 // 1_000_000)
    assert actual_cost_micros(FLASH, {"prompt_tokens": 1, "completion_tokens": 1}) == 1 + 2
    usage = {"prompt_tokens": 1000, "completion_tokens": 10, "prompt_cache_hit_tokens": 400,
             "prompt_cache_miss_tokens": 600, "completion_tokens_details": {"reasoning_tokens": 5}}
    assert actual_cost_micros(FLASH, usage) == 3 + 180 + 18
    assert actual_cost_micros(FLASH, {"total_tokens": 3}) is None
    assert usd(3_000_000) == "3.000000" and usd(1) == "0.000001"


def test_budget_setting_parses_decimal_without_float(monkeypatch):
    from linkedia.config import Settings

    monkeypatch.setenv("LIA_API_BUDGET_USD", "0.30")
    assert Settings.from_env(load_dotenv_file=False).api_budget_micros == 300_000


def public_analysis(app):
    """Caso pubblico già calcolato (prezzi finti, nessuna IA)."""
    store, analysis = app.extensions["lia"]["store"], app.extensions["lia"]["analysis"]
    store.upsert_event(replace(make_event("public-case"), public=True))
    return analysis.request_analysis("public-case")


def ai_app(settings, llm, clock=None, **overrides):
    return make_app(settings, llm=llm, clock=clock, deepseek_api_key="k", **overrides)


def entries(app):
    return app.extensions["lia"]["store"].spend_entries_since("2000-01-01")


def request_summary(op, analysis_id, regenerate=False):
    return op.post(f"/api/analyses/{analysis_id}/summary",
                   json={"confirm_cost": True, "regenerate": regenerate})


# 7. Budget esaurito: il provider non viene invocato.
def test_exhausted_budget_never_invokes_provider(settings):
    llm = FakeLLM()
    app = ai_app(settings, llm, api_budget_micros=100)  # 0,0001 USD: meno di una riserva
    analysis_id = public_analysis(app)
    op = Operator(client_for(app))
    r = request_summary(op, analysis_id)
    assert r.status_code == 429
    error = r.get_json()["error"]
    assert error["code"] in ("budget_blocked", "budget_exceeded")
    assert llm.calls == 0 and entries(app) == []


def test_reservation_is_checked_again_when_job_runs(settings):
    """Il controllo all'accodamento non basta: il job prenota prima di chiamare."""
    llm = FakeLLM()
    app = ai_app(settings, llm)
    analysis_id = public_analysis(app)
    services = app.extensions["lia"]
    store = services["store"]
    summary_id = store.create_summary(analysis_id, "summary-v1")
    services["budget"].settings = replace(settings, api_budget_micros=10)
    services["summary"].authorize = lambda session_id: True  # sessione valida (vedi test_security)
    services["summary"].run(summary_id, analysis_id, "")
    assert llm.calls == 0
    assert store.latest_summary(analysis_id)["error_code"] == "budget_blocked"


# 8. Richieste simultanee non oltrepassano le riserve disponibili.
def test_concurrent_reservations_never_exceed_budget(settings):
    store = Store(settings.database_path)
    store.initialize()
    capped = replace(settings, api_budget_micros=10_000)
    results, barrier = [], threading.Barrier(12)

    def worker():
        # Ogni thread usa un proprio Store sullo stesso file, come processi distinti.
        budget = BudgetService(Store(settings.database_path), capped)
        barrier.wait()
        try:
            budget.reserve(provider="deepseek", model="deepseek-flash", purpose="t", ref_id=None,
                           amount=3_000)
            results.append("ok")
        except RetryLater:
            results.append("refused")

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 3
    assert sum(e["committed_micros"] for e in store.spend_entries_since("2000-01-01")) == 9_000


# 9. I retry vengono contabilizzati, ciascuno con la propria riserva.
def test_retries_are_individually_reserved(settings):
    llm = FakeLLM(ProviderUnavailable("rate", code="provider_rate_limited", billing="not_billed"),
                  '{"headline": "T", "observations": ["a"], "interpretation": "i", "limitations": ["l"]}')
    app = ai_app(settings, llm)
    analysis_id = public_analysis(app)
    assert request_summary(Operator(client_for(app)), analysis_id).status_code == 202
    ledger = entries(app)
    assert llm.calls == 2
    assert [(e["attempt"], e["status"]) for e in ledger] == [(1, "released"), (2, "confirmed")]
    assert ledger[1]["actual_micros"] == actual_cost_micros(FLASH, llm.usage)


def test_retry_passes_through_the_budget_check_again(settings):
    llm = FakeLLM(ProviderUnavailable("rate", billing="not_billed"), "{}")
    app = ai_app(settings, llm)
    analysis_id = public_analysis(app)
    services = app.extensions["lia"]
    summary = services["summary"]
    # Tra il primo e il secondo tentativo un'altra spesa esaurisce il budget.
    summary.sleep = lambda seconds: services["budget"].reserve(
        provider="deepseek", model="deepseek-flash", purpose="altro", ref_id=None,
        amount=settings.api_budget_micros)
    summary_id = services["store"].create_summary(analysis_id, "summary-v1")
    summary.authorize = lambda session_id: True
    summary.run(summary_id, analysis_id, "")
    assert llm.calls == 1
    assert app.extensions["lia"]["store"].latest_summary(analysis_id)["error_code"] == "budget_blocked"


# 10. Timeout con fatturazione incerta: la riserva non viene liberata e non si ripete.
def test_uncertain_timeout_keeps_reservation(settings):
    llm = FakeLLM(ProviderUnavailable("timeout", billing="uncertain"))
    app = ai_app(settings, llm)
    analysis_id = public_analysis(app)
    request_summary(Operator(client_for(app)), analysis_id)
    ledger = entries(app)
    assert llm.calls == 1
    assert [e["status"] for e in ledger] == ["uncertain"]
    assert ledger[0]["committed_micros"] == ledger[0]["reserved_micros"] > 0
    make_app(settings)  # un riavvio non la libera
    assert [e["status"] for e in entries(app)] == ["uncertain"]


def test_crash_leaves_reservation_committed(settings):
    app = ai_app(settings, FakeLLM())
    budget = app.extensions["lia"]["budget"]
    budget.reserve(provider="deepseek", model="deepseek-flash", purpose="summary", ref_id="x",
                   amount=5_000)  # processo terminato prima della risposta
    make_app(settings)
    [entry] = entries(app)
    assert entry["status"] == "uncertain" and entry["committed_micros"] == 5_000


# 11 e 12. Riavvio e redeploy non azzerano spesa e blocco; dopo un'ora il blocco resta se il
# budget delle ultime 24 ore è ancora esaurito.
def test_block_survives_restart_and_is_not_reset_after_one_hour(settings):
    clock = Clock()
    llm = FakeLLM()
    app = ai_app(settings, llm, clock=clock)
    analysis_id = public_analysis(app)
    app.extensions["lia"]["budget"].reserve(provider="deepseek", model="deepseek-flash",
                                            purpose="fixture", ref_id=None,
                                            amount=settings.api_budget_micros - 10)
    op = Operator(client_for(app))
    store = app.extensions["lia"]["store"]
    first = request_summary(op, analysis_id)
    assert first.status_code == 429
    cooldown = store.budget_blocked_until()
    assert cooldown == (clock.now + timedelta(minutes=60)).isoformat()
    # Il momento del possibile sblocco tiene conto della finestra di 24 ore, non solo del cooldown.
    assert first.get_json()["error"]["retry_at"] > cooldown

    # Riavvio, nuovo browser e nuova sessione: il blocco resta.
    app = ai_app(settings, llm, clock=clock)
    op = Operator(client_for(app))
    assert request_summary(op, analysis_id).status_code == 429
    status = op.get("/api/operator/budget").get_json()
    assert status["blocked"] is True and status["cooldown_until"] == cooldown

    # Dopo 61 minuti il cooldown è finito ma il budget delle ultime 24 ore no: nuovo blocco.
    clock.advance(minutes=61)
    assert request_summary(op, analysis_id).status_code == 429
    assert store.budget_blocked_until() > cooldown
    assert llm.calls == 0

    # Solo quando la spesa esce dalla finestra e il cooldown è terminato si può riprovare.
    clock.advance(hours=24)
    op = Operator(client_for(app))
    assert request_summary(op, analysis_id).status_code == 202 and llm.calls == 1


def test_budget_status_distinguishes_estimated_and_confirmed(settings):
    app = ai_app(settings, FakeLLM(ProviderUnavailable("t", billing="uncertain")))
    analysis_id = public_analysis(app)
    op = Operator(client_for(app))
    request_summary(op, analysis_id)
    status = op.get("/api/operator/budget").get_json()
    assert status["budget_usd"] == "3.000000" and status["confirmed_usd"] == "0.000000"
    assert status["uncertain_usd"] != "0.000000" and status["blocked"] is False
    assert status["remaining_usd"] == usd(3_000_000 - int(status["uncertain_usd"].replace(".", "")))


# 15. I casi pubblici restano consultabili quando la ricerca è bloccata.
def test_public_cases_remain_available_while_blocked(settings):
    app = ai_app(settings, FakeLLM(), api_budget_micros=0)
    analysis_id = public_analysis(app)
    op = Operator(client_for(app))
    assert request_summary(op, analysis_id).status_code == 429
    anon = client_for(app)
    assert anon.get(f"/api/analyses/{analysis_id}").status_code == 200
    assert anon.get("/api/events").get_json()["total"] == 1


def test_max_output_tokens_is_bounded():
    assert MAX_OUTPUT_TOKENS <= 1000


@pytest.mark.parametrize("amount", [0, -1])
def test_non_positive_reservation_is_rejected(settings, amount):
    store = Store(settings.database_path)
    store.initialize()
    with pytest.raises(ValueError):
        BudgetService(store, settings).reserve(provider="deepseek", model="deepseek-flash",
                                               purpose="t", ref_id=None, amount=amount)

"""Analisi pura: separazione input/esiti e cutoff dei precedenti."""

from datetime import date

from conftest import fixture_bars, make_event

from linkedia.domain.analysis import build_market_analysis
from linkedia.domain.markets import MARKETS

BARS = fixture_bars(date(2019, 1, 1), date(2021, 12, 31))
TARGET = make_event("target", on=date(2021, 6, 15), tags=("war", "europe", "energy"))


def analyze(candidates, event=TARGET):
    return build_market_analysis(event, MARKETS["SP500"], BARS, candidates)


def test_observed_series_stops_at_base_and_outcomes_start_after():
    r = analyze([])
    assert r["base"]["date"] == "2021-06-14"
    assert max(p["s"] for p in r["observed"]["series"]) == 0
    assert min(p["s"] for p in r["outcomes"]["series"]) == 1
    assert r["observed"]["series"][-1]["index100"] == 100.0


def test_precedent_with_outcome_after_cutoff_is_excluded():
    close_before = make_event("late", on=date(2021, 6, 1))  # s=+20 cade dopo il 14 giugno
    early = make_event("early", on=date(2021, 3, 1))
    after = make_event("after", on=date(2021, 7, 1))
    r = analyze([TARGET, close_before, early, after])
    ids = [p["event_id"] for p in r["precedents"]["items"]]
    assert ids == ["early"]
    assert r["precedents"]["excluded"]["outcome_after_cutoff"] == 2
    for p in r["precedents"]["items"]:
        assert p["path"][-1]["s"] == 20


def test_irrelevant_candidates_are_excluded_and_ranked():
    same_cat = make_event("same", on=date(2020, 1, 10))
    tags_only = make_event("tags", on=date(2020, 2, 10), category="energy", tags=("war", "energy"))
    unrelated = make_event("other", on=date(2020, 3, 10), category="pandemic", tags=("health",))
    r = analyze([same_cat, tags_only, unrelated])
    ids = [p["event_id"] for p in r["precedents"]["items"]]
    assert ids == ["same", "tags"]
    assert r["precedents"]["excluded"]["not_relevant"] == 1


def test_stats_match_precedent_returns():
    cands = [make_event(f"c{i}", on=date(2020, 1 + i, 10)) for i in range(5)]
    r = analyze(cands)
    values = sorted(p["returns"]["5"] for p in r["precedents"]["items"])
    assert r["stats"]["5"]["values"] == values
    assert r["stats"]["5"]["n"] == 5


def test_recent_event_marks_incomplete_horizon():
    recent = make_event("recent", on=date(2021, 12, 28))
    r = analyze([], event=recent)
    returns = {x["h"]: x["value"] for x in r["outcomes"]["returns"]}
    assert returns[20] is None
    assert "horizon_incomplete" in [w["code"] for w in r["warnings"]]


def test_no_history_gives_explicit_status():
    r = analyze([], event=make_event("old", on=date(2018, 1, 1)))
    assert r["status"] == "insufficient_data"
    assert r["warnings"][0]["code"] == "no_base_session"

from datetime import date, datetime
from zoneinfo import ZoneInfo

from conftest import fixture_bars, make_event

from linkedia.domain.markets import MARKETS
from linkedia.domain.sessions import (
    RULE_DATE_ONLY,
    RULE_TIME_KNOWN,
    PriceBar,
    find_base_index,
    usable_sessions,
)

NY = ZoneInfo("America/New_York")
SP500 = MARKETS["SP500"]
BARS = usable_sessions(fixture_bars(date(2020, 6, 1), date(2020, 6, 30)))


def base_date(event, market=SP500):
    i, rule = find_base_index(BARS, event, market)
    return BARS[i].date, rule


def test_unknown_time_uses_previous_session():
    # mercoledì 10 giugno: la base è martedì 9
    assert base_date(make_event(on=date(2020, 6, 10))) == (date(2020, 6, 9), RULE_DATE_ONLY)


def test_unknown_time_on_weekend_uses_friday():
    assert base_date(make_event(on=date(2020, 6, 14)))[0] == date(2020, 6, 12)


def test_event_before_close_excludes_same_day_session():
    event = make_event(on=date(2020, 6, 10), at=datetime(2020, 6, 10, 14, 0, tzinfo=NY),
                       precision="exact")
    assert base_date(event) == (date(2020, 6, 9), RULE_TIME_KNOWN)


def test_event_after_close_includes_same_day_session():
    event = make_event(on=date(2020, 6, 10), at=datetime(2020, 6, 10, 16, 30, tzinfo=NY),
                       precision="exact")
    assert base_date(event)[0] == date(2020, 6, 10)


def test_event_at_close_counts_as_after_close():
    event = make_event(on=date(2020, 6, 10), at=datetime(2020, 6, 10, 16, 0, tzinfo=NY),
                       precision="approximate")
    assert base_date(event)[0] == date(2020, 6, 10)


def test_time_known_uses_market_timezone():
    # 22:00 a New York del 10 giugno = 11 giugno ore 11:00 a Tokyo, prima della chiusura:
    # per il Nikkei la base è il 10 giugno.
    event = make_event(on=date(2020, 6, 10), at=datetime(2020, 6, 10, 22, 0, tzinfo=NY),
                       precision="exact")
    assert base_date(event, MARKETS["NIKKEI"])[0] == date(2020, 6, 10)


def test_no_session_before_event():
    assert find_base_index(BARS, make_event(on=date(2020, 6, 1)), SP500)[0] is None


def test_rows_without_close_are_not_sessions():
    bars = [PriceBar(date(2020, 6, 1), 1, 1, 1, 10), PriceBar(date(2020, 6, 2), None, None, None, None),
            PriceBar(date(2020, 6, 3), 1, 1, 1, float("nan")), PriceBar(date(2020, 6, 4), 1, 1, 1, 11)]
    assert [b.date.day for b in usable_sessions(bars)] == [1, 4]


def test_tokyo_close_time_changed_in_2024():
    assert MARKETS["NIKKEI"].close_time_on(date(2024, 11, 1)).hour == 15
    assert MARKETS["NIKKEI"].close_time_on(date(2024, 11, 5)).minute == 30

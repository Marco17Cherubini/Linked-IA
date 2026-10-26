import math
from datetime import date, timedelta

import pytest

from linkedia.domain.indicators import forward_return, min_return_after, pre_event_indicators
from linkedia.domain.sample_stats import describe
from linkedia.domain.sessions import PriceBar


def series(closes):
    start = date(2020, 1, 1)
    return [PriceBar(start + timedelta(days=i), c, c * 1.01, c * 0.99, c) for i, c in enumerate(closes)]


def by_id(indicators):
    return {i.id: i for i in indicators}


def test_returns_use_only_history():
    closes = [100.0] * 55 + [100, 101, 102, 103, 104, 110]
    ind = by_id(pre_event_indicators(series(closes)))
    assert ind["ret_1"].value == pytest.approx((110 / 104 - 1) * 100)
    assert ind["ret_5"].value == pytest.approx(10.0)
    assert ind["drawdown_60"].value == pytest.approx(0.0)


def test_volatility_is_annualized_sample_stdev():
    closes = [100 * (1.01 if i % 2 else 0.99) ** 1 for i in range(30)]
    ind = by_id(pre_event_indicators(series(closes)))
    window = closes[-21:]
    rets = [math.log(b / a) for a, b in zip(window, window[1:], strict=False)]
    mean = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))
    assert ind["vol_20"].value == pytest.approx(sd * math.sqrt(252) * 100)
    assert ind["vol_20"].unit == "% annua"


def test_missing_history_is_reported_not_zero():
    ind = by_id(pre_event_indicators(series([100, 101, 102])))
    assert ind["vol_20"].value is None
    assert "servono almeno" in ind["vol_20"].reason
    assert ind["ret_1"].value is not None


def test_forward_returns_and_missing_horizon():
    s = series([100, 110, 121])
    assert forward_return(s, 0, 1) == pytest.approx(10)
    assert forward_return(s, 0, 2) == pytest.approx(21)
    assert forward_return(s, 0, 3) is None
    assert min_return_after(s, 0, 2) == pytest.approx(10)
    assert min_return_after(s, 0, 5) is None


def test_describe_small_samples():
    assert describe([])["median"] is None
    two = describe([1.0, -2.0])
    assert two["median"] is None and two["q1"] is None and two["up_count"] == 1
    assert two["observed_up_frequency"] == 0.5
    five = describe([1, 2, 3, 4, 5])
    assert five["median"] == 3 and five["q1"] == 2 and five["q3"] == 4
    assert five["small_sample"] is True

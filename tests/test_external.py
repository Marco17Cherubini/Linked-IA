"""Smoke test con il provider reale (gratuito). Escluso di default: `pytest -m external`."""

from datetime import date

import pytest

from linkedia.domain.markets import MARKETS
from linkedia.providers.market_data import YahooChartProvider


@pytest.mark.external
def test_yahoo_returns_known_close():
    bars = YahooChartProvider().daily_bars(MARKETS["SP500"], date(2022, 2, 22), date(2022, 2, 25))
    closes = {b.date: b.close for b in bars}
    # Chiusura ufficiale dell'S&P 500 del 23 febbraio 2022.
    assert closes[date(2022, 2, 23)] == pytest.approx(4225.50, abs=0.05)

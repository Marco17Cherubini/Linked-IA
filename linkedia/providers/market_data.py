"""Prezzi giornalieri degli indici.

`YahooChartProvider` usa l'endpoint pubblico (non ufficiale) `v8/finance/chart` di Yahoo
Finance. È sostituibile con qualunque oggetto che implementi `MarketDataProvider`.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, time
from typing import Protocol
from zoneinfo import ZoneInfo

import requests

from ..domain.markets import Market
from ..domain.sessions import PriceBar
from ..errors import ProviderUnavailable
from .http import new_session, request_json


class MarketDataProvider(Protocol):
    name: str

    def daily_bars(self, market: Market, start: date, end: date) -> list[PriceBar]: ...


def _num(value) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def parse_chart_response(payload: dict, market: Market) -> list[PriceBar]:
    """Valida e converte la risposta del chart endpoint. Le date sono quelle locali del mercato."""
    chart = payload.get("chart") if isinstance(payload, dict) else None
    if not isinstance(chart, dict):
        raise ProviderUnavailable("Risposta prezzi non valida: manca 'chart'")
    if chart.get("error"):
        raise ProviderUnavailable(f"Il provider prezzi ha segnalato un errore per {market.name}")
    results = chart.get("result") or []
    if not results:
        return []
    result = results[0]
    timestamps = result.get("timestamp") or []
    quotes = (result.get("indicators") or {}).get("quote") or [{}]
    quote = quotes[0] if quotes else {}
    tz = ZoneInfo(result.get("meta", {}).get("exchangeTimezoneName") or market.timezone)
    columns = {k: quote.get(k) or [] for k in ("open", "high", "low", "close", "volume")}
    if any(len(col) not in (0, len(timestamps)) for col in columns.values()):
        raise ProviderUnavailable("Risposta prezzi non valida: colonne di lunghezza diversa")

    bars: dict[date, PriceBar] = {}
    for i, ts in enumerate(timestamps):
        day = datetime.fromtimestamp(int(ts), tz=tz).date()

        def col(name: str, i: int = i) -> float | None:
            values = columns[name]
            return _num(values[i]) if values else None

        bars[day] = PriceBar(day, col("open"), col("high"), col("low"), col("close"), col("volume"))
    return [bars[d] for d in sorted(bars)]


class YahooChartProvider:
    name = "Yahoo Finance (chart API)"
    URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

    def __init__(self, timeout: float = 20, session: requests.Session | None = None):
        self.timeout = timeout
        self.session = session or new_session()
        # La sessione ha già uno User-Agent predefinito (python-requests), che Yahoo rifiuta.
        self.session.headers["User-Agent"] = "Mozilla/5.0 (LiA research prototype)"

    def daily_bars(self, market: Market, start: date, end: date) -> list[PriceBar]:
        period1 = int(datetime.combine(start, time(0), tzinfo=UTC).timestamp())
        period2 = int(datetime.combine(end, time(23, 59), tzinfo=UTC).timestamp())
        payload = request_json(
            self.session,
            "GET",
            self.URL.format(symbol=requests.utils.quote(market.symbol)),
            provider=self.name,
            timeout=self.timeout,
            params={"period1": period1, "period2": period2, "interval": "1d",
                    "includePrePost": "false", "events": ""},
        )
        return [b for b in parse_chart_response(payload, market) if start <= b.date <= end]

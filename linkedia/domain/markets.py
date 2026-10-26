"""Mercati osservati: unica fonte per simboli, fusi e orari di chiusura."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Market:
    id: str
    name: str
    symbol: str  # simbolo Yahoo Finance
    exchange: str
    timezone: str
    currency: str
    # Orari di chiusura regolari, dal più vecchio al più recente: (valido dal, orario).
    # Le chiusure anticipate (vigilie, festività parziali) non sono modellate.
    close_schedule: tuple[tuple[date, time], ...]

    def close_time_on(self, session_date: date) -> time:
        current = self.close_schedule[0][1]
        for valid_from, close_time in self.close_schedule:
            if session_date >= valid_from:
                current = close_time
        return current

    def close_at(self, session_date: date) -> datetime:
        """Istante di chiusura della seduta, con fuso esplicito."""
        return datetime.combine(
            session_date, self.close_time_on(session_date), tzinfo=ZoneInfo(self.timezone)
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "timezone": self.timezone,
            "currency": self.currency,
            "close_time": self.close_schedule[-1][1].strftime("%H:%M"),
        }


_EPOCH = date(1900, 1, 1)

MARKETS: dict[str, Market] = {
    m.id: m
    for m in (
        Market("SP500", "S&P 500", "^GSPC", "NYSE", "America/New_York", "USD",
               ((_EPOCH, time(16, 0)),)),
        Market("NASDAQ", "Nasdaq Composite", "^IXIC", "Nasdaq", "America/New_York", "USD",
               ((_EPOCH, time(16, 0)),)),
        Market("DAX", "DAX 40", "^GDAXI", "Xetra", "Europe/Berlin", "EUR",
               ((_EPOCH, time(17, 30)),)),
        Market("FTSE100", "FTSE 100", "^FTSE", "London Stock Exchange", "Europe/London", "GBP",
               ((_EPOCH, time(16, 30)),)),
        # La Borsa di Tokyo ha esteso la seduta alle 15:30 dal 5 novembre 2024.
        Market("NIKKEI", "Nikkei 225", "^N225", "Tokyo Stock Exchange", "Asia/Tokyo", "JPY",
               ((_EPOCH, time(15, 0)), (date(2024, 11, 5), time(15, 30)))),
    )
}

DEFAULT_MARKET = "SP500"


def get_market(market_id: str) -> Market | None:
    return MARKETS.get(market_id)

"""Sedute di borsa e convenzione temporale evento → seduta base.

Seduta base (s=0): ultima seduta la cui chiusura è anteriore all'evento.
- Orario noto (exact/approximate): chiusura locale del mercato <= istante dell'evento.
- Orario sconosciuto: ultima seduta con data precedente alla data dell'evento.
  È una scelta prudente: la seduta s=+1 può includere movimenti precedenti
  all'evento, ma la seduta base non contiene mai la reazione all'evento.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from datetime import date

from .events import Event
from .markets import Market

RULE_TIME_KNOWN = "close_before_event_time"
RULE_DATE_ONLY = "last_close_before_event_date"


@dataclass(frozen=True)
class PriceBar:
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None = None


def _valid(value: float | None) -> bool:
    return value is not None and math.isfinite(value) and value > 0


def usable_sessions(bars: list[PriceBar]) -> list[PriceBar]:
    """Sedute ordinate con chiusura valida. Le righe senza chiusura non sono sedute utilizzabili."""
    return sorted((b for b in bars if _valid(b.close)), key=lambda b: b.date)


def missing_bars(bars: list[PriceBar], start: date, end: date) -> int:
    return sum(1 for b in bars if start <= b.date <= end and not _valid(b.close))


def find_base_index(sessions: list[PriceBar], event: Event, market: Market) -> tuple[int | None, str]:
    """Indice della seduta base in `sessions` (ordinate per data), o None se non esiste."""
    dates = [s.date for s in sessions]
    if event.time_known:
        # Data locale del mercato nell'istante dell'evento: le sedute dei giorni precedenti
        # sono chiuse; quella dello stesso giorno solo se la chiusura è già avvenuta.
        local_day = event.occurred_at.astimezone(market.close_at(event.occurred_on).tzinfo).date()
        i = bisect_left(dates, local_day)
        if i < len(sessions) and dates[i] == local_day and market.close_at(local_day) <= event.occurred_at:
            i += 1
        rule = RULE_TIME_KNOWN
    else:
        i = bisect_left(dates, event.occurred_on)
        rule = RULE_DATE_ONLY
    return (i - 1 if i > 0 else None), rule

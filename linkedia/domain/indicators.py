"""Indicatori calcolati sulle sedute.

`pre_event_indicators` usa solo sedute fino alla seduta base inclusa: è l'informazione
disponibile al cutoff. `forward_return` e `min_return_after` misurano esiti futuri e
vanno sempre tenuti separati dagli input.
Le percentuali sono espresse in punti percentuali (1.5 = +1,5%).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

from .sessions import PriceBar

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class Indicator:
    id: str
    label: str
    value: float | None
    unit: str
    window: int
    description: str
    reason: str | None = None  # perché il valore manca

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "value": None if self.value is None else round(self.value, 4),
            "unit": self.unit,
            "window": self.window,
            "description": self.description,
            "reason": self.reason,
        }


def pct_change(new: float, old: float) -> float:
    return (new / old - 1.0) * 100.0


def _not_enough(needed: int) -> str:
    return f"servono almeno {needed} sedute precedenti"


def pre_event_indicators(history: list[PriceBar]) -> list[Indicator]:
    """`history` termina con la seduta base (s=0)."""
    closes = [b.close for b in history]
    out: list[Indicator] = []

    def add(id_, label, unit, window, description, compute, needed):
        if len(closes) >= needed:
            out.append(Indicator(id_, label, compute(), unit, window, description))
        else:
            out.append(Indicator(id_, label, None, unit, window, description, _not_enough(needed)))

    add("ret_1", "Rendimento ultima seduta", "%", 1,
        "Variazione della chiusura base rispetto alla seduta precedente.",
        lambda: pct_change(closes[-1], closes[-2]), 2)
    add("ret_5", "Rendimento 5 sedute", "%", 5,
        "Variazione della chiusura base rispetto a 5 sedute prima.",
        lambda: pct_change(closes[-1], closes[-6]), 6)

    def realized_vol() -> float:
        window = closes[-21:]
        log_returns = [math.log(b / a) for a, b in zip(window, window[1:], strict=False)]
        return statistics.stdev(log_returns) * math.sqrt(TRADING_DAYS_PER_YEAR) * 100.0

    add("vol_20", "Volatilità realizzata 20 sedute", "% annua", 20,
        "Deviazione standard campionaria dei rendimenti logaritmici giornalieri delle "
        "ultime 20 sedute, annualizzata con √252.", realized_vol, 21)

    def drawdown() -> float:
        return pct_change(closes[-1], max(closes[-60:]))

    add("drawdown_60", "Distanza dal massimo a 60 sedute", "%", 60,
        "Variazione della chiusura base rispetto alla chiusura più alta delle ultime 60 sedute.",
        drawdown, 60)

    def zscore() -> float:
        window = closes[-20:]
        sd = statistics.stdev(window)
        return 0.0 if sd == 0 else (closes[-1] - statistics.fmean(window)) / sd

    add("zscore_20", "Z-score a 20 sedute", "σ", 20,
        "Distanza della chiusura base dalla media delle ultime 20 chiusure, in deviazioni standard.",
        zscore, 20)

    base, prev = history[-1] if history else None, history[-2] if len(history) >= 2 else None
    range_kwargs = dict(
        id="range_1", label="Escursione seduta base", unit="%", window=1,
        description="(Massimo − minimo) della seduta base rispetto alla chiusura precedente.",
    )
    if base and prev and base.high and base.low:
        out.append(Indicator(**range_kwargs, value=(base.high - base.low) / prev.close * 100.0))
    else:
        out.append(Indicator(**range_kwargs, value=None, reason="massimo/minimo non disponibili"))
    return out


def forward_return(sessions: list[PriceBar], base_index: int, horizon: int) -> float | None:
    target = base_index + horizon
    if target >= len(sessions):
        return None
    return pct_change(sessions[target].close, sessions[base_index].close)


def min_return_after(sessions: list[PriceBar], base_index: int, horizon: int) -> float | None:
    """Peggior chiusura nelle `horizon` sedute successive, rispetto alla base (esito futuro)."""
    window = sessions[base_index + 1 : base_index + 1 + horizon]
    if len(window) < horizon:
        return None
    return pct_change(min(b.close for b in window), sessions[base_index].close)

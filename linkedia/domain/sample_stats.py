"""Statistiche descrittive del campione di precedenti.

Descrivono ciò che è accaduto nei casi selezionati: non sono stime di probabilità né
intervalli di confidenza. Ogni statistica è calcolata solo con una numerosità minima.
"""

from __future__ import annotations

import statistics

MIN_N_MEDIAN = 3
MIN_N_QUARTILES = 5
SMALL_SAMPLE = 10


def describe(returns: list[float]) -> dict:
    values = sorted(returns)
    n = len(values)
    result: dict = {
        "n": n,
        "values": [round(v, 4) for v in values],
        "median": None,
        "q1": None,
        "q3": None,
        "min": round(values[0], 4) if n else None,
        "max": round(values[-1], 4) if n else None,
        "up_count": sum(1 for v in values if v > 0),
        "observed_up_frequency": None,
        "small_sample": n < SMALL_SAMPLE,
        "notes": [],
    }
    if n:
        result["observed_up_frequency"] = round(result["up_count"] / n, 4)
    if n >= MIN_N_MEDIAN:
        result["median"] = round(statistics.median(values), 4)
    else:
        result["notes"].append(f"mediana non calcolata: servono almeno {MIN_N_MEDIAN} casi")
    if n >= MIN_N_QUARTILES:
        q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
        result["q1"], result["q3"] = round(q1, 4), round(q3, 4)
    else:
        result["notes"].append(f"quartili non calcolati: servono almeno {MIN_N_QUARTILES} casi")
    return result

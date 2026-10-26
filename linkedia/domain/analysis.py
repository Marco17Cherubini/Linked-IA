"""Analisi evento × mercato: funzione pura che produce un risultato serializzabile.

Il risultato separa:
- `observed`: ciò che era disponibile al cutoff (serie fino a s=0, indicatori);
- `outcomes`: esiti successivi all'evento (serie s>0, rendimenti agli orizzonti);
- `precedents` e `stats`: campione storico, composto solo da casi osservabili al cutoff.
"""

from __future__ import annotations

from . import precedents as prec
from .events import Event
from .indicators import forward_return, min_return_after, pre_event_indicators
from .markets import Market
from .sample_stats import describe
from .sessions import RULE_DATE_ONLY, PriceBar, find_base_index, missing_bars, usable_sessions

HORIZONS = (1, 5, 20)
MAX_HORIZON = max(HORIZONS)
SERIES_WINDOW = 60  # sedute prima e dopo l'evento restituite per il grafico principale
PATH_WINDOW = 20  # sedute prima e dopo per il confronto con i precedenti
MIN_HISTORY = 60
CLOSED_GAP_DAYS = 4  # oltre questo intervallo tra s=0 e s=+1 il mercato è rimasto chiuso


def _point(sessions: list[PriceBar], i: int, base_i: int) -> dict:
    s = sessions[i]
    return {
        "s": i - base_i,
        "date": s.date.isoformat(),
        "close": round(s.close, 4),
        "index100": round(s.close / sessions[base_i].close * 100.0, 3),
    }


def _path(sessions: list[PriceBar], base_i: int, before: int, after: int) -> list[dict]:
    lo, hi = max(0, base_i - before), min(len(sessions) - 1, base_i + after)
    return [
        {"s": p["s"], "index100": p["index100"]}
        for p in (_point(sessions, i, base_i) for i in range(lo, hi + 1))
    ]


def _warning(code: str, message: str, severity: str = "info") -> dict:
    return {"code": code, "severity": severity, "message": message}


def build_market_analysis(
    event: Event,
    market: Market,
    bars: list[PriceBar],
    candidates: list[Event],
) -> dict:
    sessions = usable_sessions(bars)
    base_i, rule = find_base_index(sessions, event, market)
    result: dict = {"market": market.id, "status": "ok", "warnings": []}
    warnings = result["warnings"]

    if base_i is None:
        result["status"] = "insufficient_data"
        warnings.append(_warning("no_base_session",
                                 "Nessuna seduta disponibile prima dell'evento per questo mercato.",
                                 "error"))
        result["quality"] = {"sessions_available": len(sessions)}
        return result

    base = sessions[base_i]
    event_dt = event.occurred_at.isoformat() if event.occurred_at else None
    result["base"] = {
        "date": base.date.isoformat(),
        "close": round(base.close, 4),
        "close_at": market.close_at(base.date).isoformat(),
        "rule": rule,
        "rule_description": (
            "Orario dell'evento sconosciuto: la base è l'ultima chiusura precedente alla data "
            "dell'evento."
            if rule == RULE_DATE_ONLY
            else "La base è l'ultima chiusura avvenuta prima dell'orario dell'evento."
        ),
    }
    result["event_time"] = {
        "occurred_on": event.occurred_on.isoformat(),
        "occurred_at": event_dt,
        "precision": event.time_precision,
    }

    # --- Informazione disponibile al cutoff -------------------------------------------------
    history = sessions[: base_i + 1]
    lo = max(0, base_i - SERIES_WINDOW)
    result["observed"] = {
        "series": [_point(sessions, i, base_i) for i in range(lo, base_i + 1)],
        "indicators": [ind.to_dict() for ind in pre_event_indicators(history)],
    }

    # --- Esiti successivi --------------------------------------------------------------------
    hi = min(len(sessions) - 1, base_i + SERIES_WINDOW)
    outcome_returns = []
    for h in HORIZONS:
        value = forward_return(sessions, base_i, h)
        end = sessions[base_i + h].date.isoformat() if base_i + h < len(sessions) else None
        outcome_returns.append({"h": h, "value": None if value is None else round(value, 4),
                                "end_date": end})
    min_after = min_return_after(sessions, base_i, MAX_HORIZON)
    result["outcomes"] = {
        "series": [_point(sessions, i, base_i) for i in range(base_i + 1, hi + 1)],
        "returns": outcome_returns,
        "min_after": {"h": MAX_HORIZON, "value": None if min_after is None else round(min_after, 4)},
    }
    result["target_path"] = _path(sessions, base_i, PATH_WINDOW, PATH_WINDOW)

    if base_i + 1 < len(sessions):
        first = sessions[base_i + 1]
        result["first_reaction"] = {"date": first.date.isoformat()}
        gap = (first.date - base.date).days
        if gap > CLOSED_GAP_DAYS:
            warnings.append(_warning(
                "market_closed_after_event",
                f"Il mercato è rimasto chiuso per {gap - 1} giorni tra la seduta base e la prima "
                "seduta successiva.", "warning"))
    else:
        result["first_reaction"] = None

    if not any(s.date == event.occurred_on for s in sessions):
        warnings.append(_warning("no_session_on_event_date",
                                 "Il giorno dell'evento non è una seduta di questo mercato "
                                 "(fine settimana, festività o chiusura)."))
    if event.time_precision == "unknown":
        warnings.append(_warning("time_unknown", result["base"]["rule_description"]))
    elif event.time_precision == "approximate":
        warnings.append(_warning("time_approximate",
                                 "Orario dell'evento approssimato: la seduta base può cambiare se "
                                 "l'evento è avvenuto vicino alla chiusura."))
    missing_h = [r["h"] for r in outcome_returns if r["value"] is None]
    if missing_h:
        warnings.append(_warning("horizon_incomplete",
                                 "Esiti non ancora osservabili per gli orizzonti: "
                                 + ", ".join(f"{h} sedute" for h in missing_h) + ".", "warning"))
    if base_i + 1 < MIN_HISTORY:
        warnings.append(_warning("short_history",
                                 f"Meno di {MIN_HISTORY} sedute disponibili prima dell'evento.",
                                 "warning"))

    # --- Precedenti --------------------------------------------------------------------------
    items, excluded = [], {"not_relevant": 0, "outcome_after_cutoff": 0, "no_data": 0}
    for cand in candidates:
        if cand.id == event.id:
            continue
        sim = prec.similarity(event, cand)
        if not prec.is_relevant(sim):
            excluded["not_relevant"] += 1
            continue
        c_sessions = sessions  # stesso mercato, stessa serie
        c_base, _ = find_base_index(c_sessions, cand, market)
        if c_base is None or c_base + MAX_HORIZON >= len(c_sessions):
            # Esito non osservabile nei dati: se l'evento è successivo al cutoff è escluso
            # per il cutoff, altrimenti per mancanza di dati.
            if cand.occurred_on >= base.date:
                excluded["outcome_after_cutoff"] += 1
            else:
                excluded["no_data"] += 1
            continue
        if c_sessions[c_base + MAX_HORIZON].date > base.date:
            excluded["outcome_after_cutoff"] += 1
            continue
        returns = {str(h): round(forward_return(c_sessions, c_base, h), 4) for h in HORIZONS}
        items.append({
            "event_id": cand.id,
            "title": cand.title,
            "occurred_on": cand.occurred_on.isoformat(),
            "category": cand.category,
            "tags": list(cand.tags),
            "score": sim.score,
            "same_category": sim.same_category,
            "shared_tags": list(sim.shared_tags),
            "base_date": c_sessions[c_base].date.isoformat(),
            "time_precision": cand.time_precision,
            "returns": returns,
            "min_after": round(min_return_after(c_sessions, c_base, MAX_HORIZON), 4),
            "path": _path(c_sessions, c_base, PATH_WINDOW, PATH_WINDOW),
            "sources": [s.to_dict() for s in cand.sources],
        })
    # a parità di punteggio, il più recente prima
    items.sort(key=lambda it: (it["score"], it["occurred_on"]), reverse=True)
    selected = items[: prec.MAX_PRECEDENTS]
    result["precedents"] = {
        "criteria": prec.criteria(),
        "cutoff_date": base.date.isoformat(),
        "items": selected,
        "eligible_count": len(items),
        "excluded": excluded,
    }
    result["stats"] = {
        str(h): describe([it["returns"][str(h)] for it in selected]) for h in HORIZONS
    }
    if not selected:
        warnings.append(_warning("no_precedents",
                                 "Nessun precedente pertinente con esito osservabile prima "
                                 "dell'evento.", "warning"))
    elif len(selected) < 10:
        warnings.append(_warning("small_sample",
                                 f"Campione di {len(selected)} precedenti: le statistiche "
                                 "descrivono pochi casi e non sono stime di probabilità.",
                                 "warning"))

    # --- Qualità -----------------------------------------------------------------------------
    window_start = sessions[lo].date
    window_end = sessions[hi].date
    result["quality"] = {
        "sessions_available": len(sessions),
        "coverage": {"first_date": sessions[0].date.isoformat(),
                     "last_date": sessions[-1].date.isoformat()},
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat(),
                   "sessions": hi - lo + 1},
        "missing_in_window": missing_bars(bars, window_start, window_end),
        "pre_event_sessions": base_i + 1,
        "usable_precedents": {str(h): result["stats"][str(h)]["n"] for h in HORIZONS},
    }
    if result["quality"]["missing_in_window"]:
        warnings.append(_warning("missing_sessions",
                                 f"{result['quality']['missing_in_window']} righe senza chiusura "
                                 "nella finestra sono state escluse.", "warning"))
    return result

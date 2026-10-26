"""Rotte JSON. Il calcolo resta nei servizi: qui solo validazione dell'input e forma della risposta."""

from __future__ import annotations

import hmac
from datetime import date
from functools import wraps

from flask import Blueprint, current_app, jsonify, request

from .. import METHOD_VERSION, __version__
from ..domain.analysis import HORIZONS, PATH_WINDOW, SERIES_WINDOW
from ..domain.events import CATEGORIES
from ..domain.markets import DEFAULT_MARKET, MARKETS
from ..domain.precedents import criteria
from ..errors import Forbidden, InvalidInput, NotFound

api = Blueprint("api", __name__)

VIEWS = ("retrospective", "as_of")
STATUSES = ("queued", "running", "succeeded", "failed")
MAX_PAGE_SIZE = 50


def ctx(name: str):
    return current_app.extensions["lia"][name]


def require_analyst(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = ctx("settings").admin_token
        if token is None:
            raise Forbidden("La creazione di analisi è disabilitata su questo server")
        header = request.headers.get("Authorization", "")
        supplied = header.removeprefix("Bearer ").strip()
        if not supplied or not hmac.compare_digest(supplied.encode(), token.encode()):
            raise Forbidden("Token di analista mancante o non valido")
        return fn(*args, **kwargs)

    return wrapper


def _page_args() -> tuple[int, int]:
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("page_size", 20))
    except ValueError as exc:
        raise InvalidInput("Parametri di paginazione non validi") from exc
    if page < 1 or not 1 <= size <= MAX_PAGE_SIZE:
        raise InvalidInput(f"page >= 1 e page_size tra 1 e {MAX_PAGE_SIZE}")
    return page, size


def _date_arg(name: str) -> date | None:
    raw = request.args.get(name)
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise InvalidInput(f"'{name}' deve essere una data YYYY-MM-DD") from exc


def _json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise InvalidInput("Il corpo della richiesta deve essere un oggetto JSON")
    return data


def _paginated(items, total, page, size):
    return {"items": items, "page": page, "page_size": size, "total": total,
            "pages": max(1, -(-total // size))}


@api.get("/health")
def health():
    return {"status": "ok", "version": __version__}


@api.get("/meta")
def meta():
    settings = ctx("settings")
    return {
        "version": __version__,
        "method_version": METHOD_VERSION,
        "markets": [m.to_dict() for m in MARKETS.values()],
        "default_market": DEFAULT_MARKET,
        "horizons": list(HORIZONS),
        "series_window": SERIES_WINDOW,
        "path_window": PATH_WINDOW,
        "categories": [{"id": k, "label": v} for k, v in CATEGORIES.items()],
        "precedent_criteria": criteria(),
        "features": {"create": settings.creation_enabled, "ai_summary": settings.ai_enabled},
        "featured_event_id": settings.featured_event_id,
    }


@api.get("/featured")
def featured():
    store = ctx("store")
    event_id = ctx("settings").featured_event_id
    analysis = store.latest_analysis_for_event(event_id, succeeded_only=True)
    if analysis is None:
        raise NotFound("Caso dimostrativo non ancora calcolato")
    return {"event_id": event_id, "analysis_id": analysis["id"]}


@api.get("/events")
def list_events():
    page, size = _page_args()
    category = request.args.get("category") or None
    if category and category not in CATEGORIES:
        raise InvalidInput("Categoria sconosciuta")
    items, total = ctx("store").list_events_with_latest(
        q=(request.args.get("q") or "").strip()[:100] or None, category=category,
        page=page, page_size=size)
    for item in items:
        item["category_label"] = CATEGORIES.get(item["category"], item["category"])
    return _paginated(items, total, page, size)


@api.get("/events/<event_id>")
def get_event(event_id: str):
    return ctx("store").get_event(event_id).to_dict()


@api.post("/events")
@require_analyst
def create_event():
    event, analysis_id = ctx("analysis").create_event(_json_body())
    return jsonify(event_id=event.id, analysis_id=analysis_id), 202


@api.post("/events/<event_id>/analyses")
@require_analyst
def rerun_analysis(event_id: str):
    analysis_id = ctx("analysis").request_analysis(event_id)
    return jsonify(event_id=event_id, analysis_id=analysis_id), 202


@api.get("/analyses")
def list_analyses():
    page, size = _page_args()
    status = request.args.get("status") or None
    if status and status not in STATUSES:
        raise InvalidInput("Stato sconosciuto")
    category = request.args.get("category") or None
    if category and category not in CATEGORIES:
        raise InvalidInput("Categoria sconosciuta")
    items, total = ctx("store").list_analyses(
        q=(request.args.get("q") or "").strip()[:100] or None, category=category, status=status,
        date_from=_date_arg("from"), date_to=_date_arg("to"), page=page, page_size=size)
    for item in items:
        item["category_label"] = CATEGORIES.get(item["category"], item["category"])
    return _paginated(items, total, page, size)


def _market_view(data: dict, view: str) -> dict:
    """In vista as-of si rimuove tutto ciò che è successivo alla seduta base."""
    if view == "retrospective" or data.get("status") != "ok":
        return data
    data = dict(data)
    data.pop("outcomes", None)
    data["target_path"] = [p for p in data.get("target_path", []) if p["s"] <= 0]
    data["first_reaction"] = None
    data["warnings"] = [w for w in data["warnings"] if w["code"] != "horizon_incomplete"]
    return data


@api.get("/analyses/<analysis_id>")
def get_analysis(analysis_id: str):
    store = ctx("store")
    analysis = store.get_analysis(analysis_id)
    market_id = request.args.get("market", DEFAULT_MARKET)
    if market_id not in MARKETS:
        raise InvalidInput("Mercato sconosciuto")
    view = request.args.get("view", "retrospective")
    if view not in VIEWS:
        raise InvalidInput("Vista non valida: retrospective o as_of")

    result = analysis.pop("result")
    error = ({"code": analysis.pop("error_code"), "message": analysis.pop("error_message")}
             if analysis["status"] == "failed" else None)
    analysis.pop("error_code", None)
    analysis.pop("error_message", None)
    body = {**analysis, "error": error, "market": market_id, "view": view}

    if result is None:
        body["event"] = store.get_event(analysis["event_id"]).to_dict()
        body["markets"] = []
        body["data"] = None
        body["summary"] = None
        return body

    errors = result.get("market_errors", {})
    body["event"] = result["event"]
    body["computed_at"] = result["computed_at"]
    body["markets"] = [
        {**m.to_dict(),
         "status": result["markets"].get(mid, {}).get("status", "unavailable"),
         "error": errors.get(mid)}
        for mid, m in MARKETS.items()
    ]
    market_data = result["markets"].get(market_id)
    body["data"] = _market_view(market_data, view) if market_data else None
    body["price_source"] = result.get("price_sources", {}).get(market_id)
    body["summary"] = store.latest_summary(analysis_id)

    response = jsonify(body)
    if analysis["status"] == "succeeded":
        response.add_etag()
        response.headers["Cache-Control"] = "no-cache"
        response.make_conditional(request)
    return response


@api.post("/analyses/<analysis_id>/summary")
@require_analyst
def request_summary(analysis_id: str):
    body = _json_body()
    summary_id = ctx("summary").request(
        analysis_id, confirm_cost=body.get("confirm_cost") is True,
        regenerate=body.get("regenerate") is True)
    return jsonify(summary_id=summary_id), 202

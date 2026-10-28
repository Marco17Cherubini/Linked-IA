"""Rotte JSON. Il calcolo resta nei servizi: qui solo validazione dell'input, autorizzazione
e forma della risposta.

Lettura pubblica: casi dimostrativi marcati `public`. Tutto ciò che può contattare servizi
esterni (nuovi eventi, ricalcoli, sintesi IA) richiede una sessione operatore valida e, per
le richieste che modificano lo stato, il token CSRF della sessione. Il controllo avviene
prima di qualunque accodamento o chiamata a provider.
"""

from __future__ import annotations

import hmac
from datetime import date
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from .. import METHOD_VERSION, __version__
from ..domain.analysis import HORIZONS, PATH_WINDOW, SERIES_WINDOW
from ..domain.events import CATEGORIES
from ..domain.markets import DEFAULT_MARKET, MARKETS
from ..domain.precedents import criteria
from ..errors import ConfigurationError, Forbidden, InvalidInput, LiaError, NotFound, Unauthorized

api = Blueprint("api", __name__)

VIEWS = ("retrospective", "as_of")
STATUSES = ("queued", "running", "succeeded", "failed")
MAX_PAGE_SIZE = 50


def ctx(name: str):
    return current_app.extensions["lia"][name]


def cookie_name() -> str:
    # Il prefisso __Host- impone Secure, Path=/ e nessun Domain: il cookie resta di questo host.
    return "__Host-lia_session" if ctx("settings").cookie_secure else "lia_session"


def current_session() -> dict | None:
    if "lia_session" not in g:
        g.lia_session = ctx("auth").session(request.cookies.get(cookie_name()))
    return g.lia_session


def _same_origin() -> bool:
    """Le richieste del browser dichiarano l'origine: deve coincidere con questo host."""
    origin = request.headers.get("Origin")
    if origin is not None:
        return origin == f"{request.scheme}://{request.host}"
    fetch_site = request.headers.get("Sec-Fetch-Site")
    return fetch_site in (None, "same-origin", "none")


def require_operator(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not ctx("settings").auth_configured:
            raise ConfigurationError("Le funzioni riservate sono disabilitate su questo server")
        session = current_session()
        if session is None:
            raise Unauthorized("Accesso richiesto")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            supplied = request.headers.get("X-CSRF-Token", "")
            if not _same_origin() or not hmac.compare_digest(supplied.encode(),
                                                             session["csrf_token"].encode()):
                raise Forbidden("Richiesta non autorizzata (verifica CSRF non superata)", code="csrf")
        return fn(*args, **kwargs)

    return wrapper


def _page_args() -> tuple[int, int]:
    try:
        page = int(request.args.get("page", 1))
        size = int(request.args.get("page_size", 20))
    except ValueError as exc:
        raise InvalidInput("Parametri di paginazione non validi") from exc
    if not 1 <= page <= 10_000 or not 1 <= size <= MAX_PAGE_SIZE:
        raise InvalidInput(f"page tra 1 e 10000 e page_size tra 1 e {MAX_PAGE_SIZE}")
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
    if not request.is_json:
        raise InvalidInput("Il corpo della richiesta deve essere JSON")
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise InvalidInput("Il corpo della richiesta deve essere un oggetto JSON")
    return data


def _paginated(items, total, page, size):
    return {"items": items, "page": page, "page_size": size, "total": total,
            "pages": max(1, -(-total // size))}


def _visible_event(event_id: str):
    """Evento consultabile da chi fa la richiesta: i privati esistono solo per l'operatore."""
    event = ctx("store").get_event(event_id)
    if not event.public and current_session() is None:
        raise NotFound("Evento non trovato")
    return event


# --- Stato e metadati ----------------------------------------------------------------------

@api.get("/health")
def health():
    try:
        ctx("store").check()
    except LiaError:
        return jsonify(status="unavailable"), 503
    return {"status": "ok"}


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
        "features": {"create": settings.creation_enabled, "ai_summary": settings.ai_enabled,
                     "login": settings.auth_configured, "news_search": settings.news_search_enabled},
        "featured_event_id": settings.featured_event_id,
        "legal": {"controller_name": settings.controller_name,
                  "controller_email": settings.controller_email,
                  "session_hours": settings.session_hours,
                  "ai_model": settings.deepseek_model if settings.ai_enabled else None},
    }


# --- Accesso operatore ---------------------------------------------------------------------

def _session_body(session: dict | None) -> dict:
    if session is None:
        return {"authenticated": False}
    return {"authenticated": True, "expires_at": session["expires_at"],
            "csrf_token": session["csrf_token"]}


@api.get("/auth/session")
def auth_session():
    response = jsonify(_session_body(current_session()))
    response.headers["Cache-Control"] = "no-store"
    return response


@api.post("/auth/login")
def auth_login():
    if not _same_origin():
        raise Forbidden("Origine della richiesta non consentita", code="csrf")
    body = _json_body()
    result = ctx("auth").login(body.get("password"), request.remote_addr)
    response = jsonify(authenticated=True, expires_at=result["expires_at"],
                       csrf_token=result["csrf_token"])
    response.headers["Cache-Control"] = "no-store"
    response.set_cookie(cookie_name(), result["token"], max_age=result["max_age"], path="/",
                        secure=ctx("settings").cookie_secure, httponly=True, samesite="Strict")
    return response


@api.post("/auth/logout")
@require_operator
def auth_logout():
    ctx("auth").logout(current_session()["id"])
    response = jsonify(authenticated=False)
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(cookie_name(), path="/", secure=ctx("settings").cookie_secure,
                           httponly=True, samesite="Strict")
    return response


@api.get("/operator/budget")
@require_operator
def operator_budget():
    summary = ctx("summary")
    status = ctx("budget").status(typical_amount=summary.typical_reservation())
    status["active_jobs"] = ctx("store").active_job_count()
    status["ai_enabled"] = ctx("settings").ai_enabled
    status["ai_model"] = ctx("settings").deepseek_model
    response = jsonify(status)
    response.headers["Cache-Control"] = "no-store"
    return response


# --- Eventi e analisi -----------------------------------------------------------------------

@api.get("/featured")
def featured():
    store = ctx("store")
    event_id = ctx("settings").featured_event_id
    if not store.event_exists(event_id) or not store.get_event(event_id).public:
        raise NotFound("Caso dimostrativo non ancora calcolato")
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
        page=page, page_size=size, public_only=current_session() is None)
    for item in items:
        item["category_label"] = CATEGORIES.get(item["category"], item["category"])
    return _paginated(items, total, page, size)


@api.get("/events/<event_id>")
def get_event(event_id: str):
    return _visible_event(event_id).to_dict()


@api.post("/events")
@require_operator
def create_event():
    event, analysis_id = ctx("analysis").create_event(_json_body(),
                                                      session_id=current_session()["id"])
    return jsonify(event_id=event.id, analysis_id=analysis_id), 202


@api.post("/events/<event_id>/analyses")
@require_operator
def rerun_analysis(event_id: str):
    analysis_id = ctx("analysis").request_analysis(event_id, session_id=current_session()["id"])
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
        date_from=_date_arg("from"), date_to=_date_arg("to"), page=page, page_size=size,
        public_only=current_session() is None)
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
    event = _visible_event(analysis["event_id"])
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
    body = {**analysis, "error": error, "market": market_id, "view": view, "public": event.public}

    if result is None:
        body["event"] = event.to_dict()
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
        # Le analisi private non devono restare in cache condivise.
        response.headers["Cache-Control"] = "no-cache" if event.public else "private, no-cache"
        response.make_conditional(request)
    return response


@api.post("/analyses/<analysis_id>/summary")
@require_operator
def request_summary(analysis_id: str):
    body = _json_body()
    _visible_event(ctx("store").get_analysis(analysis_id)["event_id"])
    summary_id = ctx("summary").request(
        analysis_id, confirm_cost=body.get("confirm_cost") is True,
        regenerate=body.get("regenerate") is True, session_id=current_session()["id"])
    return jsonify(summary_id=summary_id), 202

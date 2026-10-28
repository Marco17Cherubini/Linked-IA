"""Rotte della ricerca automatica delle notizie. Tutte riservate all'operatore: avviare una
ricerca consuma API a pagamento, e ricerche e risultati sono dati privati."""

from __future__ import annotations

from flask import Blueprint, jsonify

from .routes import _json_body, ctx, current_session, require_operator

news_api = Blueprint("news_api", __name__)


@news_api.post("/searches")
@require_operator
def start_search():
    result = ctx("news").request(_json_body(), session_id=current_session()["id"])
    return jsonify(result), 202 if not result["cached"] else 200


@news_api.get("/searches")
@require_operator
def recent_searches():
    return {"items": ctx("news").recent()}


@news_api.get("/searches/<search_id>")
@require_operator
def get_search(search_id: str):
    response = jsonify(ctx("news").get(search_id))
    response.headers["Cache-Control"] = "no-store"
    return response


@news_api.post("/searches/<search_id>/events/<int:idx>/analyze")
@require_operator
def analyze_event(search_id: str, idx: int):
    result = ctx("news").analyze_event(search_id, idx, session_id=current_session()["id"])
    return jsonify(result), 200 if result["reused"] else 202

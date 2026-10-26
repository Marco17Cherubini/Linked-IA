"""Applicazione Flask: API JSON sotto /api e frontend compilato su tutte le altre rotte."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException

from ..config import Settings, configure_logging
from ..errors import LiaError
from ..providers.llm import DeepSeekClient
from ..providers.market_data import YahooChartProvider
from ..services.analysis import AnalysisService
from ..services.jobs import BackgroundRunner
from ..services.summary import SummaryService
from ..storage.store import Store
from .routes import api

log = logging.getLogger(__name__)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    ),
}


def create_app(settings: Settings | None = None, *, store: Store | None = None,
               market_data=None, runner=None, llm_factory=None) -> Flask:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)

    store = store or Store(settings.database_path)
    store.initialize()
    interrupted = store.fail_interrupted_jobs()
    if interrupted:
        log.warning("%s job interrotti dal riavvio sono stati segnati come falliti", interrupted)

    runner = runner or BackgroundRunner()
    market_data = market_data or YahooChartProvider(timeout=settings.http_timeout_seconds)
    if llm_factory is None:
        def llm_factory():
            return DeepSeekClient(settings.require_deepseek_key(), base_url=settings.deepseek_base_url,
                                  model=settings.deepseek_model)

    app = Flask(__name__, static_folder=None)
    app.json.sort_keys = False
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    app.extensions["lia"] = {
        "settings": settings,
        "store": store,
        "analysis": AnalysisService(store, market_data, runner),
        "summary": SummaryService(store, settings, runner, llm_factory),
    }
    app.register_blueprint(api, url_prefix="/api")

    @app.errorhandler(LiaError)
    def handle_lia_error(exc: LiaError):
        if exc.http_status >= 500:
            log.error("%s: %s", exc.code, exc.message)
        return jsonify(error={"code": exc.code, "message": exc.message}), exc.http_status

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        messages = {404: "Risorsa non trovata", 405: "Metodo non consentito",
                    413: "Richiesta troppo grande", 400: "Richiesta non valida"}
        return (jsonify(error={"code": f"http_{exc.code}",
                               "message": messages.get(exc.code, exc.name)}), exc.code)

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        log.exception("Errore non gestito")
        return jsonify(error={"code": "internal_error", "message": "Errore interno del server"}), 500

    @app.after_request
    def security_headers(response):
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response

    dist = Path(settings.frontend_dist)

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def frontend(path: str):
        if path.startswith("api/"):
            return jsonify(error={"code": "http_404", "message": "Risorsa non trovata"}), 404
        if not (dist / "index.html").exists():
            return ("Frontend non compilato: eseguire `npm run build` in frontend/.", 503)
        if path and (dist / path).is_file():
            response = send_from_directory(dist, path)
            if path.startswith("assets/"):
                # I file in assets/ hanno l'hash nel nome: sono immutabili.
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            return response
        response = send_from_directory(dist, "index.html")
        response.headers["Cache-Control"] = "no-cache"
        return response

    return app

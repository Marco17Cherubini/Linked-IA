"""Applicazione Flask: API JSON sotto /api e frontend compilato su tutte le altre rotte."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Flask, jsonify, redirect, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from ..config import Settings, configure_logging
from ..errors import LiaError, RetryLater
from ..providers.llm import DeepSeekClient
from ..providers.market_data import YahooChartProvider
from ..services.analysis import AnalysisService
from ..services.auth import AuthService
from ..services.budget import BudgetService
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
        "script-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'self'"
    ),
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}


def create_app(settings: Settings | None = None, *, store: Store | None = None,
               market_data=None, runner=None, llm_factory=None, clock=None) -> Flask:
    settings = settings or Settings.from_env()
    configure_logging(settings.log_level)
    if os.environ.get("LIA_ADMIN_TOKEN"):
        log.warning("LIA_ADMIN_TOKEN è obsoleto e viene ignorato: usare l'accesso con password")
    if not settings.auth_configured:
        log.warning("LIA_OPERATOR_PASSWORD_HASH assente: creazione e sintesi IA disabilitate")

    store = store or Store(settings.database_path)
    store.initialize()
    interrupted = store.fail_interrupted_jobs()
    if interrupted:
        log.warning("%s job interrotti dal riavvio sono stati segnati come falliti", interrupted)

    clock_kw = {"clock": clock} if clock else {}
    budget = BudgetService(store, settings, **clock_kw)
    budget.recover()
    auth = AuthService(store, settings, **clock_kw)
    auth.purge()

    runner = runner or BackgroundRunner()
    market_data = market_data or YahooChartProvider(timeout=settings.http_timeout_seconds)
    if llm_factory is None:
        def llm_factory():
            return DeepSeekClient(settings.require_deepseek_key(), base_url=settings.deepseek_base_url,
                                  model=settings.deepseek_model)

    app = Flask(__name__, static_folder=None)
    app.json.sort_keys = False
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    if settings.proxy_hops > 0:
        # Railway: un proxy davanti all'app. Si considerano solo le intestazioni che aggiunge.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=settings.proxy_hops, x_proto=settings.proxy_hops,
                                x_host=0, x_port=0, x_prefix=0)
    app.extensions["lia"] = {
        "settings": settings,
        "store": store,
        "auth": auth,
        "budget": budget,
        "analysis": AnalysisService(store, market_data, runner, authorize=auth.session_is_valid),
        "summary": SummaryService(store, settings, runner, llm_factory, budget,
                                  authorize=auth.session_is_valid),
    }
    app.register_blueprint(api, url_prefix="/api")

    @app.before_request
    def canonical_host():
        host = settings.canonical_host
        if host and request.host.lower() == f"www.{host}":
            return redirect(f"https://{host}{request.full_path.rstrip('?')}", code=301)
        return None

    @app.errorhandler(LiaError)
    def handle_lia_error(exc: LiaError):
        if exc.http_status >= 500:
            log.error("%s: %s", exc.code, exc.message)
        error = {"code": exc.code, "message": exc.message}
        if isinstance(exc, RetryLater):
            error.update(retry_after=exc.retry_after, retry_at=exc.retry_at)
        response = jsonify(error=error)
        response.status_code = exc.http_status
        if isinstance(exc, RetryLater) and exc.retry_after:
            response.headers["Retry-After"] = str(exc.retry_after)
        return response

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
        if request.is_secure:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if request.path.startswith("/api/"):
            # Le risposte cambiano con la sessione: nessuna cache condivisa deve mescolarle.
            response.vary.add("Cookie")
            response.headers.setdefault("Cache-Control", "no-store")
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

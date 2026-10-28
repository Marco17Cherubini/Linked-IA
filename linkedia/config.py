"""Configurazione centralizzata.

Legge le variabili d'ambiente (e un eventuale `.env` nella radice del progetto)
solo quando `Settings.from_env()` viene chiamato: importare il modulo non ha
effetti collaterali. Le chiavi esterne sono facoltative e vengono richieste
solo dalle funzioni che ne hanno bisogno.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .errors import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} deve essere un intero") from exc


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def _env_usd_micros(name: str, default: int) -> int:
    """Importo in USD (es. "3.00") convertito in milionesimi di dollaro, senza virgola mobile."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ConfigurationError(f"{name} deve essere un importo in USD") from exc
    if not value.is_finite() or value < 0:
        raise ConfigurationError(f"{name} deve essere un importo in USD non negativo")
    return int(value * 1_000_000)


@dataclass(frozen=True)
class Settings:
    database_path: Path
    frontend_dist: Path
    # Hash Argon2id della password dell'operatore: la password in chiaro non è mai configurata.
    operator_password_hash: str | None = field(default=None, repr=False)
    # Cambiare questo valore invalida tutte le sessioni aperte senza toccare il codice.
    session_epoch: str = "1"
    session_hours: int = 8
    cookie_secure: bool = True
    # Numero di proxy fidati davanti all'applicazione (Railway: 1). 0 in locale.
    proxy_hops: int = 0
    # Host canonico: le richieste per "www.<host>" vengono reindirizzate qui.
    canonical_host: str | None = None
    deepseek_api_key: str | None = field(default=None, repr=False)
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    ai_daily_limit: int = 20
    # Budget globale delle chiamate a pagamento, in milionesimi di USD, su finestra mobile.
    api_budget_micros: int = 3_000_000
    api_budget_window_hours: int = 24
    api_block_minutes: int = 60
    featured_event_id: str = "russia-invades-ukraine-2022"
    http_timeout_seconds: int = 20
    log_level: str = "INFO"
    debug: bool = False
    # Dati del titolare mostrati nell'informativa privacy (nessun valore predefinito).
    controller_name: str | None = None
    controller_email: str | None = None
    # Ricerca automatica delle notizie (Perplexity Search API).
    perplexity_api_key: str | None = field(default=None, repr=False)
    perplexity_base_url: str = "https://api.perplexity.ai"
    # Tetto di costo per singola ricerca (richieste di ricerca + estrazione), in micro-USD.
    news_search_max_micros: int = 50_000

    @classmethod
    def from_env(cls, *, load_dotenv_file: bool = True) -> Settings:
        if load_dotenv_file:
            from dotenv import load_dotenv

            load_dotenv(PROJECT_ROOT / ".env", override=False)

        def path_from_env(name: str, default: Path) -> Path:
            raw = os.environ.get(name, "").strip()
            if not raw:
                return default
            path = Path(raw)
            # Percorsi relativi sempre rispetto alla radice del progetto,
            # mai rispetto alla directory di avvio.
            return path if path.is_absolute() else PROJECT_ROOT / path

        return cls(
            database_path=path_from_env("LIA_DATABASE_PATH", PROJECT_ROOT / "instance" / "lia.sqlite3"),
            frontend_dist=path_from_env("LIA_FRONTEND_DIST", PROJECT_ROOT / "frontend" / "dist"),
            operator_password_hash=os.environ.get("LIA_OPERATOR_PASSWORD_HASH", "").strip() or None,
            session_epoch=os.environ.get("LIA_SESSION_EPOCH", "").strip() or "1",
            session_hours=_env_int("LIA_SESSION_HOURS", 8),
            cookie_secure=_env_bool("LIA_COOKIE_SECURE", True),
            proxy_hops=_env_int("LIA_PROXY_HOPS", 0),
            canonical_host=os.environ.get("LIA_CANONICAL_HOST", "").strip().lower() or None,
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip() or None,
            deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "").strip() or "deepseek-flash",
            ai_daily_limit=_env_int("LIA_AI_DAILY_LIMIT", 20),
            api_budget_micros=_env_usd_micros("LIA_API_BUDGET_USD", 3_000_000),
            api_budget_window_hours=_env_int("LIA_API_BUDGET_WINDOW_HOURS", 24),
            api_block_minutes=_env_int("LIA_API_BLOCK_MINUTES", 60),
            featured_event_id=os.environ.get("LIA_FEATURED_EVENT", "russia-invades-ukraine-2022"),
            http_timeout_seconds=_env_int("LIA_HTTP_TIMEOUT", 20),
            log_level=os.environ.get("LIA_LOG_LEVEL", "INFO").upper(),
            debug=_env_bool("LIA_DEBUG"),
            controller_name=os.environ.get("LIA_CONTROLLER_NAME", "").strip() or None,
            controller_email=os.environ.get("LIA_CONTROLLER_EMAIL", "").strip() or None,
            perplexity_api_key=os.environ.get("PERPLEXITY_API_KEY", "").strip() or None,
            perplexity_base_url=os.environ.get("PERPLEXITY_BASE_URL", "https://api.perplexity.ai").rstrip("/"),
            news_search_max_micros=_env_usd_micros("LIA_NEWS_SEARCH_MAX_USD", 50_000),
        )

    @property
    def auth_configured(self) -> bool:
        return self.operator_password_hash is not None

    @property
    def creation_enabled(self) -> bool:
        return self.auth_configured

    @property
    def ai_enabled(self) -> bool:
        from .services.budget import price_for

        return (self.deepseek_api_key is not None and self.auth_configured
                and price_for("deepseek", self.deepseek_model) is not None)

    @property
    def news_search_enabled(self) -> bool:
        return (self.perplexity_api_key is not None and self.auth_configured
                and self.perplexity_base_url.startswith("https://"))

    def require_deepseek_key(self) -> str:
        if not self.deepseek_api_key:
            raise ConfigurationError("Sintesi IA non disponibile: DEEPSEEK_API_KEY non configurata")
        return self.deepseek_api_key


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

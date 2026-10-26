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


@dataclass(frozen=True)
class Settings:
    database_path: Path
    frontend_dist: Path
    admin_token: str | None = field(default=None, repr=False)
    deepseek_api_key: str | None = field(default=None, repr=False)
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    ai_daily_limit: int = 20
    featured_event_id: str = "russia-invades-ukraine-2022"
    http_timeout_seconds: int = 20
    log_level: str = "INFO"
    debug: bool = False

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
            admin_token=os.environ.get("LIA_ADMIN_TOKEN", "").strip() or None,
            deepseek_api_key=os.environ.get("DEEPSEEK_API_KEY", "").strip() or None,
            deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
            ai_daily_limit=_env_int("LIA_AI_DAILY_LIMIT", 20),
            featured_event_id=os.environ.get("LIA_FEATURED_EVENT", "russia-invades-ukraine-2022"),
            http_timeout_seconds=_env_int("LIA_HTTP_TIMEOUT", 20),
            log_level=os.environ.get("LIA_LOG_LEVEL", "INFO").upper(),
            debug=_env_bool("LIA_DEBUG"),
        )

    @property
    def creation_enabled(self) -> bool:
        return self.admin_token is not None

    @property
    def ai_enabled(self) -> bool:
        return self.deepseek_api_key is not None and self.admin_token is not None

    def require_deepseek_key(self) -> str:
        if not self.deepseek_api_key:
            raise ConfigurationError("Sintesi IA non disponibile: DEEPSEEK_API_KEY non configurata")
        return self.deepseek_api_key


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

"""Accesso dell'operatore: password con hash Argon2id, sessioni opache lato server, limiti ai tentativi.

- La password non è mai configurata in chiaro: il server conosce solo l'hash
  (`LIA_OPERATOR_PASSWORD_HASH`), generato con `python -m linkedia hash-password`.
- La sessione è un token casuale nel cookie; nel database si conserva solo il suo SHA-256,
  con un token CSRF, la scadenza assoluta e l'impronta della credenziale con cui è nata.
- Cambiare l'hash della password o `LIA_SESSION_EPOCH` invalida tutte le sessioni esistenti.
- I tentativi falliti sono registrati in SQLite (sopravvivono ai riavvii), per client e in
  totale; l'indirizzo del client è conservato solo come HMAC con un segreto dell'istanza.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from ..config import Settings
from ..errors import ConfigurationError, RetryLater, Unauthorized
from ..storage.store import Store

log = logging.getLogger(__name__)

MAX_PASSWORD_LENGTH = 256
FAILURE_WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_CLIENT = 5
MAX_FAILURES_GLOBAL = 20
ATTEMPT_RETENTION = timedelta(days=1)

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class AuthService:
    def __init__(self, store: Store, settings: Settings, *,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.store = store
        self.settings = settings
        self.clock = clock
        self._secret: str | None = None
        # Hash di riferimento per mantenere costante il tempo di risposta senza configurazione.
        self._credential = (_sha256(settings.operator_password_hash)
                            if settings.operator_password_hash else None)

    @property
    def configured(self) -> bool:
        return self.settings.auth_configured

    def _client_key(self, client_ip: str | None) -> str:
        if self._secret is None:
            self._secret = self.store.instance_secret()
        return hmac.new(self._secret.encode(), (client_ip or "unknown").encode(),
                        hashlib.sha256).hexdigest()[:32]

    def _check_rate(self, client: str, now: datetime) -> None:
        since = _iso(now - FAILURE_WINDOW)
        for count, oldest, limit in (
            (*self.store.login_failures_since(since, client), MAX_FAILURES_PER_CLIENT),
            (*self.store.login_failures_since(since), MAX_FAILURES_GLOBAL),
        ):
            if count >= limit:
                retry_at = datetime.fromisoformat(oldest) + FAILURE_WINDOW
                seconds = max(1, int((retry_at - now).total_seconds()))
                raise RetryLater("Troppi tentativi di accesso. Riprova più tardi.",
                                 code="too_many_attempts", retry_after=seconds, retry_at=_iso(retry_at))

    def login(self, password: object, client_ip: str | None) -> dict:
        """Verifica la password e crea una sessione. Restituisce token (per il cookie) e dati."""
        if not self.configured:
            raise ConfigurationError("Accesso operatore non configurato su questo server")
        now = self.clock()
        client = self._client_key(client_ip)
        self._check_rate(client, now)
        ok = False
        if isinstance(password, str) and 0 < len(password) <= MAX_PASSWORD_LENGTH:
            try:
                ok = _hasher.verify(self.settings.operator_password_hash, password)
            except VerifyMismatchError:
                ok = False
            except (VerificationError, InvalidHashError):
                log.error("LIA_OPERATOR_PASSWORD_HASH non è un hash Argon2 valido")
                ok = False
        self.store.record_login_attempt(client, ok, _iso(now))
        self.store.purge_login_attempts(_iso(now - ATTEMPT_RETENTION))
        if not ok:
            log.info("Accesso operatore rifiutato")
            raise Unauthorized("Password non valida", code="invalid_credentials")

        self.store.purge_expired_sessions(_iso(now))
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        expires = now + timedelta(hours=self.settings.session_hours)
        self.store.create_session(token_hash=_sha256(token), csrf_token=csrf,
                                  epoch=self.settings.session_epoch, credential=self._credential,
                                  created_at=_iso(now), expires_at=_iso(expires))
        log.info("Accesso operatore riuscito")
        return {"token": token, "csrf_token": csrf, "expires_at": _iso(expires),
                "max_age": int((expires - now).total_seconds())}

    def session(self, token: str | None) -> dict | None:
        """Sessione valida associata al token del cookie, oppure None."""
        if not token or not self.configured or len(token) > 128:
            return None
        token_hash = _sha256(token)
        row = self.store.get_session(token_hash)
        if row is None:
            return None
        now = _iso(self.clock())
        valid = (row["expires_at"] > now
                 and hmac.compare_digest(row["epoch"], self.settings.session_epoch)
                 and hmac.compare_digest(row["credential"], self._credential))
        if not valid:
            self.store.delete_session(token_hash)
            return None
        return {"id": token_hash, "csrf_token": row["csrf_token"], "expires_at": row["expires_at"]}

    def session_is_valid(self, session_id: str) -> bool:
        """Ricontrollo eseguito dai job al momento dell'esecuzione."""
        row = self.store.get_session(session_id)
        return bool(row and self.configured and row["expires_at"] > _iso(self.clock())
                    and row["epoch"] == self.settings.session_epoch
                    and row["credential"] == self._credential)

    def purge(self) -> None:
        """Rimuove sessioni scadute e tentativi oltre il periodo di conservazione (all'avvio)."""
        now = self.clock()
        self.store.purge_expired_sessions(_iso(now))
        self.store.purge_login_attempts(_iso(now - ATTEMPT_RETENTION))

    def logout(self, session_id: str) -> None:
        self.store.delete_session(session_id)

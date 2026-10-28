"""Errori applicativi condivisi da servizi, provider, storage, API e CLI.

Ogni errore ha un codice stabile e un messaggio adatto all'utente; i dettagli
diagnostici restano nei log del server.
"""


class LiaError(Exception):
    code = "internal_error"
    http_status = 500

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class InvalidInput(LiaError):
    code = "invalid_input"
    http_status = 400


class NotFound(LiaError):
    code = "not_found"
    http_status = 404


class Unauthorized(LiaError):
    code = "unauthorized"
    http_status = 401


class Forbidden(LiaError):
    code = "forbidden"
    http_status = 403


class Conflict(LiaError):
    code = "conflict"
    http_status = 409


class InsufficientData(LiaError):
    code = "insufficient_data"
    http_status = 422


class ProviderUnavailable(LiaError):
    """Un servizio esterno non ha risposto o ha risposto in modo non valido.

    Non va mai convertito in "nessun risultato": il chiamante deve propagarlo
    o registrarlo come avviso esplicito.
    """

    code = "provider_unavailable"
    http_status = 502

    def __init__(self, message: str, *, code: str | None = None, billing: str = "uncertain"):
        super().__init__(message, code=code)
        # Per le chiamate a pagamento: "not_billed" solo quando è certo che il provider
        # non ha elaborato la richiesta; in ogni altro caso la riserva resta impegnata.
        self.billing = billing


class RetryLater(LiaError):
    """Operazione rifiutata per ora: limite di frequenza, budget, job già in corso."""

    code = "retry_later"
    http_status = 429

    def __init__(self, message: str, *, code: str | None = None, retry_after: int | None = None,
                 retry_at: str | None = None):
        super().__init__(message, code=code)
        self.retry_after = retry_after
        self.retry_at = retry_at


class ConfigurationError(LiaError):
    code = "not_configured"
    http_status = 503


class PersistenceError(LiaError):
    code = "persistence_error"
    http_status = 500

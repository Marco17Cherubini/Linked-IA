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


class ConfigurationError(LiaError):
    code = "not_configured"
    http_status = 503


class PersistenceError(LiaError):
    code = "persistence_error"
    http_status = 500

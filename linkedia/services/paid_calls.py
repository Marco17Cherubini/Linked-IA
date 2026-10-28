"""Esecuzione di una chiamata a pagamento sotto il controllo del budget.

Unico percorso per sintesi IA, ricerca notizie ed estrazione degli eventi. Ogni tentativo:
1. prenota atomicamente il costo massimo (`BudgetService.reserve`, che rifiuta se non basta);
2. esegue la chiamata;
3. riconcilia: costo dall'utilizzo dichiarato, oppure l'intera riserva se l'utilizzo manca;
   libera la riserva solo se è certo che il provider non ha elaborato la richiesta;
   la lascia impegnata («incerta») se l'esito è sconosciuto e in quel caso non ripete.
Si ripete al massimo `attempts - 1` volte e solo dopo un errore certamente non fatturato.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from ..errors import ProviderUnavailable
from .budget import BudgetService

log = logging.getLogger(__name__)

T = TypeVar("T")

RETRY_DELAY_SECONDS = 2.0


def run_paid(budget: BudgetService, *, provider: str, model: str, purpose: str, ref_id: str | None,
             amount: int, call: Callable[[], tuple[T, dict | None]],
             cost_of: Callable[[dict | None], int | None], attempts: int = 2,
             sleep: Callable[[float], None] = time.sleep) -> T:
    """Esegue `call()` (che restituisce (valore, utilizzo)) con una riserva per tentativo."""
    for attempt in range(1, attempts + 1):
        entry = budget.reserve(provider=provider, model=model, purpose=purpose, ref_id=ref_id,
                               amount=amount, attempt=attempt)
        try:
            value, usage = call()
        except ProviderUnavailable as exc:
            if exc.billing == "billed":
                usage = getattr(exc, "usage", None)
                budget.confirm(entry, reserved=amount, usage=usage, actual=cost_of(usage) if usage else None)
                raise
            if exc.billing != "not_billed":
                budget.mark_uncertain(entry, f"esito incerto: {exc.code}")
                raise
            budget.release(entry, f"non fatturata: {exc.code}")
            retryable = exc.code in ("provider_rate_limited", "provider_unavailable")
            if attempt == attempts or not retryable:
                raise
            log.info("%s: nuovo tentativo dopo un errore non fatturato (%s)", purpose, exc.code)
            sleep(RETRY_DELAY_SECONDS)
            continue
        except BaseException:
            budget.mark_uncertain(entry, "errore inatteso durante la chiamata")
            raise
        budget.confirm(entry, reserved=amount, usage=usage, actual=cost_of(usage))
        return value
    raise AssertionError("unreachable")

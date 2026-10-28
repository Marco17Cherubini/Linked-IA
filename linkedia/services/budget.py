"""Budget globale delle chiamate a pagamento, controllato prima di ogni consumo.

Ogni tentativo di chiamata a pagamento (compresi i retry) passa da `reserve()`: si calcola
il costo massimo possibile, lo si prenota atomicamente in SQLite e solo allora la richiesta
può partire. Dopo la risposta la riserva viene riconciliata con l'utilizzo dichiarato dal
provider; se l'esito è incerto (timeout, errore 5xx, risposta illeggibile) la riserva resta
impegnata per l'intera finestra e non viene mai liberata automaticamente.

Gli importi sono interi in milionesimi di USD (micro-USD): nessun errore da virgola mobile.
Il budget è unico per l'istanza: non dipende da sessione, browser o indirizzo IP.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ..config import Settings
from ..errors import RetryLater
from ..storage.store import Store

log = logging.getLogger(__name__)

MICROS_PER_USD = 1_000_000
TOKENS_PER_PRICE_UNIT = 1_000_000
# Margine fisso per i token del modello di chat (ruoli, delimitatori) oltre al testo inviato.
PROMPT_TOKEN_OVERHEAD = 64


@dataclass(frozen=True)
class Price:
    """Prezzi in micro-USD: per milione di token e, se presente, per richiesta."""

    input_cache_miss: int
    input_cache_hit: int
    output: int
    verified_on: str
    per_request: int = 0


# Tariffe di picco (le più alte) pubblicate su https://api-docs.deepseek.com/quick_start/pricing,
# verificate il 2026-10-28. Si usano sempre quelle di picco anche fuori fascia: la stima resta
# prudente. Un modello assente da questa tabella non può essere chiamato.
PRICING: dict[tuple[str, str], Price] = {
    ("deepseek", "deepseek-flash"): Price(300_000, 6_000, 1_200_000, "2026-10-28"),
    ("deepseek", "deepseek-v4-pro"): Price(1_320_000, 44_000, 3_960_000, "2026-10-28"),
    # Search API: 5 USD ogni 1.000 richieste riuscite, nessun costo a token; una richiesta può
    # contenere fino a 5 query (https://docs.perplexity.ai/getting-started/pricing).
    ("perplexity", "search"): Price(0, 0, 0, "2026-10-28", per_request=5_000),
}


def price_for(provider: str, model: str) -> Price | None:
    return PRICING.get((provider, model))


def _cost(tokens: int, price_per_million: int) -> int:
    """Costo in micro-USD arrotondato per eccesso."""
    return -(-max(0, int(tokens)) * price_per_million // TOKENS_PER_PRICE_UNIT)


def max_cost_micros(price: Price, *, prompt_bytes: int, max_output_tokens: int) -> int:
    """Tetto prudenziale: ogni token copre almeno un byte UTF-8, quindi i token in ingresso
    non superano i byte inviati (più un margine fisso); l'uscita è limitata da max_tokens."""
    return (price.per_request + _cost(prompt_bytes + PROMPT_TOKEN_OVERHEAD, price.input_cache_miss)
            + _cost(max_output_tokens, price.output))


def actual_cost_micros(price: Price, usage: dict) -> int | None:
    """Costo dall'utilizzo dichiarato dal provider; None se l'utilizzo non è interpretabile."""
    try:
        prompt = int(usage["prompt_tokens"])
        completion = int(usage["completion_tokens"])
    except (KeyError, TypeError, ValueError):
        return None
    hit = usage.get("prompt_cache_hit_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    if isinstance(hit, int) and isinstance(miss, int) and hit + miss == prompt:
        input_cost = _cost(hit, price.input_cache_hit) + _cost(miss, price.input_cache_miss)
    else:
        input_cost = _cost(prompt, price.input_cache_miss)
    # I token di ragionamento si sommano per prudenza anche se il provider li includesse già.
    details = usage.get("completion_tokens_details") or {}
    reasoning = details.get("reasoning_tokens") if isinstance(details, dict) else None
    reasoning = reasoning if isinstance(reasoning, int) and reasoning > 0 else 0
    return price.per_request + input_cost + _cost(completion + reasoning, price.output)


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).isoformat(timespec="seconds")


def usd(micros: int) -> str:
    """Importo leggibile con 6 decimali, senza passare dalla virgola mobile."""
    sign = "-" if micros < 0 else ""
    whole, frac = divmod(abs(micros), MICROS_PER_USD)
    return f"{sign}{whole}.{frac:06d}"


class BudgetService:
    def __init__(self, store: Store, settings: Settings, *,
                 clock: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.store = store
        self.settings = settings
        self.clock = clock

    @property
    def window(self) -> timedelta:
        return timedelta(hours=self.settings.api_budget_window_hours)

    @property
    def block_duration(self) -> timedelta:
        return timedelta(minutes=self.settings.api_block_minutes)

    def recover(self) -> int:
        """All'avvio: le riserve rimaste aperte da un processo terminato restano impegnate."""
        n = self.store.mark_open_spend_uncertain(_iso(self.clock()))
        if n:
            log.warning("%s riserve di spesa aperte dopo il riavvio: marcate come incerte", n)
        return n

    def _available_at(self, now: datetime, amount: int) -> datetime | None:
        """Primo istante in cui, senza nuove spese, la finestra mobile consentirà `amount`."""
        budget = self.settings.api_budget_micros
        if amount > budget:
            return None
        entries = self.store.spend_entries_since(_iso(now - self.window))
        excess = sum(e["committed_micros"] for e in entries) + amount - budget
        if excess <= 0:
            return now
        for entry in entries:
            excess -= entry["committed_micros"]
            if excess <= 0:
                return datetime.fromisoformat(entry["created_at"]) + self.window
        return now + self.window

    def _refusal(self, now: datetime, blocked_until: str | None, amount: int) -> RetryLater:
        candidates = [t for t in (self._available_at(now, amount),) if t is not None]
        if blocked_until:
            candidates.append(datetime.fromisoformat(blocked_until))
        retry_at = max(candidates) if candidates else None
        if retry_at is None:
            return RetryLater("La chiamata supera il budget complessivo configurato.",
                              code="budget_exceeded")
        seconds = max(1, int((retry_at - now).total_seconds()))
        return RetryLater(
            "Budget delle chiamate IA esaurito o in pausa: le nuove sintesi sono sospese.",
            code="budget_blocked", retry_after=seconds, retry_at=_iso(retry_at))

    def ensure_available(self, amount: int) -> None:
        """Controllo all'accodamento. Non prenota: la prenotazione avviene prima della chiamata."""
        now = self.clock()
        blocked_until = self.store.budget_blocked_until()
        if blocked_until and blocked_until > _iso(now):
            raise self._refusal(now, blocked_until, amount)
        committed = sum(e["committed_micros"]
                        for e in self.store.spend_entries_since(_iso(now - self.window)))
        if committed + amount > self.settings.api_budget_micros:
            until = _iso(now + self.block_duration)
            self.store.set_budget_blocked_until(until)
            raise self._refusal(now, until, amount)

    def reserve(self, *, provider: str, model: str, purpose: str, ref_id: str | None,
                amount: int, attempt: int = 1) -> str:
        """Prenota `amount` micro-USD o solleva RetryLater. Restituisce l'id della voce."""
        if amount <= 0:
            raise ValueError("La riserva deve essere positiva")
        now = self.clock()
        entry_id = uuid.uuid4().hex
        outcome = self.store.reserve_spend(
            entry={"id": entry_id, "provider": provider, "model": model, "purpose": purpose,
                   "ref_id": ref_id, "attempt": attempt, "reserved_micros": amount},
            budget_micros=self.settings.api_budget_micros,
            window_start=_iso(now - self.window), now=_iso(now),
            block_until=_iso(now + self.block_duration))
        if not outcome["ok"]:
            log.warning("Chiamata a pagamento rifiutata dal budget (%s %s, riserva %s USD)",
                        provider, model, usd(amount))
            raise self._refusal(now, outcome["blocked_until"], amount)
        return entry_id

    def confirm(self, entry_id: str, *, reserved: int, actual: int | None, usage: dict | None) -> None:
        """Esito noto: si registra il costo calcolato dall'utilizzo. Se l'utilizzo manca si
        conferma l'intera riserva; se supera la riserva si registra comunque il valore reale."""
        if actual is None:
            actual, note = reserved, "utilizzo non dichiarato: confermata la riserva"
        else:
            note = None
            if actual > reserved:
                log.warning("Costo reale superiore alla riserva (%s > %s USD)", usd(actual), usd(reserved))
        self.store.settle_spend(entry_id, status="confirmed", now=_iso(self.clock()),
                                actual_micros=actual, usage=usage, note=note)

    def release(self, entry_id: str, note: str) -> None:
        """Solo quando è certo che il provider non ha elaborato (né fatturato) la richiesta."""
        self.store.settle_spend(entry_id, status="released", now=_iso(self.clock()),
                                actual_micros=0, note=note)

    def mark_uncertain(self, entry_id: str, note: str) -> None:
        self.store.settle_spend(entry_id, status="uncertain", now=_iso(self.clock()), note=note)

    def status(self, *, typical_amount: int | None = None) -> dict:
        now = self.clock()
        entries = self.store.spend_entries_since(_iso(now - self.window))
        confirmed = sum(e["committed_micros"] for e in entries if e["status"] == "confirmed")
        reserved = sum(e["committed_micros"] for e in entries if e["status"] == "reserved")
        uncertain = sum(e["committed_micros"] for e in entries if e["status"] == "uncertain")
        committed = confirmed + reserved + uncertain
        budget = self.settings.api_budget_micros
        blocked_until = self.store.budget_blocked_until()
        blocked = bool(blocked_until and blocked_until > _iso(now))
        amount = typical_amount or 1
        exhausted = committed + amount > budget
        next_at = None
        if blocked or exhausted:
            refusal = self._refusal(now, blocked_until if blocked else None, amount)
            next_at = refusal.retry_at
        return {
            "currency": "USD",
            "window_hours": self.settings.api_budget_window_hours,
            "budget_usd": usd(budget),
            "confirmed_usd": usd(confirmed),
            "reserved_usd": usd(reserved),
            "uncertain_usd": usd(uncertain),
            "committed_usd": usd(committed),
            "remaining_usd": usd(max(0, budget - committed)),
            "blocked": blocked or exhausted,
            "cooldown_until": blocked_until if blocked else None,
            "next_possible_at": next_at,
            "typical_reservation_usd": usd(amount) if typical_amount else None,
            "calls_in_window": len(entries),
            "as_of": _iso(now),
        }

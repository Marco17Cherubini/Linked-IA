"""Evento: che cosa è successo, quando, con quale precisione e quali fonti."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from urllib.parse import urlparse

CATEGORIES: dict[str, str] = {
    "geopolitical_conflict": "Conflitto geopolitico",
    "terrorism": "Terrorismo",
    "financial_crisis": "Crisi finanziaria",
    "monetary_policy": "Politica monetaria",
    "political": "Politica ed elezioni",
    "trade": "Commercio e dazi",
    "pandemic": "Pandemia e sanità",
    "natural_disaster": "Disastro naturale",
    "energy": "Energia e materie prime",
}

# exact: orario documentato al minuto; approximate: orario noto con un margine
# di incertezza (ore); unknown: è nota solo la data.
TIME_PRECISIONS = ("exact", "approximate", "unknown")

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TAG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Source:
    url: str
    publisher: str
    title: str
    kind: str = "reference"  # reference | official | news
    accessed_on: date | None = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "publisher": self.publisher,
            "title": self.title,
            "kind": self.kind,
            "accessed_on": self.accessed_on.isoformat() if self.accessed_on else None,
        }


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    description: str
    category: str
    tags: tuple[str, ...]
    occurred_on: date
    occurred_at: datetime | None = None  # sempre con fuso quando presente
    time_precision: str = "unknown"
    sources: tuple[Source, ...] = field(default_factory=tuple)
    origin: str = "curated"  # curated | user
    # Solo i casi marcati esplicitamente come pubblici sono visibili senza accesso.
    public: bool = False

    @property
    def time_known(self) -> bool:
        return self.occurred_at is not None and self.time_precision != "unknown"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "category_label": CATEGORIES.get(self.category, self.category),
            "tags": list(self.tags),
            "occurred_on": self.occurred_on.isoformat(),
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "time_precision": self.time_precision,
            "sources": [s.to_dict() for s in self.sources],
            "origin": self.origin,
            "public": self.public,
        }


def _require_str(data: dict, key: str, *, max_len: int, errors: list[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"'{key}' è obbligatorio")
        return ""
    value = value.strip()
    if len(value) > max_len:
        errors.append(f"'{key}' supera {max_len} caratteri")
    return value


def parse_event(data: dict, *, origin: str = "curated") -> tuple[Event | None, list[str]]:
    """Valida un dizionario (catalogo o richiesta API) e restituisce l'evento o gli errori."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return None, ["il corpo deve essere un oggetto JSON"]

    event_id = _require_str(data, "id", max_len=80, errors=errors)
    if event_id and not _SLUG.match(event_id):
        errors.append("'id' deve contenere solo minuscole, cifre e trattini")
    title = _require_str(data, "title", max_len=160, errors=errors)
    description = _require_str(data, "description", max_len=1200, errors=errors)

    category = data.get("category")
    if category not in CATEGORIES:
        errors.append(f"'category' deve essere uno tra: {', '.join(CATEGORIES)}")

    raw_tags = data.get("tags") or []
    tags: list[str] = []
    if not isinstance(raw_tags, list) or len(raw_tags) > 12:
        errors.append("'tags' deve essere un elenco di al massimo 12 etichette")
    else:
        for tag in raw_tags:
            if not isinstance(tag, str) or not _TAG.match(tag.strip().lower()):
                errors.append(f"tag non valido: {tag!r}")
            else:
                tags.append(tag.strip().lower())

    occurred_on: date | None = None
    try:
        occurred_on = date.fromisoformat(str(data.get("occurred_on", "")))
    except ValueError:
        errors.append("'occurred_on' deve essere una data YYYY-MM-DD")

    precision = data.get("time_precision", "unknown")
    if precision not in TIME_PRECISIONS:
        errors.append(f"'time_precision' deve essere uno tra: {', '.join(TIME_PRECISIONS)}")

    occurred_at: datetime | None = None
    raw_at = data.get("occurred_at")
    if raw_at:
        try:
            occurred_at = datetime.fromisoformat(str(raw_at))
        except ValueError:
            errors.append("'occurred_at' deve essere un timestamp ISO 8601")
        else:
            if occurred_at.tzinfo is None:
                errors.append("'occurred_at' deve indicare il fuso (es. +01:00)")
            elif occurred_on and occurred_at.date() != occurred_on:
                errors.append("'occurred_at' deve cadere nella data 'occurred_on' (ora locale)")
    if precision != "unknown" and not raw_at:
        errors.append("con 'time_precision' diverso da 'unknown' serve 'occurred_at'")
    if precision == "unknown":
        occurred_at = None

    sources: list[Source] = []
    raw_sources = data.get("sources") or []
    if not isinstance(raw_sources, list) or not raw_sources:
        errors.append("serve almeno una fonte")
    elif len(raw_sources) > 10:
        errors.append("al massimo 10 fonti")
    else:
        for i, src in enumerate(raw_sources, 1):
            if not isinstance(src, dict):
                errors.append(f"fonte {i}: formato non valido")
                continue
            url = str(src.get("url", "")).strip()
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"fonte {i}: URL non valido")
                continue
            accessed_on = None
            if src.get("accessed_on"):
                try:
                    accessed_on = date.fromisoformat(str(src["accessed_on"]))
                except ValueError:
                    errors.append(f"fonte {i}: 'accessed_on' non valido")
            kind = src.get("kind", "reference")
            if kind not in {"reference", "official", "news"}:
                errors.append(f"fonte {i}: 'kind' non valido")
            sources.append(
                Source(
                    url=url,
                    publisher=str(src.get("publisher") or parsed.netloc)[:80],
                    title=str(src.get("title") or url)[:200],
                    kind=kind,
                    accessed_on=accessed_on,
                )
            )

    if errors or occurred_on is None:
        return None, errors
    return (
        Event(
            id=event_id,
            title=title,
            description=description,
            category=category,
            tags=tuple(dict.fromkeys(tags)),
            occurred_on=occurred_on,
            occurred_at=occurred_at,
            time_precision=precision,
            sources=tuple(sources),
            origin=origin,
            # Un evento creato via API nasce sempre privato; la pubblicazione è esplicita.
            public=origin == "curated" and data.get("public") is True,
        ),
        [],
    )

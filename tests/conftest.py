"""Fixture comuni. I test non usano la rete: ogni tentativo di connessione fallisce."""

from __future__ import annotations

import socket
from datetime import date, timedelta

import pytest

from linkedia.config import Settings
from linkedia.domain.events import Event, Source
from linkedia.domain.sessions import PriceBar
from linkedia.services.auth import hash_password

# FIXTURE: password usata solo dai test, mai configurata altrove.
PASSWORD = "fixture-password-0001"
PASSWORD_HASH = hash_password(PASSWORD)


@pytest.fixture(autouse=True)
def no_network(monkeypatch, request):
    if request.node.get_closest_marker("external"):
        return

    def guard(*args, **kwargs):
        raise RuntimeError("Accesso alla rete vietato nei test offline")

    monkeypatch.setattr(socket, "create_connection", guard)
    monkeypatch.setattr(socket.socket, "connect", guard)


def business_days(start: date, end: date) -> list[date]:
    days, d = [], start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def fixture_bars(start: date, end: date, *, base: float = 100.0, step: float = 0.1) -> list[PriceBar]:
    """FIXTURE sintetica: serie lineare riconoscibile (non sono prezzi reali)."""
    return [
        PriceBar(d, base + i * step, base + i * step + 1, base + i * step - 1, base + i * step, 1000)
        for i, d in enumerate(business_days(start, end))
    ]


def make_event(event_id: str = "fixture-event", *, on: date = date(2020, 6, 10),
               category: str = "geopolitical_conflict", tags=("war", "europe"),
               at=None, precision: str = "unknown") -> Event:
    return Event(
        id=event_id,
        title=f"FIXTURE {event_id}",
        description="Evento sintetico per i test",
        category=category,
        tags=tuple(tags),
        occurred_on=on,
        occurred_at=at,
        time_precision=precision,
        sources=(Source("https://example.org/fixture", "Example", "Fixture"),),
        origin="curated",
    )


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(database_path=tmp_path / "test.sqlite3", frontend_dist=tmp_path / "dist",
                    operator_password_hash=PASSWORD_HASH)

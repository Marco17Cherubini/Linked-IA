"""Esecuzione dei job in background.

Un solo thread: i calcoli sono brevi, le chiamate esterne vanno serializzate e lo stato
dei job vive nel database, quindi sopravvive al ricaricamento della pagina.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

log = logging.getLogger(__name__)


class BackgroundRunner:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lia-job")

    def submit(self, fn: Callable, *args) -> None:
        def wrapped():
            try:
                fn(*args)
            except Exception:  # il job registra già il proprio errore: qui solo il log
                log.exception("Job %s terminato con errore", getattr(fn, "__name__", fn))

        self._executor.submit(wrapped)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


class InlineRunner:
    """Esegue subito il job: usato dalla CLI e dai test."""

    def submit(self, fn: Callable, *args) -> None:
        fn(*args)

    def shutdown(self) -> None:
        pass

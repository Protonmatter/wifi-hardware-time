"""Bounded wait for a request's report group, optionally forcing ETW delivery. No device access."""
from __future__ import annotations

from typing import Callable

LISTEN_S = 5.0
POLL_S = 0.005
FLUSH_RETRY_S = 0.05
MAX_FLUSHES = 3


def wait_for_report(arrived: Callable[[], bool], *, pump: Callable[[], None], monotonic: Callable[[], float],
                    sleep: Callable[[float], None], flush: Callable[[], dict] | None = None,
                    listen_s: float = LISTEN_S, retry_s: float = FLUSH_RETRY_S, max_flushes: int = MAX_FLUSHES) -> list[dict]:
    """Pump until the report arrives or listen_s passes; flush first, then every retry_s up to max_flushes.

    The first flush is issued immediately because the caller enters after terminal I/O
    completion, which the driver logs after the report. Returns the flush receipts.
    """
    if listen_s <= 0 or retry_s <= 0 or type(max_flushes) is not int or max_flushes < 0:
        raise ValueError('Invalid report-wait bounds')
    flushes: list[dict] = []
    start = monotonic()
    next_flush = start
    while not arrived() and monotonic() - start < listen_s:
        if flush is not None and len(flushes) < max_flushes and monotonic() >= next_flush:
            flushes.append(flush())
            next_flush = monotonic() + retry_s
        pump()
        if arrived():
            break
        sleep(POLL_S)
    return flushes

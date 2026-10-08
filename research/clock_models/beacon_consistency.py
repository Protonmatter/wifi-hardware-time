"""Coarse falsification of the station-TSF/AP-TSF link from public cache reads.

A cached beacon was transmitted before it was read, so its AP timestamp must
not exceed the predicted station TSF at the read. Cache age is unknown, so this
catches only gross disagreement, never sub-millisecond error.
"""
from __future__ import annotations

from dataclasses import dataclass

from research.clock_models.bracket_bound import SpanReport

TOLERANCE_US = 1_000


@dataclass(frozen=True)
class Beacon:
    qpc: int
    ap_tsf_us: int


def check_beacons(beacons: list[Beacon], spans: list[SpanReport]) -> dict:
    checked = unchecked = violations = 0
    worst = None
    for beacon in beacons:
        covering = [s for s in spans if s.feasible and s.start_qpc <= beacon.qpc <= s.end_qpc]
        if not covering:
            unchecked += 1
            continue
        checked += 1
        # Every covering feasible model constrains the same beacon. Using the
        # tightest upper bound is independent of span enumeration order.
        excess = beacon.ap_tsf_us - min(s.bound.predict(beacon.qpc)[1] for s in covering)
        worst = excess if worst is None else max(worst, excess)
        if excess > TOLERANCE_US:
            violations += 1
    return dict(checked=checked, unchecked=unchecked, violations=violations, tolerance_us=TOLERANCE_US,
                worst_excess_us=None if worst is None else str(worst),
                scope='coarse: AP timestamp must not exceed predicted station TSF; cache age unknown')

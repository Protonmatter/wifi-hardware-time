"""Exact worst-case TSF bounds from host QPC windows. Offline analysis only.

Each Window states that the firmware captured the reported TSF somewhere in
[lower_qpc, upper_qpc]. Sample screening checks that condition separately; this
module only computes what follows if it holds. All arithmetic is exact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations

from research.clock_models.rate_bound import check_jump

US_PER_S = 1_000_000
RATE_PRIOR_PPM = 200  # Physical prior on |TSF rate / QPC rate - 1|.


@dataclass(frozen=True)
class Window:
    tsf_us: int
    lower_qpc: int
    upper_qpc: int

    def __post_init__(self) -> None:
        if any(type(v) is not int for v in (self.tsf_us, self.lower_qpc, self.upper_qpc)):
            raise ValueError('Window fields must be integers')
        if not 0 <= self.tsf_us < 1 << 64 or not 0 <= self.lower_qpc <= self.upper_qpc < 1 << 63:
            raise ValueError('Window outside range or reversed')


@dataclass(frozen=True)
class Bound:
    """Feasible (rate, offset) polygon; rate in TSF us per QPC tick from origin_qpc."""
    feasible: bool
    sample_count: int
    qpc_hz: int
    origin_qpc: int
    origin_tsf: int
    vertices: tuple[tuple[Fraction, Fraction], ...]

    def predict(self, qpc: int) -> tuple[Fraction, Fraction]:
        if not self.feasible:
            raise ValueError('No feasible model')
        x = qpc - self.origin_qpc
        values = [rate * x + offset for rate, offset in self.vertices]
        return self.origin_tsf + min(values), self.origin_tsf + max(values)

    def half_width_us(self, qpc: int) -> Fraction:
        low, high = self.predict(qpc)
        return (high - low) / 2

    def max_half_width_us(self, start_qpc: int, end_qpc: int) -> Fraction:
        # The half-width is convex in time, so its maximum on an interval is at an end.
        return max(self.half_width_us(start_qpc), self.half_width_us(end_qpc))

    def rate_ppm(self) -> tuple[Fraction, Fraction]:
        rates = [rate * self.qpc_hz / US_PER_S for rate, _ in self.vertices]
        return (min(rates) - 1) * US_PER_S, (max(rates) - 1) * US_PER_S


def window_bound(windows: list[Window], qpc_hz: int, rate_prior_ppm: int = RATE_PRIOR_PPM, jump_us=0) -> Bound:
    check_jump(jump_us)
    if type(qpc_hz) is not int or qpc_hz <= 0:
        raise ValueError('QPC frequency must be a positive integer')
    if type(rate_prior_ppm) is not int or not 0 < rate_prior_ppm < 10_000:
        raise ValueError('Rate prior must be 1 to 9999 ppm')
    if not windows or any(type(w) is not Window for w in windows):
        raise ValueError('Require at least one Window')
    origin_qpc, origin_tsf = windows[0].lower_qpc, windows[0].tsf_us
    # Integer TSF and QPC: widen by one TSF microsecond and one QPC tick.
    rows = [(w.tsf_us - origin_tsf, w.lower_qpc - origin_qpc, w.upper_qpc + 1 - origin_qpc) for w in windows]
    nominal = Fraction(US_PER_S, qpc_hz)
    r_low = nominal * (US_PER_S - rate_prior_ppm) / US_PER_S
    r_high = nominal * (US_PER_S + rate_prior_ppm) / US_PER_S
    # Offset limits per window: y - J - r*upper <= c <= y + 1 + J - r*lower (J: phase-jump allowance).
    lines = ([(y - jump_us, upper) for y, lower, upper in rows]
             + [(y + 1 + jump_us, lower) for y, lower, upper in rows])

    def inside(rate: Fraction, offset: Fraction) -> bool:
        return r_low <= rate <= r_high and all(
            y - jump_us - rate * upper <= offset <= y + 1 + jump_us - rate * lower for y, lower, upper in rows)

    candidates = {(r, y - r * x) for r in (r_low, r_high) for y, x in lines}
    for (y1, x1), (y2, x2) in combinations(lines, 2):
        if x1 != x2:
            rate = Fraction(y1 - y2, x1 - x2)
            candidates.add((rate, y1 - rate * x1))
    vertices = tuple(sorted(v for v in candidates if inside(*v)))
    return Bound(bool(vertices), len(windows), qpc_hz, origin_qpc, origin_tsf, vertices)


@dataclass(frozen=True)
class SpanReport:
    start_qpc: int
    end_qpc: int
    sample_count: int
    feasible: bool
    max_half_width_us: Fraction | None
    bound: Bound = field(repr=False, compare=False)


def sliding_bounds(windows: list[Window], qpc_hz: int, span_s: int = 60, step_s: int = 10,
                   min_samples: int = 3, rate_prior_ppm: int = RATE_PRIOR_PPM) -> list[SpanReport]:
    if type(span_s) is not int or type(step_s) is not int or not 0 < step_s <= span_s:
        raise ValueError('Require integer seconds with 0 < step_s <= span_s')
    if type(min_samples) is not int or min_samples < 1:
        raise ValueError('min_samples must be positive')
    if not windows:
        return []
    if any(b.lower_qpc <= a.lower_qpc for a, b in zip(windows, windows[1:])):
        raise ValueError('Windows must be strictly ordered by lower_qpc')
    span, step = span_s * qpc_hz, step_s * qpc_hz
    reports, seen, start = [], set(), windows[0].lower_qpc
    while start <= windows[-1].lower_qpc:
        members = [w for w in windows if start <= w.lower_qpc and w.upper_qpc <= start + span]
        if len(members) >= min_samples:
            key = (members[0].lower_qpc, members[-1].upper_qpc)
            if key not in seen:
                seen.add(key)
                bound = window_bound(members, qpc_hz, rate_prior_ppm)
                width = bound.max_half_width_us(*key) if bound.feasible else None
                reports.append(SpanReport(key[0], key[1], len(members), bound.feasible, width, bound))
        start += step
    return reports


def coverage(reports: list[SpanReport], start_qpc: int, end_qpc: int) -> Fraction:
    """Share of [start_qpc, end_qpc] covered by feasible spans."""
    if end_qpc <= start_qpc:
        raise ValueError('Empty interval')
    covered, cursor = 0, start_qpc
    for low, high in sorted((r.start_qpc, r.end_qpc) for r in reports if r.feasible):
        low, high = max(low, cursor), min(high, end_qpc)
        if high > low:
            covered += high - low
            cursor = high
    return Fraction(covered, end_qpc - start_qpc)

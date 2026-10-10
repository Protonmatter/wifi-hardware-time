"""Rate-only TSF bounds: no constant-rate model, exact arithmetic. Offline analysis only.

Assumes each reported TSF was captured inside its window and that the TSF advances at a rate
within the prior of nominal at every instant, with no unmodelled phase steps. Integer counters
widen each window by one QPC tick and each value by one TSF microsecond.
"""
from __future__ import annotations

from fractions import Fraction

US_PER_S = 1_000_000
TU_US = 1_024  # 802.11 time unit


def beacon_jump_allowance_us(beacon_interval_tu: int = 100, beacon_intervals: int = 6,
                             relative_ppm: int = 40) -> int:
    """Declared pairwise phase-jump allowance from station adoption of AP beacon timestamps.

    Between adoptions the station TSF free-runs; its drift from the AP trajectory over
    beacon_intervals beacon periods at relative_ppm is the largest correction one
    adoption can apply. Defaults: 100 TU beacons, six periods without an adopted beacon
    (power-save/DTIM listening), and two 20-ppm OFDM oscillators. A declared prior,
    not a measurement; the result is rounded up to whole microseconds.
    """
    values = (beacon_interval_tu, beacon_intervals, relative_ppm)
    if any(type(v) is not int or v <= 0 for v in values):
        raise ValueError('Beacon jump parameters must be positive integers')
    drift = Fraction(beacon_interval_tu * TU_US * beacon_intervals * relative_ppm, US_PER_S)
    return -(-drift.numerator // drift.denominator)


DEFAULT_JUMP_US = beacon_jump_allowance_us()


def rate_limits(qpc_hz: int, rate_prior_ppm: int = 200) -> tuple[Fraction, Fraction]:
    """Lowest and highest TSF microseconds per QPC tick allowed by the prior."""
    if type(qpc_hz) is not int or qpc_hz <= 0:
        raise ValueError('QPC frequency must be a positive integer')
    if type(rate_prior_ppm) is not int or not 0 < rate_prior_ppm < 10_000:
        raise ValueError('Rate prior must be 1 to 9999 ppm')
    nominal = Fraction(US_PER_S, qpc_hz)
    return (nominal * (US_PER_S - rate_prior_ppm) / US_PER_S, nominal * (US_PER_S + rate_prior_ppm) / US_PER_S)


def check_jump(jump_us) -> None:
    if type(jump_us) not in (int, Fraction) or jump_us < 0:
        raise ValueError('Phase-jump allowance must be a non-negative int or Fraction')


def envelope(tsf_us: int, lower_qpc: int, upper_qpc: int, query_qpc, limits: tuple[Fraction, Fraction],
             jump_us=0):
    """TSF interval at query_qpc implied by one sample alone (capture anywhere in its widened window).

    jump_us widens both sides for a bounded pairwise phase jump, such as station TSF
    adoption of the access point's beacon timestamp; 0 keeps the historical envelope.
    """
    check_jump(jump_us)
    a, b = limits
    toward_low = query_qpc - (upper_qpc + 1)  # latest possible capture gives the lowest value later
    toward_high = query_qpc - lower_qpc       # earliest possible capture gives the highest value later
    low = tsf_us - jump_us + (a if toward_low >= 0 else b) * toward_low
    high = tsf_us + 1 + jump_us + (b if toward_high >= 0 else a) * toward_high
    return low, high


def _half_width(earlier, later, q, limits) -> Fraction:
    lo1, hi1 = envelope(earlier.tsf_us, earlier.lower_qpc, earlier.upper_qpc, q, limits)
    lo2, hi2 = envelope(later.tsf_us, later.lower_qpc, later.upper_qpc, q, limits)
    return (min(hi1, hi2) - max(lo1, lo2)) / 2


def _gap_extremes(earlier, later, limits) -> tuple[Fraction, Fraction]:
    start, end = earlier.lower_qpc, later.upper_qpc + 1
    kinks = sorted({start, end} | {k for k in (earlier.upper_qpc + 1, later.lower_qpc) if start < k < end})
    candidates = set(kinks)
    for k0, k1 in zip(kinks, kinks[1:]):
        # Every bound is linear between kinks; the half-width can only turn where two bounds cross.
        ends = [(envelope(s.tsf_us, s.lower_qpc, s.upper_qpc, k0, limits),
                 envelope(s.tsf_us, s.lower_qpc, s.upper_qpc, k1, limits)) for s in (earlier, later)]
        for side in (0, 1):  # 0: lower bounds, 1: upper bounds
            d0 = ends[0][0][side] - ends[1][0][side]
            d1 = ends[0][1][side] - ends[1][1][side]
            if d0 != d1 and (d0 < 0 < d1 or d1 < 0 < d0):
                candidates.add(k0 + (k1 - k0) * d0 / (d0 - d1))
    widths = [_half_width(earlier, later, q, limits) for q in candidates]
    return min(widths), max(widths)


def gap_max_half_width(earlier, later, limits: tuple[Fraction, Fraction]) -> Fraction:
    """Exact worst half-width from the earlier sample's window start to the later sample's window end."""
    return _gap_extremes(earlier, later, limits)[1]


def retrospective_max_half_width(samples: list, qpc_hz: int, rate_prior_ppm: int = 200) -> dict:
    """Worst half-width over a run using each pair of consecutive samples (both sides of every gap)."""
    if len(samples) < 2:
        raise ValueError('Need at least two samples')
    if any(b.lower_qpc <= a.upper_qpc for a, b in zip(samples, samples[1:])):
        raise ValueError('Samples must be ordered with non-overlapping windows')
    limits = rate_limits(qpc_hz, rate_prior_ppm)
    worst, worst_index = None, None
    for index, (earlier, later) in enumerate(zip(samples, samples[1:])):
        low, high = _gap_extremes(earlier, later, limits)
        if low < 0:
            raise ValueError(f'Samples {earlier.sequence} and {later.sequence} are incompatible under the rate limit')
        if worst is None or high > worst:
            worst, worst_index = high, index
    gap = samples[worst_index + 1].lower_qpc - samples[worst_index].lower_qpc
    return dict(mode='retrospective-consecutive-pairs', rate_prior_ppm=rate_prior_ppm,
                quantization='window widened by 1 QPC tick; TSF value widened by 1 us',
                max_half_width_us=worst, worst_gap_index=worst_index, worst_gap_s=Fraction(gap, qpc_hz),
                gap_count=len(samples) - 1)

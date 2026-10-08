"""Causal TSF provider: intervals from available samples only, with sub-millisecond expiry.

Contract: docs/overview/2026-10-08-causal-provider-design.md. Under the declared capture, rate and
continuity assumptions, the provider returns an interval using only information available at the
specified input boundary, and withdraws its sub-millisecond status when that interval becomes too wide.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from research.clock_models.rate_bound import rate_limits

THRESHOLD_US = 1_000
ROUNDING_ALLOWANCE_US = Fraction(1, 2)
CONDITIONS = (
    'causal capture: each TSF was captured inside its window [lower_qpc, upper_qpc]',
    'bounded rate: TSF advances within the rate prior of nominal at every instant, with no unmodelled phase steps',
    'continuity: one continuous TSF within the epoch',
    'station TSF equals access point TSF (802.11 synchronization; not checked here)',
)


@dataclass(frozen=True)
class AvailableSample:
    sequence: int
    tsf_us: int
    lower_qpc: int
    upper_qpc: int
    available_qpc: int

    def __post_init__(self) -> None:
        values = (self.sequence, self.tsf_us, self.lower_qpc, self.upper_qpc, self.available_qpc)
        if any(type(v) is not int for v in values):
            raise ValueError('Sample fields must be integers')
        if not 0 <= self.lower_qpc <= self.upper_qpc:
            raise ValueError('Capture window reversed or negative')
        # A sample cannot be available before the tick after its report was logged.
        if self.available_qpc < self.upper_qpc + 1:
            raise ValueError('Sample available before the end of its capture window')


@dataclass(frozen=True)
class Consistency:
    sequence: int
    compatible: bool
    epoch: int
    reason: str


@dataclass(frozen=True)
class Estimate:
    query_qpc: int
    state: str
    epoch: int
    low_us: Fraction | None
    high_us: Fraction | None
    midpoint_us: Fraction | None
    half_width_us: Fraction | None
    estimate_us: int | None
    uncertainty_us: Fraction | None
    last_available_qpc: int | None
    reason: str
    conditions: tuple[str, ...] = CONDITIONS


class CausalProvider:
    """Model for any query Q at or after every incorporated sample's window end:
    low(Q) = c_low + a*Q with c_low = max(T_k - a*(U_k + 1)), and
    high(Q) = c_high + b*Q with c_high = min(T_k + 1 - b*L_k), over the epoch's samples k.
    Availability at least one tick after each window end makes every allowed query satisfy that."""

    def __init__(self, qpc_hz: int, rate_prior_ppm: int = 200, threshold_us: int = THRESHOLD_US):
        self.qpc_hz = qpc_hz
        self.rate_prior_ppm = rate_prior_ppm
        self.threshold_us = threshold_us
        self.a, self.b = rate_limits(qpc_hz, rate_prior_ppm)
        self.epoch = -1
        self.last_available: int | None = None
        self.reset()

    def reset(self) -> None:
        """Start a new epoch; clears samples and any latched invalid state. Time stays monotonic."""
        self.epoch += 1
        self.count = 0
        self.c_low: Fraction | None = None
        self.c_high: Fraction | None = None
        self.last_capture_end: int | None = None
        self.invalid_reason: str | None = None

    def model(self) -> tuple[int, Fraction | None, Fraction | None]:
        return self.count, self.c_low, self.c_high

    def invalidate(self, reason: str) -> None:
        """Record an established continuity or identity failure; latched until reset()."""
        if self.invalid_reason is None:
            self.invalid_reason = reason

    def _ordered(self, sample: AvailableSample) -> None:
        if self.last_available is not None and sample.available_qpc < self.last_available:
            raise ValueError('Samples must arrive in availability order')
        if self.last_capture_end is not None and sample.lower_qpc <= self.last_capture_end:
            raise ValueError('Capture window overlaps or precedes the previous sample')

    def check(self, sample: AvailableSample) -> Consistency:
        """Pre-update feasibility against the frozen model; never changes the provider."""
        self._ordered(sample)
        if self.invalid_reason is not None:
            return Consistency(sample.sequence, False, self.epoch, f'provider invalid: {self.invalid_reason}')
        if self.count == 0:
            return Consistency(sample.sequence, True, self.epoch, 'first sample in epoch')
        # Exists q in [L, U + 1] with low(q) <= T + 1 and high(q) >= T?
        latest = min(Fraction(sample.upper_qpc + 1), (sample.tsf_us + 1 - self.c_low) / self.a)
        earliest = max(Fraction(sample.lower_qpc), (sample.tsf_us - self.c_high) / self.b)
        if earliest <= latest:
            return Consistency(sample.sequence, True, self.epoch, 'compatible with earlier samples')
        return Consistency(sample.sequence, False, self.epoch,
                           'incompatible with earlier samples under the declared assumptions')

    def ingest(self, sample: AvailableSample) -> Consistency:
        result = self.check(sample)
        self.last_available = sample.available_qpc
        if not result.compatible:
            if self.invalid_reason is None:
                self.invalid_reason = f'sample {sample.sequence}: {result.reason}'
            return result
        low = sample.tsf_us - self.a * (sample.upper_qpc + 1)
        high = sample.tsf_us + 1 - self.b * sample.lower_qpc
        self.c_low = low if self.c_low is None else max(self.c_low, low)
        self.c_high = high if self.c_high is None else min(self.c_high, high)
        self.count += 1
        self.last_capture_end = sample.upper_qpc
        return result

    def stale_from_qpc(self) -> Fraction | None:
        """First QPC at which the returned conservative uncertainty reaches the threshold."""
        if self.count == 0 or self.invalid_reason is not None:
            return None
        return (2 * (self.threshold_us - ROUNDING_ALLOWANCE_US) - self.c_high + self.c_low) / (self.b - self.a)

    def estimate(self, query_qpc: int) -> Estimate:
        if type(query_qpc) is not int:
            raise ValueError('Query QPC must be an integer')
        if self.last_available is not None and query_qpc < self.last_available:
            raise ValueError('Query precedes the latest available sample; that would use future information')
        if self.invalid_reason is not None:
            return Estimate(query_qpc, 'invalid', self.epoch, None, None, None, None, None, None,
                            self.last_available, self.invalid_reason)
        if self.count == 0:
            return Estimate(query_qpc, 'acquiring', self.epoch, None, None, None, None, None, None,
                            self.last_available, 'no usable sample in the current epoch')
        low = self.c_low + self.a * query_qpc
        high = self.c_high + self.b * query_qpc
        midpoint, half_width = (low + high) / 2, (high - low) / 2
        rounded = math.floor(midpoint + Fraction(1, 2))
        # A uniform allowance covers nearest-integer rounding and keeps expiry
        # monotone between updates. The tight radius oscillates with midpoint
        # phase and can otherwise alternate tracking/stale near the threshold.
        uncertainty = half_width + ROUNDING_ALLOWANCE_US
        state = 'tracking' if uncertainty < self.threshold_us else 'stale'
        reason = 'uncertainty below threshold' if state == 'tracking' else 'uncertainty at or above threshold'
        return Estimate(query_qpc, state, self.epoch, low, high, midpoint, half_width, rounded, uncertainty,
                        self.last_available, reason)

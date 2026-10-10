"""Stronger-assumption companion to CausalProvider: a learned rate with bounded wander.

The guaranteed result stays CausalProvider's rate-only interval. This module adds a
narrower model interval under an explicitly declared extra assumption: across the
trailing span and the holdover to the query, the TSF rate stays within the exact
constant-rate interval of the trailing samples widened by +/- wander_ppm. The model is
labeled, never replaces the guarantee, and is validated out of sample by check_model().
Offline research code; contract in docs/overview/2026-10-09-sub-millisecond-plan.md.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fractions import Fraction
import math

from research.clock_models.causal_provider import ROUNDING_ALLOWANCE_US, AvailableSample, CausalProvider, Consistency, Estimate
from research.clock_models.rate_bound import US_PER_S, check_jump

WANDER_POLICY_VERSION = 'wht/wander-model-v1'
SPAN_S = 60
MIN_SAMPLES = 5


def constant_rate_interval(samples, limits: tuple[Fraction, Fraction], jump_us=0) -> tuple[Fraction, Fraction] | None:
    """Exact constant-rate interval (TSF us per QPC tick) consistent with every sample, or None.

    Under TSF(q) = c + r*q with pairwise phase jumps of at most jump_us, sample i limits
    c to [T_i - J - r*(U_i + 1), T_i + 1 + J - r*L_i]. A common c exists for rate r
    iff every pair satisfies r*(L_j - U_i - 1) <= T_j - T_i + 1 + 2J, so the feasible
    rates are an intersection of half-lines: O(n^2), exact.
    """
    check_jump(jump_us)
    low, high = limits
    for i in samples:
        for j in samples:
            span = j.lower_qpc - (i.upper_qpc + 1)
            slack = j.tsf_us - i.tsf_us + 1 + 2 * jump_us
            if span > 0:
                high = min(high, Fraction(slack) / span)
            elif span < 0:
                low = max(low, Fraction(slack) / span)
            elif slack < 0:
                return None
    return (low, high) if low <= high else None


@dataclass(frozen=True)
class WanderEstimate:
    guaranteed: Estimate
    state: str  # tracking | stale | unavailable | rejected | invalid
    low_us: Fraction | None
    high_us: Fraction | None
    half_width_us: Fraction | None
    estimate_us: int | None
    uncertainty_us: Fraction | None
    rate_ppm: tuple[Fraction, Fraction] | None
    reason: str
    policy_version: str = WANDER_POLICY_VERSION


class WanderProvider:
    def __init__(self, qpc_hz: int, *, wander_ppm: int, span_s: int = SPAN_S, min_samples: int = MIN_SAMPLES,
                 rate_prior_ppm: int = 200, threshold_us: int = 1_000, jump_us=0):
        if type(wander_ppm) is not int or not 0 <= wander_ppm <= rate_prior_ppm:
            raise ValueError('wander_ppm must be an integer within the rate prior')
        if type(span_s) is not int or span_s <= 0 or type(min_samples) is not int or min_samples < 2:
            raise ValueError('Require a positive span and at least two samples')
        self.guaranteed = CausalProvider(qpc_hz, rate_prior_ppm, threshold_us, jump_us)
        self.qpc_hz, self.wander_ppm, self.span_s, self.min_samples = qpc_hz, wander_ppm, span_s, min_samples
        self.threshold_us, self.jump_us = threshold_us, jump_us
        self.trailing: deque[AvailableSample] = deque()
        self.fit: tuple[Fraction, Fraction, Fraction, Fraction] | None = None  # a', b', c_low, c_high
        self.fit_reason = 'too few samples'

    @property
    def conditions(self) -> tuple[str, ...]:
        return self.guaranteed.conditions + (
            f'learned rate: over the trailing {self.span_s} s and the holdover to the query, the TSF rate stays '
            f'within the trailing constant-rate interval widened by {self.wander_ppm} ppm',)

    def _refit(self) -> None:
        self.fit = None
        if len(self.trailing) < self.min_samples:
            self.fit_reason = 'too few samples'
            return
        prior = (self.guaranteed.a, self.guaranteed.b)
        interval = constant_rate_interval(self.trailing, prior, self.jump_us)
        if interval is None:
            self.fit_reason = 'trailing samples admit no constant rate'
            return
        wander = Fraction(US_PER_S, self.qpc_hz) * self.wander_ppm / US_PER_S
        a, b = max(prior[0], interval[0] - wander), min(prior[1], interval[1] + wander)
        c_low = max(s.tsf_us - self.jump_us - a * (s.upper_qpc + 1) for s in self.trailing)
        c_high = min(s.tsf_us + 1 + self.jump_us - b * s.lower_qpc for s in self.trailing)
        self.fit, self.fit_reason = (a, b, c_low, c_high), 'fitted'

    def check_model(self, sample: AvailableSample) -> bool | None:
        """Out-of-sample test before ingest: is the new sample feasible under the model? None: no model."""
        if self.fit is None or self.guaranteed.invalid_reason is not None:
            return None
        a, b, c_low, c_high = self.fit
        latest = min(Fraction(sample.upper_qpc + 1), (sample.tsf_us + 1 - c_low) / a)
        earliest = max(Fraction(sample.lower_qpc), (sample.tsf_us - c_high) / b)
        return earliest <= latest

    def ingest(self, sample: AvailableSample) -> Consistency:
        result = self.guaranteed.ingest(sample)
        if result.compatible:
            self.trailing.append(sample)
            horizon = sample.lower_qpc - self.span_s * self.qpc_hz
            while self.trailing and self.trailing[0].lower_qpc < horizon:
                self.trailing.popleft()
        self._refit()
        return result

    def stale_from_qpc(self) -> Fraction | None:
        """First QPC at which the model uncertainty reaches the threshold (ignores the guarantee's narrowing)."""
        if self.fit is None or self.guaranteed.invalid_reason is not None:
            return None
        a, b, c_low, c_high = self.fit
        return (2 * (self.threshold_us - ROUNDING_ALLOWANCE_US) - c_high + c_low) / (b - a)

    def estimate(self, query_qpc: int) -> WanderEstimate:
        guaranteed = self.guaranteed.estimate(query_qpc)
        if guaranteed.state in ('invalid', 'acquiring'):
            return WanderEstimate(guaranteed, guaranteed.state, None, None, None, None, None, None, guaranteed.reason)
        if self.fit is None:
            return WanderEstimate(guaranteed, 'unavailable', None, None, None, None, None, None, self.fit_reason)
        a, b, c_low, c_high = self.fit
        low = max(guaranteed.low_us, c_low + a * query_qpc)
        high = min(guaranteed.high_us, c_high + b * query_qpc)
        if low > high:
            return WanderEstimate(guaranteed, 'rejected', None, None, None, None, None, None,
                                  'model interval excludes the guaranteed interval; learned-rate assumption failed')
        midpoint, half_width = (low + high) / 2, (high - low) / 2
        uncertainty = half_width + ROUNDING_ALLOWANCE_US
        state = 'tracking' if uncertainty < self.threshold_us else 'stale'
        scale = Fraction(self.qpc_hz, US_PER_S)
        rate_ppm = ((a * scale - 1) * US_PER_S, (b * scale - 1) * US_PER_S)
        return WanderEstimate(guaranteed, state, low, high, half_width, math.floor(midpoint + Fraction(1, 2)),
                              uncertainty, rate_ppm, self.fit_reason)

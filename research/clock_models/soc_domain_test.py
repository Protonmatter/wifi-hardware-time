"""Test whether the TSF report's SoC counter can lie in the QPC time domain.

Compatibility is a falsifiable condition, never proof of a shared oscillator.
"""
from __future__ import annotations

from fractions import Fraction

from research.clock_models.analyze_clock_pairing_hypothesis import assess
from research.clock_models.sample_screen import Sample


def _ratio(value: dict) -> Fraction:
    return Fraction(int(value['numerator']), int(value['denominator']))


def soc_domain(samples: list[Sample], ticks_per_unit: int = 10) -> dict:
    if type(ticks_per_unit) is not int or ticks_per_unit <= 0:
        raise ValueError('ticks_per_unit must be a positive integer')
    points = [(s.soc_raw, s.lower_qpc, s.upper_qpc) for s in samples]
    rate = assess(points)  # Validates count, ordering and ranges.
    low = max(lower - ticks_per_unit * (soc + 1) for soc, lower, upper in points)
    high = min(upper + 1 - ticks_per_unit * soc for soc, lower, upper in points)
    contains = False
    if rate['affine_feasible']:
        interval = rate['slope_interval']
        contains = (_ratio(interval['lower']) <= ticks_per_unit
                    and (interval['upper'] is None or ticks_per_unit <= _ratio(interval['upper'])))
    return dict(sample_count=len(points), ticks_per_unit=ticks_per_unit,
                model_version=rate['model_version'], quantization=rate['quantization'],
                fixed_rate_feasible=low <= high, fixed_rate_gap_qpc_ticks=max(0, low - high),
                fixed_rate_offset_interval_qpc_ticks=dict(lower=low, upper=high) if low <= high else None,
                rate_interval=rate['slope_interval'], rate_interval_contains_nominal=contains,
                compatible_with_qpc_domain=low <= high and contains, shared_oscillator_proven=False)

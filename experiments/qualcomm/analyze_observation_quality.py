"""Held-out prediction of TSF at host report logging times, never sample times.

Offline exploratory analysis. Constant sampling bias is not identifiable here.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from validate_research_bundle import validate_bundle


def _validate(points: list[tuple[int, int]]) -> None:
    if len(points) < 3 or any(type(x) is not int or type(y) is not int or not 0 <= x < (1 << 63) or not 0 <= y < (1 << 64) for x,y in points):
        raise ValueError('Require nonnegative integer counters')
    if any(b[0] <= a[0] or b[1] <= a[1] for a,b in zip(points,points[1:])):
        raise ValueError('Unordered data or counter discontinuity')


def _fit(points: list[tuple[int, int]]) -> tuple[Fraction, Fraction]:
    x0,y0=points[0]
    train=[(Fraction(x-x0),Fraction(y-y0)) for x,y in points]
    mx=sum(x for x,y in train)/len(train);my=sum(y for x,y in train)/len(train)
    slope=sum((x-mx)*(y-my) for x,y in train)/sum((x-mx)**2 for x,y in train)
    return slope,my-slope*mx


def evaluate(points: list[tuple[int, int]], *, train_count: int) -> dict[str, Any]:
    if type(train_count) is not int or train_count < 3 or len(points)-train_count < 3:
        raise ValueError('Require at least three training and three held-out points')
    _validate(points)
    x0,y0=points[0]
    slope,intercept=_fit(points[:train_count])
    errors=[abs(Fraction(y-y0)-(intercept+slope*(x-x0))) for x,y in points[train_count:]]
    last_errors=[abs(y-points[train_count-1][1]) for x,y in points[train_count:]]
    # Endpoint rate is fitted only on training data and predicts all holdout points.
    xe,ye=points[train_count-1]
    endpoint=Fraction(ye-y0,xe-x0)
    baseline=[abs(Fraction(y-y0)-endpoint*(x-x0)) for x,y in points[train_count:]]
    return dict(training_count=train_count, heldout_count=len(errors),
        slope_raw_ticks_per_qpc_tick=dict(numerator=str(slope.numerator),denominator=str(slope.denominator)),
        heldout=dict(affine_max_abs_raw_ticks=float(max(errors)),affine_mean_abs_raw_ticks=float(sum(errors)/len(errors)),
                     endpoint_rate_max_abs_raw_ticks=float(max(baseline)),last_value_max_abs_raw_ticks=max(last_errors)),
        firmware_sampling_validated=False,external_uncertainty_ns=None,
        target='TSF versus host report-log time; not hardware sampling time',
        physical_value_beyond_host_clock='not_established')


def evaluate_rate_transfer(training: list[tuple[int,int]], validation: list[tuple[int,int]]) -> dict[str,Any]:
    """Fit rate on another run; use one validation anchor, never join phase epochs."""
    _validate(training);_validate(validation)
    if len(validation) < 4:raise ValueError('Require one anchor and three held-out points')
    slope,_=_fit(training)
    x0,y0=validation[0]
    residuals=[abs(Fraction(y-y0)-slope*(x-x0)) for x,y in validation[1:]]
    endpoint=Fraction(training[-1][1]-training[0][1],training[-1][0]-training[0][0])
    baseline=[abs(Fraction(y-y0)-endpoint*(x-x0)) for x,y in validation[1:]]
    return dict(training_count=len(training),validation_anchor_count=1,heldout_count=len(residuals),
        phase_continuity_assumed=False,firmware_sampling_validated=False,external_uncertainty_ns=None,
        heldout=dict(affine_max_abs_raw_ticks=float(max(residuals)),affine_mean_abs_raw_ticks=float(sum(residuals)/len(residuals)),
                     endpoint_rate_max_abs_raw_ticks=float(max(baseline))),
        target='Rate transfer between runs, anchored at first validation report; not clock synchronization',
        physical_value_beyond_host_clock='not_established')


def _load(path: Path) -> tuple[list[tuple[int,int]], int]:
    if path.stat().st_size > 1_048_576:raise ValueError('Bundle exceeds 1 MiB contract limit')
    data=json.loads(path.read_text(encoding='utf-8'))
    validate_bundle(data)
    return [(int(s['report_qpc']),int(s['tsf_raw'])) for s in data['observations']],int(data['manifest']['qpc_frequency_hz'])


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--train-count',type=int)
    mode.add_argument('--rate-training-bundle',type=Path)
    args=parser.parse_args()
    try:
        points,frequency=_load(args.bundle)
        if args.rate_training_bundle:
            training,other_frequency=_load(args.rate_training_bundle)
            if frequency != other_frequency:raise ValueError('Incompatible QPC frequencies')
            result=evaluate_rate_transfer(training,points)
        else:
            result=evaluate(points,train_count=args.train_count)
        print(json.dumps(result,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError) as error:
        print(f'Analysis failed: {error}',file=sys.stderr);return 1


if __name__ == '__main__': raise SystemExit(main())

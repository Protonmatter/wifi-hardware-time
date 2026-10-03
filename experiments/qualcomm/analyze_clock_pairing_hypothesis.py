"""Falsify clock-pairing hypotheses; do not certify sampling or accuracy.

Input windows are host request-to-report observations. Treating them as hardware
sampling brackets is an explicit unproven assumption, even when a model fits.
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


def _ratio(value: Fraction) -> dict[str,str]:
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))


def assess(points: list[tuple[int,int,int]]) -> dict[str,Any]:
    """Assess H = a*S+b under assumed [host-before, host-report] brackets.

    Each point is (SoC raw counter, lower QPC, upper QPC). Default caller scope
    is one uninterrupted capture. Cross-capture use assumes extra continuity.
    """
    if len(points)<3:raise ValueError('Need at least three captures')
    for point in points:
        if len(point)!=3 or any(type(v) is not int for v in point):raise ValueError('Require integer triples')
        s,lower,upper=point
        if not 0<=s<(1<<64) or not 0<=lower<=upper<(1<<63):raise ValueError('Counter/window outside range')
    if any(b[0]<=a[0] or b[1]<=a[1] or b[2]<=a[2] for a,b in zip(points,points[1:])):
        raise ValueError('Discontinuity or unordered observations')
    nominal_low=max(lower-10*s for s,lower,upper in points)
    nominal_high=min(upper-10*s for s,lower,upper in points)
    slope_low=Fraction(0);slope_high=None
    for i,(s1,l1,u1) in enumerate(points):
        for s2,l2,u2 in points[i+1:]:
            difference=s2-s1
            slope_low=max(slope_low,Fraction(l2-u1,difference))
            upper=Fraction(u2-l1,difference)
            slope_high=upper if slope_high is None else min(slope_high,upper)
    feasible=slope_high is not None and slope_high>0 and slope_low<=slope_high
    example=None
    if feasible:
        slope=(slope_low+slope_high)/2
        lo=max(Fraction(lower)-slope*s for s,lower,upper in points)
        hi=min(Fraction(upper)-slope*s for s,lower,upper in points)
        if lo>hi:raise ArithmeticError('Pairwise slope constraints inconsistent with offset intersection')
        example=dict(slope=_ratio(slope),offset_lower=_ratio(lo),offset_upper=_ratio(hi))
    return dict(sample_count=len(points),nominal_scale='10 QPC ticks per SoC raw tick',
        nominal_scale_feasible=nominal_low<=nominal_high,
        nominal_scale_gap_qpc_ticks=str(max(0,nominal_low-nominal_high)),
        affine_feasible=feasible,
        slope_interval=dict(lower=_ratio(slope_low),upper=_ratio(slope_high)) if feasible else None,
        example_conditional_model=example,
        required_unproven_assumptions=['fresh sampling inside every host window','one affine counter relation and epoch'],
        fresh_sampling_validated=False,conversion_qualified=False,external_uncertainty_ns=None)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    args=parser.parse_args()
    try:
        if args.bundle.stat().st_size>1048576:raise ValueError('Bundle exceeds 1 MiB')
        data=json.loads(args.bundle.read_text(encoding='utf-8'));validate_bundle(data)
        samples=[s for s in data['observations'] if s['action']==4]
        result=assess([(int(s['soc_raw']),int(s['host_before_qpc']),int(s['report_qpc'])) for s in samples])
        result['bundle_id']=data['manifest']['bundle_id']
        result['scope']='one capture; QTIMER_CAPTURE observations only'
        print(json.dumps(result,indent=2));return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print(f'Pairing hypothesis rejected: {error}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())

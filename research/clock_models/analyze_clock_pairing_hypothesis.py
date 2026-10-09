"""Falsify clock-pairing hypotheses; do not certify sampling or accuracy.

Input windows are host request-to-report observations. Treating them as hardware
sampling brackets is an explicit unproven assumption, even when a model fits.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from fractions import Fraction
import json
from typing import Any

from research.evidence.validate_research_bundle import validate_bundle


def _ratio(value: Fraction) -> dict[str,str]:
    return dict(numerator=str(value.numerator),denominator=str(value.denominator))


def assess(points: list[tuple[int,int,int]]) -> dict[str,Any]:
    """Assess H = a*S+b under quantized counter and host brackets.

    Each point is (SoC raw counter, lower QPC, upper QPC). Default caller scope
    is one uninterrupted capture. Cross-capture use assumes extra continuity.
    Use the closed hull S in [raw, raw+1], H in [lower, upper+1]. Equality at
    a bin edge is deliberately conservative; compatibility is not physical proof.
    Equal counter bins can be valid. A null slope upper bound means unbounded;
    no NaN/Infinity or fitted finite ceiling substitutes for missing information.
    """
    if len(points)<3:raise ValueError('Need at least three captures')
    for point in points:
        if len(point)!=3 or any(type(v) is not int for v in point):raise ValueError('Require integer triples')
        s,lower,upper=point
        if not 0<=s<(1<<64) or not 0<=lower<=upper<(1<<63):raise ValueError('Counter/window outside range')
    if any(b[0]<a[0] or b[1]<=a[1] or b[2]<=a[2] for a,b in zip(points,points[1:])):
        raise ValueError('Discontinuity or unordered observations')
    nominal_low=max(lower-10*(s+1) for s,lower,upper in points)
    nominal_high=min(upper+1-10*s for s,lower,upper in points)
    slope_low=Fraction(0);slope_high=None
    for i,(s1,l1,u1) in enumerate(points):
        for s2,l2,u2 in points[i+1:]:
            difference=s2-s1
            # Each offset interval is [l-a*(s+1), u+1-a*s]. Enforce
            # both cross-intersections for every pair, with positive slope a.
            slope_low=max(slope_low,Fraction(l2-u1-1,difference+1))
            if difference>1:
                upper=Fraction(u2+1-l1,difference-1)
                slope_high=upper if slope_high is None else min(slope_high,upper)
    feasible=slope_high is None or (slope_high>0 and slope_low<=slope_high)
    example=None
    if feasible:
        slope=max(slope_low,Fraction(1)) if slope_high is None else (slope_low+slope_high)/2
        lo=max(Fraction(lower)-slope*(s+1) for s,lower,upper in points)
        hi=min(Fraction(upper+1)-slope*s for s,lower,upper in points)
        if lo>hi:raise ArithmeticError('Pairwise slope constraints inconsistent with offset intersection')
        example=dict(slope=_ratio(slope),offset_lower=_ratio(lo),offset_upper=_ratio(hi))
    return dict(sample_count=len(points),nominal_scale='10 QPC ticks per SoC raw tick',
        model_version='wht/clock-pairing-quantized-v2',
        quantization=dict(counter_interval='[raw, raw+1]',qpc_interval='[lower, upper+1]',
                          endpoint_policy='closed conservative hull of integer bins'),
        nominal_scale_feasible=nominal_low<=nominal_high,
        nominal_scale_gap_qpc_ticks=str(max(0,nominal_low-nominal_high)),
        affine_feasible=feasible,
        slope_interval=dict(lower=_ratio(slope_low),upper=_ratio(slope_high) if slope_high is not None else None) if feasible else None,
        example_conditional_model=example,
        required_unproven_assumptions=['fresh sampling inside every host window','one affine counter relation and epoch'],
        fresh_sampling_validated=False,conversion_qualified=False,external_uncertainty_ns=None)


def compare_counters(points: list[tuple[int,int,int,int]]) -> dict[str,Any]:
    """Compare reported TSF/SoC, without assuming the two samples are simultaneous.

    Rows are (TSF, SoC, lower QPC, upper QPC). A common rate means two
    independent constant offsets can fit; it never implies shared phase/clock.
    """
    if any(len(point)!=4 for point in points):raise ValueError('Require TSF/SoC/window quadruples')
    tsf=assess([(t,lo,hi) for t,s,lo,hi in points])
    soc=assess([(s,lo,hi) for t,s,lo,hi in points])
    bounds=None
    if tsf['affine_feasible'] and soc['affine_feasible']:
        def endpoint(result: dict[str,Any],key: str) -> Fraction | None:
            ratio=result['slope_interval'][key]
            return None if ratio is None else Fraction(int(ratio['numerator']),int(ratio['denominator']))
        lower=max(endpoint(result,'lower') for result in (tsf,soc))
        ceilings=[value for result in (tsf,soc) if (value:=endpoint(result,'upper')) is not None]
        upper=min(ceilings) if ceilings else None
        if upper is None or (0<upper and lower<=upper):
            bounds=dict(lower=_ratio(lower),upper=_ratio(upper) if upper is not None else None)
    differences=[t-s for t,s,lo,hi in points]
    soc_increment=points[-1][1]-points[0][1]
    endpoint_ratio=Fraction(points[-1][0]-points[0][0],soc_increment) if soc_increment else None
    return dict(sample_count=len(points),tsf_model=tsf,soc_model=soc,
        model_version=tsf['model_version'],quantization=tsf['quantization'],
        common_rate_feasible_under_assumptions=bounds is not None,common_rate_interval=bounds,
        reported_tsf_minus_soc_span_raw=str(max(differences)-min(differences)),
        reported_endpoint_increment_ratio=_ratio(endpoint_ratio) if endpoint_ratio is not None else None,
        reported_endpoint_increment_difference_ppm=_ratio((endpoint_ratio-1)*1_000_000) if endpoint_ratio is not None else None,
        interpretation='reported increments only; sampling skew and rate are not separated',
        required_unproven_assumptions=['each counter freshly sampled inside its host window',
                                      'both counters use the same raw unit scale',
                                      'one affine relation per counter within one epoch'],
        simultaneous_sampling_validated=False,conversion_qualified=False,external_uncertainty_ns=None)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--compare-counters',action='store_true',help='Compare conditional TSF and SoC rate intervals')
    args=parser.parse_args()
    try:
        if args.bundle.stat().st_size>1048576:raise ValueError('Bundle exceeds 1 MiB')
        data=json.loads(args.bundle.read_text(encoding='utf-8'));validate_bundle(data)
        samples=[s for s in data['observations'] if s['action']==4]
        if args.compare_counters:
            result=compare_counters([(int(s['tsf_raw']),int(s['soc_raw']),int(s['host_before_qpc']),int(s['report_qpc'])) for s in samples])
        else:
            result=assess([(int(s['soc_raw']),int(s['host_before_qpc']),int(s['report_qpc'])) for s in samples])
        result['bundle_id']=data['manifest']['bundle_id']
        result['scope']='one capture; QTIMER_CAPTURE observations only'
        print(json.dumps(result,indent=2));return 0
    except (OSError,ValueError,TypeError,KeyError,ArithmeticError) as error:
        print(f'Pairing hypothesis rejected: {error}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())

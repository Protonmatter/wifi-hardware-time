"""Offline exact-build replay of logged per-record FTM delta subtraction.

This checks arithmetic, not absolute timestamp semantics or calibrated units.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

DRIVER='ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115'


def signed_delta(t3_delta: int,t4_delta: int) -> int:
    if any(type(v) is not int or not 0 <= v < (1 << 32) for v in (t3_delta,t4_delta)):
        raise ValueError('Delta operands must be unsigned 32-bit integers')
    value=(t4_delta-t3_delta)&0xffffffff
    return value-(1 << 32) if value & (1 << 31) else value


def _number(value: Any,minimum: int,maximum: int) -> int:
    if type(value) is not str or not re.fullmatch(r'0|-[1-9][0-9]{0,9}|[1-9][0-9]{0,9}',value):
        raise ValueError('Expected canonical decimal integer string')
    result=int(value)
    if not minimum <= result <= maximum:raise ValueError('Number outside field width')
    return result


def analyze(data: dict[str,Any]) -> dict[str,Any]:
    if type(data) is not dict or set(data)!=set('schema driver_sha256 etl_sha256 preview_sha256 trace_health_sha256 trace_events_lost trace_buffers_lost provider_events events'.split()):
        raise ValueError('Unexpected evidence fields')
    if data['schema']!='qcom-ftm-deltas/v1' or data['driver_sha256']!=DRIVER:
        raise ValueError('Unsupported schema/build')
    for field in ('etl_sha256','preview_sha256','trace_health_sha256'):
        if type(data[field]) is not str or not re.fullmatch('[0-9a-f]{64}',data[field]):raise ValueError('Invalid provenance hash')
    for field in ('trace_events_lost','trace_buffers_lost'):
        if type(data[field]) is not int or data[field]!=0:raise ValueError('Trace loss/invalid loss field')
    count=data['provider_events']
    if type(count) is not int or count<=0:raise ValueError('Invalid event count')
    events=data['events']
    if type(events) is not list or not events or len(events)%3 or len(events)>count:
        raise ValueError('Empty/incomplete delta groups')
    records=[];last_ordinal=0
    for offset in range(0,len(events),3):
        group=events[offset:offset+3]
        values=[];thread=None
        for event,field in zip(group,('t3_del','t4_del','rtt')):
            if type(event) is not dict or set(event)!=set('field value ordinal thread_id'.split()):raise ValueError('Unknown event fields')
            if event['field']!=field:raise ValueError('Duplicate or out-of-order field')
            ordinal=event['ordinal'];tid=event['thread_id']
            if type(ordinal) is not int or not last_ordinal<ordinal<=count:raise ValueError('Unordered event ordinal')
            if type(tid) is not int or tid<0 or (thread is not None and tid!=thread):raise ValueError('Mixed log thread')
            last_ordinal=ordinal;thread=tid
            values.append(_number(event['value'],-(1 << 31) if field=='rtt' else 0,(1 << 31)-1 if field=='rtt' else (1 << 32)-1))
        a,b,rtt=values
        if signed_delta(a,b)!=rtt:raise ValueError('Logged RTT differs from signed 32-bit delta subtraction')
        records.append(dict(t3_delta_raw=a,t4_delta_raw=b,rtt_raw=rtt))
    return dict(matched_triplets=len(records),records=records,etl_sha256=data['etl_sha256'],
        driver_sha256=DRIVER,clock_offset_identifiable=False,tsf_relationship_validated=False,
        absolute_event_time_unit=None,calibrated_accuracy_validated=False,
        qualification='exact-build delta arithmetic only; not an absolute clock observation')


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        if args.evidence.stat().st_size>4*1024*1024:raise ValueError('Evidence exceeds 4 MiB')
        result=analyze(json.loads(args.evidence.read_text(encoding='utf-8-sig')))
        if args.output:
            with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
        print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2));return 0
    except (OSError,ValueError,TypeError,KeyError) as error:
        print(f'Delta evidence rejected: {error}',file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())

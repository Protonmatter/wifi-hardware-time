"""Offline structural postmortem of a finalized TSF decoder stream.

No device, trace, process, firmware or quarantine-marker operations. Grouping is
syntactic: it does not identify the producer or authenticate a request association.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from ndis_evidence import decode_json, load_json, write_json_new

KINDS=('command','report','soc_timer','delay')


def integer(value: Any, bits: int=64) -> int:
    if type(value) is not int or not 0<=value<(1<<bits):raise ValueError('Invalid numeric timing field')
    return value


def summarize_timing(rows: list[dict[str,Any]]) -> dict[str,Any]:
    if type(rows) is not list or len(rows)<2 or any(type(r) is not dict for r in rows):raise ValueError('Invalid decoder stream')
    header,last=rows[0],rows[-1]
    if header.get('kind')!='header' or last.get('kind')!='summary':raise ValueError('Missing decoder header/summary')
    if any(integer(header[k],32)!=0 for k in ('events_lost','buffers_lost')) or any(integer(last[k],32)!=0 for k in ('process_status','close_status')):
        raise ValueError('Loss or incomplete decoding')
    if integer(header['clock_type'],32)!=1 or integer(header['perf_frequency_hz'],63)==0:raise ValueError('Unqualified host trace clock')
    timing=rows[1:-1]
    if integer(last['matches'])!=len(timing):raise ValueError('Decoder count mismatch')
    previous=-1
    for event in timing:
        kind=event.get('kind')
        if kind not in KINDS:raise ValueError('Unknown timing record')
        stamp=integer(event['raw_timestamp'],63)
        if stamp<previous:raise ValueError('Timing records are not ordered')
        previous=stamp
        if kind in ('command','report','delay'):integer(event['vdev'],32)
        if kind=='command':integer(event['action'],32)
        if kind=='report':integer(event['tsf_raw'])
        if kind=='soc_timer':integer(event['soc_timer_raw']);integer(event['g_tsf_raw'])
        if kind=='delay':integer(event['tsf_delay_raw'],32)
    position=0;commands=0;unmatched=[];actions=Counter();diagnostics=[];previous_by_vdev={}
    while position<len(timing):
        command=timing[position] if timing[position]['kind']=='command' else None
        start=position+(command is not None)
        group=timing[start:start+3]
        if [r['kind'] for r in group]!=['report','soc_timer','delay']:raise ValueError('Incomplete or reordered report group')
        if group[0]['vdev']!=group[2]['vdev'] or (command and command['vdev']!=group[0]['vdev']):raise ValueError('Mixed vdev within group')
        if command:
            commands+=1;actions[str(command['action'])]+=1
        else:
            unmatched.append(dict(timing_record_offset=position,origin='unattributed'))
        report,timer,delay=group
        values=(report['tsf_raw'],timer['soc_timer_raw'],timer['g_tsf_raw'])
        prior=previous_by_vdev.get(report['vdev'])
        diagnostics.append(dict(report_ordinal=len(diagnostics)+1,
            structurally_preceded_by_command=command is not None,
            preceding_action=command['action'] if command else None,
            report_gap_qpc=report['raw_timestamp']-prior[0] if prior else None,
            tsf_change_raw=values[0]-prior[1][0] if prior else None,
            soc_change_raw=values[1]-prior[1][1] if prior else None,
            global_tsf_change_raw=values[2]-prior[1][2] if prior else None,
            same_counter_tuple_as_previous=values==prior[1] if prior else None,
            delay_matches_low_word_difference=delay['tsf_delay_raw']==(values[0]-values[1])%(1<<32)))
        previous_by_vdev[report['vdev']]=(report['raw_timestamp'],values)
        position=start+3
    return dict(schema='tsf-structural-postmortem/v1',timing_records=len(timing),
        counts={kind:sum(r['kind']==kind for r in timing) for kind in KINDS},
        command_groups=commands,commands_by_action=dict(actions),
        unmatched_report_groups=len(unmatched),unmatched=unmatched,
        qpc_frequency_hz=header['perf_frequency_hz'],report_diagnostics=diagnostics,
        diagnostic_deltas='signed differences from previous same-vdev report; no wrap or epoch inference',
        fresh_sampling_qualified=False,
        request_association_qualified=False,firmware_origin_identified=False,
        calibrated_accuracy_validated=False)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,required=True)
    parser.add_argument('--timing',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.output.exists():raise ValueError('Output already exists')
        with args.timing.open('rb') as stream:raw=stream.read(32*1024*1024+1)
        if len(raw)>32*1024*1024:raise ValueError('Decoder stream exceeds size limit')
        rows=[decode_json(line) for line in raw.splitlines() if line]
        if len(rows)>100000:raise ValueError('Too many timing records')
        result=summarize_timing(rows)
        requests=sorted(args.capture.glob('request-*.json'));admissions=list(args.capture.glob('admission-*.json'))
        if len(requests)>12 or len(admissions)>12:raise ValueError('Capture exceeds reviewed request bound')
        states=Counter();inputs={args.timing.name:hashlib.sha256(raw).hexdigest()}
        success_closed=0
        for path in requests:
            request=load_json(path)
            success_closed+=request.get('success') is True and request.get('handle_closed') is True
            inputs[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(args.capture.glob('submission-*.json')):
            states[load_json(path)['state']]+=1
            inputs[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
        outcome=load_json(args.capture/'run-result.json')
        result.update(capture_success=outcome['success'],capture_validation=outcome['validation'],
            request_receipts=len(requests),successful_closed_receipts=success_closed,
            admission_receipts=len(admissions),submission_states=dict(states),input_sha256=inputs,
            quarantine_modified=False)
        write_json_new(args.output,result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('unmatched','input_sha256','report_diagnostics')},indent=2))
        return 0
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as error:
        parser.exit(1,f'Postmortem rejected: {error}\n')


if __name__=='__main__':raise SystemExit(main())

"""Offline scan-trial postmortem. Valid evidence never promotes a failed trial.

Reads saved files only; no device, trace, notification or quarantine operations.
Outputs aggregate counts and relative host intervals, never raw endpoint IDs.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import hashlib
import json

from research.windows_timestamps.ndis_evidence import decode_json,write_json_new
from research.acquisition.run_passive_observation import assess
from research.acquisition.analyze_quarantined_tsf import integer


def characterize(request: dict,live: list[dict],timing: list[dict],outcome: dict,cleanup: dict,notifications: dict | None) -> dict:
    hz=integer(request['qpc_frequency_hz'],63)
    before=integer(request['qpc_before'],63);after=integer(request['qpc_after'],63)
    quiet=integer(request['quiet_started_qpc'],63)
    if hz==0 or after<before or quiet>before or request['api']!='WlanScan' or integer(request['status'],32)!=0:
        raise ValueError('Incomplete or reversed scan receipt')
    if type(outcome['success']) is not bool or integer(outcome['scan_calls'],32)!=1 or integer(outcome['private_requests'],32)!=0:
        raise ValueError('Unexpected experiment outcome')
    evidence=assess(live,timing,hz)
    if cleanup.get('observer_clean_stop') is not True or cleanup.get('evidence_drained') is not True:raise ValueError('Unqualified cleanup')
    reports=[r for r in timing if r['kind']=='report'];timers=[r for r in timing if r['kind']=='soc_timer']
    own=[] if notifications is None else [r for r in notifications['records'] if r.get('source')==8 and r.get('code')==7]
    observer=[r for r in live if r.get('kind')=='lifecycle' and r.get('source')==8 and r.get('code')==7]
    def delay(records):
        return (integer(records[0]['qpc'],63)-before)*1000000000//hz if len(records)==1 else None
    own_delay=delay(own)
    return dict(schema='scan-trial-postmortem/v1',controller_success=outcome['success'],
        quiet_interval_recorded_ns=(before-quiet)*1000000000//hz,
        scan_call_ns=(after-before)*1000000000//hz,
        baseline_reports=sum(r['raw_timestamp']<before for r in reports),
        report_delays_ns=[(r['raw_timestamp']-before)*1000000000//hz for r in reports],
        report_count=len(reports),distinct_soc_values=len({r['soc_timer_raw'] for r in timers}),
        recognized_tsf_commands=evidence['counts']['command'],
        client_notifications_collected=notifications is not None,
        client_completion_delay_ns=own_delay,observer_completion_delay_ns=delay(observer),
        client_completion_within_four_seconds=own_delay is not None and 0<=own_delay<=4000000000,
        health_records=evidence['health_records'],connection_records=evidence['connection_records'],
        live_offline_equal=True,cleanup_qualified=True,clock_qualified=False,firmware_initiator_identified=False)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if not 1<=len(args.capture)<=3:raise ValueError('At most three saved trials')
        if args.output.exists():raise ValueError('Output already exists')
        results=[]
        for number,folder in enumerate(args.capture,1):
            hashes={}
            def read(name: str,lines: bool=False):
                with (folder/name).open('rb') as stream:raw=stream.read(32*1024*1024+1)
                if len(raw)>32*1024*1024:raise ValueError('Input exceeds size bound')
                hashes[name]=hashlib.sha256(raw).hexdigest()
                if not lines:return decode_json(raw)
                rows=raw.splitlines()
                if len(rows)>100000:raise ValueError('Input exceeds record bound')
                return [decode_json(line) for line in rows if line.strip()]
            result=characterize(read('scan-request.json'),read('live-observer.jsonl',True),read('raw-timing.jsonl',True),read('result.json'),read('observer-cleanup.json'),read('scan-client-notifications.json') if (folder/'scan-client-notifications.json').exists() else None)
            result.update(trial=number,input_sha256=hashes);results.append(result)
        write_json_new(args.output,dict(schema='scan-comparison-postmortem/v1',trials=results,private_quarantine_modified=False))
        print(json.dumps([{k:v for k,v in r.items() if k!='input_sha256'} for r in results],indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as error:parser.exit(1,f'Postmortem rejected: {error}\n')


if __name__=='__main__':raise SystemExit(main())

"""Offline exact-run comparison of READ_VALUE and QTIMER_CAPTURE reports."""
import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_ACTIONS = [3, 3, 4, 3, 3, 4, 3, 3, 4, 3, 3]


def analyze(run: Path) -> dict[str, Any]:
    session=json.loads((run/'session.json').read_text(encoding='utf-8-sig'))
    requests=[json.loads(p.read_text(encoding='utf-8-sig')) for p in sorted(run.glob('request-*.json'))]
    events=[json.loads(line) for line in (run/'raw-timing.jsonl').read_text(encoding='utf-8-sig').splitlines()]
    if not events or not requests:raise ValueError('Missing request or trace evidence')
    if session['Actions']!=EXPECTED_ACTIONS:raise ValueError('Unexpected latch experiment sequence')
    header=events[0];summary=events[-1]
    if header['kind']!='header' or header['clock_type']!=1 or header['events_lost'] or header['buffers_lost']:
        raise ValueError('Trace loss or wrong clock')
    if summary['kind']!='summary' or summary['process_status'] or summary['close_status']:
        raise ValueError('Incomplete trace decode')
    if len(requests)!=session['SampleCount'] or [r['firmware_action'] for r in requests]!=session['Actions']:
        raise ValueError('Incomplete or incorrect action sequence')
    for kind in ('command','report','soc_timer','delay'):
        if sum(e['kind']==kind for e in events)!=len(requests):raise ValueError('Extra or missing timing record')
    freq=header['perf_frequency_hz'];samples=[]
    if freq<=0:raise ValueError('Invalid QPC frequency')
    identity=(requests[0]['driver_sha256'],requests[0]['interface_index'])
    for i,request in enumerate(requests):
        if not request['success'] or not request['handle_closed'] or request['qpc_frequency_hz']!=freq:
            raise ValueError('Failed request or clock mismatch')
        begin=request['qpc_request_before'];end=requests[i+1]['qpc_request_before'] if i+1<len(requests) else float('inf')
        if (request['command']!='tsf_read_value' or
            (request['driver_sha256'],request['interface_index'])!=identity or
            not begin<=request['qpc_request_completed']<end):
            raise ValueError('Mixed target/build, wrong command, or overlapping request windows')
        selected={kind:[e for e in events if e['kind']==kind and begin<=e['raw_timestamp']<end]
                  for kind in ('command','report','soc_timer','delay')}
        if any(len(v)!=1 for v in selected.values()):raise ValueError('Missing or ambiguous report group')
        command,report,soc,delay=[selected[k][0] for k in selected]
        if command['action']!=request['firmware_action'] or command['vdev']!=report['vdev'] or report['vdev']!=delay['vdev']:
            raise ValueError('Wrong action/vdev correlation')
        if not command['raw_timestamp']<=report['raw_timestamp']<=soc['raw_timestamp']<=delay['raw_timestamp']:
            raise ValueError('Unexpected event order')
        if ((report['tsf_raw']-soc['soc_timer_raw'])&0xffffffff)!=delay['tsf_delay_raw']:
            raise ValueError('Wrong low-word arithmetic')
        samples.append({'sample':i+1,'action':command['action'],'tsf_raw':report['tsf_raw'],'soc_raw':soc['soc_timer_raw'],
                        'host_before_qpc':begin,'report_qpc':report['raw_timestamp'],
                        'command_log_to_report_log_us':(report['raw_timestamp']-command['raw_timestamp'])*1e6/freq,
                        'request_before_to_report_log_us':(report['raw_timestamp']-begin)*1e6/freq})
    captures=[s for s in samples if s['action']==4]
    result={'sample_count':len(samples),'capture_count':len(captures),'samples':samples,
            'all_capture_soc_values_changed':all(s['soc_raw']!=samples[s['sample']-2]['soc_raw'] for s in captures if s['sample']>1),
            'all_read_soc_values_reused_previous':all(s['soc_raw']==samples[i-1]['soc_raw'] for i,s in enumerate(samples) if i and s['action']==3),
            'tsf_strictly_increasing':all(samples[i]['tsf_raw']>samples[i-1]['tsf_raw'] for i in range(1,len(samples))),
            'capture_tsf_minus_soc_raw':[s['tsf_raw']-s['soc_raw'] for s in captures],
            'simultaneity_validated':False,'absolute_accuracy_validated':False}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);args=parser.parse_args()
    result=analyze(args.run)
    (args.run/'latch-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))

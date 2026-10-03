"""Join a completed V2 capture and classify each public query offline.

Raw receipts stay private. stdout contains only sanitized operation summaries.
This does not infer hardware capability or the original rejecting layer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
import uuid

from ndis_evidence import correlate, decode_json, load_json, write_json_new, NDIS_PROVIDER, MAX_FILE_BYTES

MARKER_PROVIDER='209754d0-15cd-42dd-a9b9-d1b38a606c08'
EVENT_IDS={10101,10102,10111,10112,10018,10052}
IDENTITY='provider id version pid tid activity_id provider_sequence'.split()
QUERY_KEYS='schema operation oid pid tid qpc_before qpc_after qpc_frequency_hz return_code activity_id interface_index interface_luid'.split()


def load_native_records(path: Path) -> list[dict[str,Any]]:
    with path.open('rb') as stream:
        raw=stream.read(MAX_FILE_BYTES+1)
    if len(raw)>MAX_FILE_BYTES:raise ValueError('Native metadata exceeds size limit')
    records=[decode_json(line) for line in raw.splitlines() if line]
    if len(records)>65538 or any(type(row) is not dict for row in records):
        raise ValueError('Invalid native record stream')
    return records


def validate_cross_values(query: dict[str,Any], values: Any) -> bool:
    keys=('system_timestamp_1','hardware_clock_timestamp','system_timestamp_2')
    if type(values) is not dict or set(values)!=set(keys):raise ValueError('Invalid cross-timestamp fields')
    for value in values.values():
        if type(value) is not str or not re.fullmatch(r'0|[1-9][0-9]{0,19}',value) or int(value)>=(1<<64):
            raise ValueError('Cross timestamps require canonical unsigned 64-bit strings')
    a,hardware,b=(int(values[k]) for k in keys)
    return 0<a<=b and hardware>0 and int(query['qpc_before'])<=a<=b<=int(query['qpc_after'])


def _number(value: Any, bits: int) -> int:
    if type(value) is not str or not value or len(value)>24:
        raise ValueError('Invalid rendered integer')
    result=int(value,16 if value.lower().startswith('0x') else 10)
    if not 0<=result<(1<<bits):raise ValueError('Rendered integer exceeds field width')
    return result


def join_events(native: list[dict[str,Any]], named: list[dict[str,Any]]) -> tuple[list[dict[str,Any]],list[dict[str,Any]],list[dict[str,Any]]]:
    """Require one-to-one provider-order/identity agreement before joining payloads."""
    if type(native) is not list or type(named) is not list or len(native)>65536 or len(named)>65536:
        raise ValueError('Invalid event collection')
    indexes=[]
    for rows in (native,named):
        result={};sequence={}
        for row in rows:
            if type(row) is not dict:raise ValueError('Invalid event record')
            provider=row['provider']
            if provider not in (NDIS_PROVIDER,MARKER_PROVIDER):raise ValueError('Unexpected selected provider')
            expected=sequence.get(provider,0)+1
            if type(row['provider_sequence']) is not int or row['provider_sequence']!=expected:
                raise ValueError('Duplicate or unordered provider sequence')
            sequence[provider]=expected;result[(provider,expected)]=row
        indexes.append(result)
    if indexes[0].keys()!=indexes[1].keys():raise ValueError('Native/named provider record counts differ')
    events=[];markers=[];excluded=[]
    for key,raw in indexes[0].items():
        rendered=indexes[1][key]
        if raw.get('kind')!='event' or any(raw[k]!=rendered[k] for k in IDENTITY):
            raise ValueError('Native/named event identity or order differs')
        event={k:raw[k] for k in ('provider','id','version','qpc','pid','tid','activity_id')}
        if raw['provider']==MARKER_PROVIDER:
            markers.append(event);continue
        if raw['id'] not in EVENT_IDS:
            excluded.append(dict(event,original_data=rendered['data']));continue
        fields={}
        for field,value in rendered['data'].items():
            if field=='IfGuid':fields[field]=str(uuid.UUID(value))
            elif field in ('IfIndex','NetLuid','Location'):fields[field]=str(_number(value,64 if field=='NetLuid' else 32))
            elif field in ('Oid','RequestType','Status','Request'):
                bits=64 if field=='Request' else 32
                fields[field]=f'0x{_number(value,bits):0{bits//4}x}'
            elif field=='CompleteRequest':
                if value not in ('true','false','0','1'):raise ValueError('Invalid rendered Boolean')
                fields[field]=value in ('true','1')
            else:raise ValueError('Unknown named payload field')
        events.append(dict(event,data=fields))
    return events,markers,excluded


def validate_markers(query: dict[str,Any], markers: list[dict[str,Any]]) -> None:
    matched=[m for m in markers if m['activity_id']==query['activity_id']]
    if len(matched)!=2 or any(m['provider']!=MARKER_PROVIDER or m['id']!=0 or m['version']!=0 or m['pid']!=query['pid'] or m['tid']!=query['tid'] for m in matched):
        raise ValueError('Missing or ambiguous query markers')
    if not int(matched[0]['qpc'])<=int(query['qpc_before'])<=int(query['qpc_after'])<=int(matched[1]['qpc']):
        raise ValueError('Query markers do not bracket API call')


def analyze_run(root: Path) -> dict[str,Any]:
    acquisition=load_json(root/'result.json')
    if acquisition['AcquisitionCompleted'] is not True or acquisition['TraceCleanupSucceeded'] is not True or acquisition['PrivateRequestSent'] is not False:
        raise ValueError('Acquisition/cleanup receipt did not pass')
    before=load_json(root/'topology-before.json');after=load_json(root/'topology-after.json')
    session=load_json(root/'session.json')
    if before['target']['index']!=session['InterfaceIndex'] or before['target']['guid']!=str(uuid.UUID(session['InterfaceGuid'])):
        raise ValueError('Session target differs from topology')
    health_path=root/'trace-health.stdout.txt'
    records=load_native_records(health_path)
    if len(records)<2 or records[0]['kind']!='header' or records[-1]['kind']!='summary':
        raise ValueError('Incomplete native decode')
    header,summary=records[0],records[-1]
    events,markers,excluded=join_events(records[1:-1],load_json(root/'named-events.json'))
    if int(summary['ndis_events'])!=len(events)+len(excluded) or int(summary['marker_events'])!=len(markers):
        raise ValueError('Native provider counts inconsistent')
    query_health=load_json(root/'controller-query.stdout.txt')
    stopped=load_json(root/'controller-stop.stdout.txt')
    if any(query_health.get(k)!=0 for k in ('status','events_lost','log_buffers_lost','real_time_buffers_lost')):
        raise ValueError('Controller query health failed')
    etl=root/'ndis.etl'
    if etl.stat().st_size>8*1024*1024:raise ValueError('Trace exceeds configured cap')
    health=dict(schema='ndis-trace-health/v1',etl_sha256=hashlib.sha256(etl.read_bytes()).hexdigest(),
        ndis_sha256=session['NdisSha256'].lower(),finalized=int(header['end_time'])>0,
        file_limit_reached=etl.stat().st_size>=8*1024*1024,
        controller=dict(query_status=query_health['status'],stop_status=stopped['status'],events_lost=stopped['events_lost'],
            log_buffers_lost=stopped['log_buffers_lost'],realtime_buffers_lost=stopped['real_time_buffers_lost'],buffers_written=stopped['buffers_written']),
        header=dict(events_lost=header['events_lost'],buffers_lost=header['buffers_lost'],end_time_100ns=header['end_time'],
            clock_type=header['clock_type'],perf_frequency_hz=header['perf_frequency_hz'],pointer_size=header['pointer_size'],buffers_written=header['buffers_written']),
        decode=dict(process_status=summary['process_status'],close_status=summary['close_status']))
    results=[];activities=set();last_after=-1
    for operation in ('supported','active','cross'):
        raw=load_json(root/f'query-{operation}.stdout.txt')
        process=load_json(root/f'query-{operation}.process.json')
        if raw['operation']!=operation or raw['pid']!=process['ProcessId'] or process['ExitCode']!=0 or raw['interface_guid']!=before['target']['guid']:
            raise ValueError('Query process/target identity mismatch')
        if raw['markers_requested'] is not True or any(raw[k]!=0 for k in ('marker_begin_status','marker_end_status','activity_restore_status','unregister_status')):
            raise ValueError('Query marker/activity operation failed')
        if raw['activity_id'] in activities or raw['activity_id']==str(uuid.UUID(int=0)):
            raise ValueError('Missing or reused query activity')
        activities.add(raw['activity_id'])
        if int(raw['qpc_before'])<=last_after:raise ValueError('Overlapping or reordered queries')
        last_after=int(raw['qpc_after'])
        query={k:raw[k] for k in QUERY_KEYS}
        validate_markers(query,markers)
        result=correlate(before,after,query,events,health)
        if any(int(query['qpc_before'])<=int(e['qpc'])<=int(query['qpc_after']) for e in excluded):
            result.update(classification='rejected',reasons=['Unsupported NDIS event inside query bracket'],matches=[],raw_statuses=[])
        result.update(operation=operation,public_return_code=raw['return_code'],query_duration_qpc_ticks=str(int(raw['qpc_after'])-int(raw['qpc_before'])))
        if raw['return_code']!=0 and raw['values'] is not None:raise ValueError('Failed query exposed output values')
        if operation=='cross':
            valid=False
            if raw['return_code']==0:
                valid=validate_cross_values(query,raw['values'])
            result['returned_cross_tuple_within_call_bracket']=valid
            result['calibrated_mapping_validated']=False
        results.append(result)
    if len(markers)!=6:raise ValueError('Unattributed marker records')
    return dict(schema='ndis-run-analysis/v1',health=health,operations=results,excluded_events=excluded,
        provider_record_parity=True,query_markers_verified=True,complete_request_identity_validated=False,
        original_rejecting_layer_validated=False)


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.output.exists():raise ValueError('Output already exists')
        result=analyze_run(args.run)
        write_json_new(args.output,result)
        print(json.dumps([dict(operation=r['operation'],classification=r['classification'],raw_statuses=r['raw_statuses'],
            public_return_code=r['public_return_code'],matching_events=len(r['matches']),reasons=r['reasons']) for r in result['operations']],indent=2))
        return int(any(r['classification']=='rejected' for r in result['operations']))
    except (OSError,ValueError,TypeError,KeyError,OverflowError) as error:
        parser.exit(1,f'NDIS run rejected: {error}\n')


if __name__=='__main__':raise SystemExit(main())

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/qualcomm'))
from analyze_ndis_run import analyze_run, join_events, validate_markers, load_native_records, validate_cross_values
from test_ndis_evidence import fixture as evidence_fixture

PROVIDER='cdead503-17f5-4a3e-b7ae-df8cc2902eb9'
ACTIVITY='11111111-1111-4111-8111-111111111111'
MARKER='209754d0-15cd-42dd-a9b9-d1b38a606c08'


def fixture():
    native=dict(kind='event',provider=PROVIDER,id=10111,version=0,qpc='123',pid=4,tid=1,activity_id=ACTIVITY,provider_sequence=1)
    named={k:v for k,v in native.items() if k not in ('kind','qpc')}
    named['data']=dict(IfGuid='{'+ACTIVITY+'}',IfIndex='2',NetLuid='0x20',RequestType='10485761',Status='0xc0010017',Location='65537')
    return [native],[named]


class RunTests(unittest.TestCase):
    def test_native_jsonl_rejects_duplicate_keys_and_excessive_nesting(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.jsonl'
            for content in ('{"kind":"summary","process_status":5,"process_status":0}\n','['*65+'0'+']'*65,'{"qpc":NaN}'):
                path.write_text(content)
                with self.assertRaises(ValueError):load_native_records(path)

    def test_cross_values_reject_noncanonical_and_overflow(self):
        query=dict(qpc_before='100',qpc_after='200')
        good=dict(system_timestamp_1='120',hardware_clock_timestamp='10',system_timestamp_2='180')
        self.assertTrue(validate_cross_values(query,good))
        for bad in (True,'18446744073709551616','01','1.0'):
            changed=dict(good,hardware_clock_timestamp=bad)
            with self.subTest(bad=bad),self.assertRaises(ValueError):validate_cross_values(query,changed)
        self.assertFalse(validate_cross_values(query,dict(good,system_timestamp_2='201')))

    def test_complete_run_rejects_bad_native_summary_and_overflow_cross(self):
        before,after,base,_,health=evidence_fixture()
        files={'result.json':dict(AcquisitionCompleted=True,TraceCleanupSucceeded=True,PrivateRequestSent=False),
               'topology-before.json':before,'topology-after.json':after,
               'session.json':dict(InterfaceIndex=1,InterfaceGuid=before['target']['guid'],NdisSha256=health['ndis_sha256']),
               'controller-query.stdout.txt':dict(status=0,events_lost=0,log_buffers_lost=0,real_time_buffers_lost=0),
               'controller-stop.stdout.txt':dict(status=0,events_lost=0,log_buffers_lost=0,real_time_buffers_lost=0,buffers_written=4)}
        records=[dict(kind='header',start_time='1000',end_time='2000',pointer_size=8,clock_type=1,perf_frequency_hz='10000000',events_lost=0,buffers_lost=0,buffers_written=4)]
        named=[]
        for i,operation in enumerate(('supported','active','cross')):
            activity=f'00000000-0000-4000-8000-{i+1:012d}'
            start=100+i*30;stop=start+20
            query=dict(base,operation=operation,oid=f'0x00a0000{i+1}',pid=100+i,tid=200+i,activity_id=activity,qpc_before=str(start),qpc_after=str(stop),
                       interface_guid=before['target']['guid'],values=None,markers_requested=True,marker_begin_status=0,marker_end_status=0,activity_restore_status=0,unregister_status=0)
            files[f'query-{operation}.stdout.txt']=query
            files[f'query-{operation}.process.json']=dict(ProcessId=100+i,ExitCode=0)
            for tick in (start-1,stop+1):
                row=dict(kind='event',provider=MARKER,id=0,version=0,qpc=str(tick),pid=100+i,tid=200+i,activity_id=activity,provider_sequence=len(named)+1)
                records.append(row);named.append({**{k:v for k,v in row.items() if k not in ('kind','qpc')},'data':{}})
        records.append(dict(kind='summary',process_status=0,close_status=0,events='7',ndis_events='0',marker_events='6',other_events='1'))
        files['named-events.json']=named
        with tempfile.TemporaryDirectory() as folder,patch('analyze_ndis_run.load_json',side_effect=lambda p:files[p.name]):
            root=Path(folder);(root/'ndis.etl').write_bytes(b'synthetic')
            native='\n'.join(json.dumps(row) for row in records)
            path=root/'trace-health.stdout.txt';path.write_text(native)
            self.assertEqual([r['classification'] for r in analyze_run(root)['operations']],['inconclusive']*3)
            path.write_text(native.replace('"process_status": 0','"process_status": 5, "process_status": 0'))
            with self.assertRaises(ValueError):analyze_run(root)
            path.write_text(native)
            files['query-cross.stdout.txt'].update(return_code=0,values=dict(system_timestamp_1='165',hardware_clock_timestamp=str(2**64),system_timestamp_2='170'))
            with self.assertRaises(ValueError):analyze_run(root)

    def test_join_normalizes_without_losing_raw_field_name(self):
        events,markers,excluded=join_events(*fixture())
        self.assertEqual(events[0]['data']['RequestType'],'0x00a00001')
        self.assertNotIn('Oid',events[0]['data'])
        self.assertEqual(events[0]['data']['NetLuid'],'32')
        self.assertFalse(markers);self.assertFalse(excluded)

    def test_join_rejects_missing_duplicate_reordered_and_identity_mismatch(self):
        for field,value in [('provider_sequence',2),('pid',99),('activity_id','00000000-0000-0000-0000-000000000000')]:
            a,b=fixture();b[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):join_events(a,b)
        a,b=fixture()
        with self.assertRaises(ValueError):join_events(a,[])
        with self.assertRaises(ValueError):join_events(a+a,b+b)

    def test_unknown_ids_are_retained_as_exclusions(self):
        a,b=fixture();a[0]['id']=b[0]['id']=999
        events,markers,excluded=join_events(a,b)
        self.assertFalse(events);self.assertEqual(excluded[0]['id'],999)

    def test_markers_require_two_matching_activity_pid_tid_and_bracket(self):
        query=dict(activity_id=ACTIVITY,pid=10,tid=11,qpc_before='100',qpc_after='200')
        good=[dict(provider=MARKER,id=0,version=0,activity_id=ACTIVITY,pid=10,tid=11,qpc=q) for q in ('99','201')]
        validate_markers(query,good)
        for changes in ('missing','inside','pid'):
            bad=copy.deepcopy(good)
            if changes=='missing':bad.pop()
            if changes=='inside':bad[0]['qpc']='101'
            if changes=='pid':bad[1]['pid']=12
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_markers(query,bad)

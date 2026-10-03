"""Synthetic-only NDIS evidence tests; no IP Helper or device calls."""
import copy
import importlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

try:
    ndis = importlib.import_module('research.windows_timestamps.ndis_evidence')
except ModuleNotFoundError:
    ndis = None

TARGET = '11111111-1111-4111-8111-111111111111'
FILTER = '22222222-2222-4222-8222-222222222222'
OTHER = '33333333-3333-4333-8333-333333333333'
ACTIVITY = '44444444-4444-4444-8444-444444444444'
PROVIDER = 'cdead503-17f5-4a3e-b7ae-df8cc2902eb9'
NDIS_BUILD = 'd90b185d403966577fe5f8bed708a4b09c8da68730690e89f9ad41304792f64a'


def fixture():
    rows = [dict(index=i, guid=g, luid=str(i * 100), flags=f, type=71,
                 physical=9, oper_status=1, admin_status=1, media_connect_state=1)
            for i, g, f in [(1, TARGET, 1), (2, FILTER, 2), (3, OTHER, 1)]]
    before = dict(schema='ndis-topology/v1', clock='qpc', qpc_frequency_hz='10000000',
                  qpc_before='90', qpc_after='95',
                  utc_before='2026-10-03T00:00:00+00:00',
                  utc_after='2026-10-03T00:00:01+00:00', observation_atomic=False,
                  target=dict(index=1, guid=TARGET, luid='100'), rows=rows,
                  edges=[dict(upper=2, lower=1)], unresolved_indices=[])
    after = copy.deepcopy(before)
    after.update(qpc_before='205', qpc_after='210',
                 utc_before='2026-10-03T00:00:02+00:00',
                 utc_after='2026-10-03T00:00:03+00:00')
    query = dict(schema='ndis-query/v1', operation='supported', oid='0x00a00001',
                 pid=100, tid=101, qpc_before='100', qpc_after='200',
                 qpc_frequency_hz='10000000', return_code=23, activity_id=ACTIVITY,
                 interface_index=1, interface_luid='100')
    event = dict(provider=PROVIDER, id=10101, version=0, activity_id=ACTIVITY,
                 pid=4, tid=20, qpc='150', data=dict(IfGuid=FILTER, IfIndex='2',
                 NetLuid='200', Request='0x000000000000abcd', CompleteRequest=True,
                 Status='0xc0010017', Oid='0x00a00001'))
    health = dict(schema='ndis-trace-health/v1', etl_sha256='a' * 64,
                  ndis_sha256=NDIS_BUILD, finalized=True, file_limit_reached=False,
                  controller=dict(query_status=0, stop_status=0, events_lost=0,
                  log_buffers_lost=0, realtime_buffers_lost=0, buffers_written=4),
                  header=dict(events_lost=0, buffers_lost=0, end_time_100ns='1234',
                  clock_type=1, perf_frequency_hz='10000000', pointer_size=8,
                  buffers_written=4), decode=dict(process_status=0, close_status=0))
    return before, after, query, [event], health


class NdisEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(ndis, 'NDIS evidence correlator is not implemented')

    def test_activity_correlated_status_is_not_hardware_or_lifecycle_proof(self):
        data = fixture()
        unchanged = copy.deepcopy(data)
        result = ndis.correlate(*data)
        self.assertEqual(result['classification'], 'activity_stack_correlated')
        self.assertEqual(result['raw_statuses'], ['0xc0010017'])
        self.assertFalse(result['request_lifecycle_validated'])
        self.assertFalse(result['hardware_capability_validated'])
        self.assertEqual(result['matches'][0]['downward_hops'], 1)
        self.assertEqual(data, unchanged)

    def test_missing_or_unmatched_activity_never_becomes_activity_bound(self):
        for activity in [None, OTHER, '00000000-0000-0000-0000-000000000000']:
            data = fixture()
            data[3][0]['activity_id'] = activity
            self.assertEqual(ndis.correlate(*data)['classification'], 'temporal_stack_candidate')

    def test_interface_scoped_activity_cannot_bind_application_query(self):
        data=fixture()
        data[2]['activity_id']=FILTER
        data[3][0]['activity_id']=FILTER
        result=ndis.correlate(*data)
        self.assertEqual(result['classification'],'temporal_stack_candidate')
        self.assertEqual(result['matches'][0]['activity_scope'],'interface')

    def test_exact_build_requesttype_inference_preserves_original_field(self):
        data = fixture()
        event = data[3][0]
        event['id'] = 10111
        event['data'].pop('Request')
        event['data'].pop('CompleteRequest')
        event['data']['RequestType'] = event['data'].pop('Oid')
        event['data']['Location'] = '65537'
        result = ndis.correlate(*data)
        self.assertEqual(result['classification'], 'temporal_stack_candidate')
        self.assertEqual(result['matches'][0]['oid_interpretation'], 'RequestType_inferred_exact_build')
        self.assertIn('RequestType', result['matches'][0]['data'])
        self.assertNotIn('Oid', result['matches'][0]['data'])
        data[4]['ndis_sha256'] = 'b' * 64
        self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')

    def test_multiple_filter_candidates_are_not_multiple_bound_requests(self):
        data = fixture()
        event = data[3][0]
        event.update(id=10111, activity_id=None)
        event['data'] = dict(IfGuid=FILTER, IfIndex='2', NetLuid='200',
                            RequestType='0x00a00001', Status='0xc0010017', Location='65537')
        data[3].append(copy.deepcopy(event))
        data[3][1]['qpc'] = '151'
        data[3][1]['data'].update(IfGuid=TARGET, IfIndex='1', NetLuid='100')
        self.assertEqual(ndis.correlate(*data)['classification'], 'temporal_stack_candidate')

    def test_no_matching_event_is_inconclusive(self):
        data = fixture()
        data[3].clear()
        self.assertEqual(ndis.correlate(*data)['classification'], 'inconclusive')
        data = fixture()
        data[3][0]['qpc'] = '201'
        self.assertEqual(ndis.correlate(*data)['classification'], 'inconclusive')

    def test_health_loss_missing_fields_and_unfinalized_are_rejected(self):
        for mutation in ['loss', 'missing', 'unfinished', 'full', 'decode', 'clock', 'end']:
            data = fixture()
            health = data[4]
            if mutation == 'loss': health['controller']['log_buffers_lost'] = 1
            if mutation == 'missing': health.pop('controller')
            if mutation == 'unfinished': health['finalized'] = False
            if mutation == 'full': health['file_limit_reached'] = True
            if mutation == 'decode': health['decode']['process_status'] = 1
            if mutation == 'clock': health['header']['clock_type'] = 2
            if mutation == 'end': health['header']['end_time_100ns'] = '0'
            with self.subTest(mutation=mutation):
                self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')

    def test_epoch_identity_and_graph_changes_are_rejected(self):
        for mutation in ['luid', 'guid', 'edge', 'cycle', 'duplicate', 'flags', 'order']:
            data = fixture()
            after = data[1]
            if mutation == 'luid': after['rows'][1]['luid'] = '999'
            if mutation == 'guid': after['rows'][1]['guid'] = ACTIVITY
            if mutation == 'edge': after['edges'].clear()
            if mutation == 'cycle': after['edges'].append(dict(upper=1, lower=2))
            if mutation == 'duplicate': after['rows'].append(copy.deepcopy(after['rows'][1]))
            if mutation == 'flags': after['rows'][1]['flags'] = 1
            if mutation == 'order': after['qpc_before'] = '150'
            with self.subTest(mutation=mutation):
                self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')

    def test_unrelated_interface_churn_does_not_invalidate_target_path(self):
        data = fixture()
        data[1]['rows'][2]['luid'] = '999'
        self.assertEqual(ndis.correlate(*data)['classification'], 'activity_stack_correlated')

    def test_missing_unrelated_stack_vertex_is_recorded_without_rejecting_target(self):
        data = fixture()
        for snapshot in data[:2]:
            snapshot['edges'].append(dict(upper=3, lower=99))
            snapshot['unresolved_indices'] = [99]
        self.assertEqual(ndis.correlate(*data)['classification'], 'activity_stack_correlated')

    def test_missing_target_ancestor_and_forged_unresolved_inventory_are_rejected(self):
        data = fixture()
        for snapshot in data[:2]:
            snapshot['edges'].append(dict(upper=99, lower=2))
            snapshot['unresolved_indices'] = [99]
        self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')
        data[0]['unresolved_indices'] = []
        self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')

    def test_ambiguous_request_or_conflicting_status_is_rejected(self):
        for mutation in ['request', 'status']:
            data = fixture()
            data[3].append(copy.deepcopy(data[3][0]))
            data[3][1]['qpc'] = '151'
            if mutation == 'request': data[3][1]['data']['Request'] = '0x000000000000abce'
            if mutation == 'status': data[3][1]['data']['Status'] = '0x00000000'
            self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')

    def test_schema_numbers_versions_and_identity_are_strict(self):
        for mutation in ['boolean', 'zeroes', 'wide', 'missing_status', 'version', 'tuple', 'oid']:
            data = fixture()
            if mutation == 'boolean': data[2]['pid'] = True
            if mutation == 'zeroes': data[2]['qpc_before'] = '0100'
            if mutation == 'wide': data[3][0]['data']['Status'] = '0x100000000'
            if mutation == 'missing_status': data[3][0]['data'].pop('Status')
            if mutation == 'version': data[3][0]['version'] = 1
            if mutation == 'tuple': data[3][0]['data']['NetLuid'] = '999'
            if mutation == 'oid': data[2]['oid'] = '0x00a00002'
            with self.subTest(mutation=mutation):
                self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')

    def test_zero_boundary_edges_and_large_graph_are_bounded(self):
        data = fixture()
        for snapshot in data[:2]:
            snapshot['edges'] += [dict(upper=0, lower=2), dict(upper=1, lower=0)]
        self.assertEqual(ndis.correlate(*data)['classification'], 'activity_stack_correlated')
        data[0]['rows'] *= 1400
        self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')

    def test_partial_completion_and_orphan_pointer_cannot_bind_query(self):
        data = fixture()
        data[3][0]['data']['CompleteRequest'] = False
        self.assertEqual(ndis.correlate(*data)['classification'], 'inconclusive')
        event = data[3][0]
        event['id'] = 10102
        event['data'].pop('CompleteRequest')
        event['data'].pop('Oid')
        event['data']['Location'] = '1'
        self.assertEqual(ndis.correlate(*data)['classification'], 'inconclusive')

    def test_file_contract_rejects_duplicate_keys_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            path.write_text('{"a":1,"a":2}', encoding='utf-8')
            with self.assertRaises(ValueError): ndis.load_json(path)
            with self.assertRaises(FileExistsError): ndis.write_json_new(path, {'replacement': True})
            self.assertEqual(path.read_text(), '{"a":1,"a":2}')

    def test_signed_qpc_width_and_excessive_json_nesting_are_rejected(self):
        data = fixture()
        data[3][0]['qpc'] = str(1 << 63)
        self.assertEqual(ndis.correlate(*data)['classification'], 'rejected')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'deep.json'
            path.write_text('[' * 1100 + '0' + ']' * 1100, encoding='utf-8')
            with self.assertRaises(ValueError): ndis.load_json(path)

    def test_cli_writes_private_result_without_stdout_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = ['before', 'after', 'query', 'events', 'health']
            command = [sys.executable, str(Path(ndis.__file__)), 'correlate']
            for name, value in zip(names, fixture()):
                path = root / (name + '.json')
                path.write_text(json.dumps(value), encoding='utf-8')
                command += ['--' + name, str(path)]
            output = root / 'result.json'
            command += ['--output', str(output)]
            process = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(json.loads(process.stdout)['classification'], 'activity_stack_correlated')
            for identity in (TARGET, FILTER, ACTIVITY, '0x000000000000abcd'):
                self.assertNotIn(identity, process.stdout)
            original = output.read_bytes()
            retry = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(retry.returncode, 1)
            self.assertEqual(output.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()

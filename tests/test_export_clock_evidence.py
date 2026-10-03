import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from test_analyze_tsf_series import fixture
from qualcomm_protocol import QUALIFIED_SHA256
from export_clock_evidence import normalize_run, export_sanitized


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.requests, self.events = fixture()
        for request in self.requests:
            request['driver_sha256'] = QUALIFIED_SHA256
            request['secret_extra'] = 'DO-NOT-EXPORT'
        self.save()

    def save(self):
        (self.run/'session.json').write_text(json.dumps({'SampleCount': len(self.requests)}))
        for i, request in enumerate(self.requests):
            (self.run/f'request-{i+1:03}.json').write_text(json.dumps(request))
        (self.run/'raw-timing.jsonl').write_text('\n'.join(map(json.dumps, self.events)))
        for name in ('adapter-before.json', 'adapter-after.json'):
            (self.run/name).write_text(json.dumps(dict(Status='Up', ifIndex=7, DriverVersion='1.0.4374.1300')))

    def test_export_is_deterministic_and_restricts_claims(self):
        bundle = normalize_run(self.run, evidence_kind='synthetic')
        a = export_sanitized(bundle, self.run/'a.json')
        b = export_sanitized(bundle, self.run/'b.json')
        self.assertEqual(a.sha256, b.sha256)
        data = json.loads((self.run/'a.json').read_text())
        self.assertNotIn('DO-NOT-EXPORT', (self.run/'a.json').read_text())
        sample = data['observations'][0]
        self.assertIsNone(sample['sampling_interval'])
        self.assertIsNone(sample['external_uncertainty_ns'])
        self.assertEqual(sample['soc_semantics'], 'cached_or_unknown')
        self.assertIsInstance(sample['tsf_raw'], str)
        self.assertEqual(data['manifest']['qualification'], 'experimental-observation-only')
        with self.assertRaises(FileExistsError): export_sanitized(bundle, self.run/'a.json')

    def test_missing_duplicate_lost_or_failed_evidence_rejected(self):
        for mutation in ('missing', 'duplicate', 'loss', 'timeout', 'build', 'counter', 'bool'):
            with self.subTest(mutation=mutation):
                original = copy.deepcopy((self.requests,self.events))
                if mutation == 'missing': self.events.pop(2)
                if mutation == 'duplicate': self.events.insert(3, self.events[2])
                if mutation == 'loss': self.events[0]['events_lost'] = 1
                if mutation == 'timeout': self.requests[0]['success'] = False
                if mutation == 'build': self.requests[0]['driver_sha256'] = '0'*64
                if mutation == 'counter': self.events[6]['tsf_raw'] = 1
                if mutation == 'bool': self.requests[0]['qpc_request_before'] = True
                self.save()
                with self.assertRaises(ValueError): normalize_run(self.run)
                self.requests,self.events = original
                self.save()

    def test_mixed_files_and_bad_final_state_rejected(self):
        (self.run/'request.json').write_text(json.dumps(self.requests[0]))
        with self.assertRaises(ValueError): normalize_run(self.run)
        (self.run/'request.json').unlink()
        (self.run/'adapter-after.json').write_text(json.dumps(dict(Status='Down',ifIndex=7,DriverVersion='1.0.4374.1300')))
        with self.assertRaises(ValueError): normalize_run(self.run)

    def test_all_counts_and_unsigned_counters_are_bounded(self):
        self.events[2]['tsf_raw'] = 1 << 64
        self.save()
        with self.assertRaises(ValueError): normalize_run(self.run)


if __name__ == '__main__': unittest.main()

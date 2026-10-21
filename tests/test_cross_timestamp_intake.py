"""Authored fixtures only: no adapter APIs or captured hardware evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.clock_models import cross_timestamp_intake as intake
from research.clock_models import microsecond_feasibility as feasibility


def fixture(root: Path) -> dict:
    source = root / 'capture.txt'
    source.write_bytes(b'Authored synthetic fixture, not a hardware capture.\n')
    return {
        'schema': intake.INPUT_SCHEMA, 'provenance': 'synthetic',
        'scope': {'adapter': 'fixture-adapter', 'driver_sha256': 'a' * 64,
                  'firmware': 'unknown', 'os_build': 'fixture', 'host': 'fixture-host',
                  'clock_domain': 'unknown'},
        'qpc_frequency_hz': 10_000_000, 'pairing_limit_us': 3,
        'references': {'capture': {'path': 'capture.txt',
                                  'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}},
        'claims': {name: {'basis': 'unknown', 'statement': 'Not established',
                          'references': []} for name in intake.CLAIMS},
        'attempt_accounting': {condition: {'issued': 1, 'reference': 'capture'}
                               for condition in ('idle', 'load')},
        'attempts': [
            {'condition': condition, 'epoch': 'fixture-epoch', 'attempt_id': str(index),
             'reference': 'capture', 'status': 0, 'qpc_before': 2**60 + index * 100,
             'hardware_ticks': 100 + index, 'qpc_after': 2**60 + index * 100 + 40}
            for index, condition in enumerate(('idle', 'load'))],
    }


class CrossTimestampIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)

    def test_exact_integer_arithmetic_above_float_precision(self):
        self.data['qpc_frequency_hz'] = 3_000_000
        self.data['attempts'][0]['qpc_after'] = self.data['attempts'][0]['qpc_before'] + 1
        result = intake.audit(self.data, self.root)
        self.assertEqual(result['attempts'][0]['bracket_half_width_us'],
                         {'numerator': 1, 'denominator': 6})
        self.assertEqual(result['attempts'][0]['qpc_before'], 2**60)

    def test_failures_and_tails_remain_in_denominator(self):
        self.data['attempts'][0]['qpc_after'] += 1000
        self.data['attempts'].append({'condition': 'load', 'epoch': 'fixture-epoch',
                                      'attempt_id': 'failed', 'reference': 'capture', 'status': 23})
        self.data['attempt_accounting']['load']['issued'] = 2
        result = intake.audit(self.data, self.root)
        self.assertEqual(result['conditions']['load']['attempts'], 2)
        self.assertEqual(result['conditions']['load']['failed'], 1)
        self.assertEqual(result['conditions']['idle']['over_limit'], 1)
        self.assertEqual(len(result['attempts']), 3)
        self.assertIn('capture_failures_present', result['blockers'])
        self.assertIn('pairing_limit_exceeded', result['blockers'])

    def test_equal_qpc_does_not_establish_zero_error(self):
        row = self.data['attempts'][0]
        row['qpc_after'] = row['qpc_before']
        result = intake.audit(self.data, self.root)
        self.assertEqual(result['attempts'][0]['bracket_half_width_us']['numerator'], 0)
        self.assertIn('equal_qpc_requires_capture_error_evidence', result['blockers'])
        self.assertFalse(result['gate1_qualified'])

    def test_supported_claims_still_require_review_and_never_qualify(self):
        self.data['provenance'] = 'retained_capture'
        self.data['scope']['clock_domain'] = 'documented-fixture-domain'
        for claim in self.data['claims'].values():
            claim.update(basis='measured', references=['capture'])
        result = intake.audit(self.data, self.root)
        self.assertEqual(result['blockers'], [])
        self.assertEqual(result['verdict'], 'ready_for_semantic_review')
        self.assertFalse(result['gate1_qualified'])
        self.assertFalse(result['physical_bound_proven'])
        self.assertNotIn('candidates', result)

    def test_unknowns_and_synthetic_provenance_cannot_reopen_gate(self):
        result = intake.audit(self.data, self.root)
        self.assertIn('synthetic_evidence', result['blockers'])
        self.assertIn('unknown_clock_domain', result['blockers'])
        for name in intake.CLAIMS:
            self.assertIn('unresolved_' + name, result['blockers'])

    def test_missing_condition_is_reported(self):
        self.data['attempts'] = self.data['attempts'][:1]
        self.assertIn('missing_load_capture', intake.audit(self.data, self.root)['blockers'])

    def test_declared_denominator_exposes_omitted_and_unknown_attempts(self):
        self.data['attempt_accounting']['load']['issued'] = 5
        result = intake.audit(self.data, self.root)
        self.assertEqual(result['conditions']['load']['issued'], 5)
        self.assertEqual(result['conditions']['load']['unrepresented'], 4)
        self.assertIn('unrepresented_load_attempts', result['blockers'])
        self.data['attempt_accounting']['idle']['issued'] = None
        result = intake.audit(self.data, self.root)
        self.assertIsNone(result['conditions']['idle']['unrepresented'])
        self.assertIn('unknown_idle_attempt_count', result['blockers'])

    def test_missing_contradictory_or_unreferenced_denominators_rejected(self):
        for accounting in (None, {}, {'idle': {'issued': 1, 'reference': 'capture'},
                                     'load': {'issued': 0, 'reference': 'capture'}},
                           {'idle': {'issued': 1, 'reference': 'capture'},
                            'load': {'issued': True, 'reference': 'capture'}},
                           {'idle': {'issued': 1, 'reference': 'capture'},
                            'load': {'issued': 1, 'reference': 'missing'}}):
            data = copy.deepcopy(self.data)
            data['attempt_accounting'] = accounting
            with self.subTest(accounting=accounting), self.assertRaises(ValueError):
                intake.audit(data, self.root)

    def test_reject_malformed_raw_fields(self):
        for key, value in [('status', True), ('qpc_before', 1.0), ('hardware_ticks', 0),
                           ('qpc_after', -1), ('qpc_after', 2**64), ('qpc_after', None)]:
            data = copy.deepcopy(self.data)
            data['attempts'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                intake.audit(data, self.root)

    def test_reject_reversed_qpc_and_duplicate_identity(self):
        self.data['attempts'][0]['qpc_after'] = 1
        with self.assertRaises(ValueError):
            intake.audit(self.data, self.root)
        self.data = fixture(self.root)
        self.data['attempts'].append(copy.deepcopy(self.data['attempts'][0]))
        with self.assertRaises(ValueError):
            intake.audit(self.data, self.root)

    def test_counter_wrap_is_retained_without_inferred_continuity(self):
        self.data['attempts'][0]['hardware_ticks'] = 2**32 - 1
        self.data['attempts'][1]['hardware_ticks'] = 1
        self.assertEqual(len(intake.audit(self.data, self.root)['attempts']), 2)

    def test_reject_bad_frequency_limit_schema_scope_and_claim(self):
        for key, value in [('qpc_frequency_hz', 0), ('qpc_frequency_hz', True),
                           ('pairing_limit_us', 0), ('pairing_limit_us', 11),
                           ('schema', 'other'), ('scope', {})]:
            data = copy.deepcopy(self.data)
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                intake.audit(data, self.root)
        self.data['claims']['fresh'].update(basis='documented', references=['capture'])
        self.assertIn('unresolved_fresh', intake.audit(self.data, self.root)['blockers'])
        self.data['claims']['fresh']['references'] = ['missing']
        with self.assertRaises(ValueError):
            intake.audit(self.data, self.root)

    def test_hash_and_path_constraints(self):
        for path in ('../capture.txt', str(self.root / 'capture.txt'), 'https://example.com/a',
                     'capture.txt:stream'):
            data = copy.deepcopy(self.data)
            data['references']['capture']['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                intake.audit(data, self.root)
        self.data['references']['capture']['sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            intake.audit(self.data, self.root)

    def test_cli_exit_codes_and_strict_json(self):
        path = self.root / 'manifest.json'
        module = 'research.clock_models.cross_timestamp_intake'
        path.write_text(json.dumps(self.data), encoding='utf-8')
        result = subprocess.run([sys.executable, '-m', module, str(path)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(json.loads(result.stdout)['gate1_qualified'])
        self.assertEqual(json.loads(result.stdout)['manifest_sha256'],
                         hashlib.sha256(path.read_bytes()).hexdigest())
        self.data['provenance'] = 'retained_capture'
        self.data['scope']['clock_domain'] = 'fixture-domain'
        for claim in self.data['claims'].values():
            claim.update(basis='measured', references=['capture'])
        path.write_text(json.dumps(self.data), encoding='utf-8')
        result = subprocess.run([sys.executable, '-m', module, str(path)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['gate1_qualified'])
        for text in ('{"schema":1,"schema":2}', '{"schema":NaN}', '[]',
                     '{"qpc_frequency_hz":1e999}'):
            path.write_text(text, encoding='utf-8')
            result = subprocess.run([sys.executable, '-m', module, str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertNotIn('Traceback', result.stderr)

    def test_overflowing_json_number_in_valid_manifest_is_rejected(self):
        path = self.root / 'manifest.json'
        text = json.dumps(self.data)[:-1] + ', "extra": 1e999}'
        path.write_text(text, encoding='utf-8')
        result = subprocess.run([sys.executable, '-m',
                                 'research.clock_models.cross_timestamp_intake', str(path)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_symlink_loop_has_deterministic_cli_error(self):
        first, second = self.root / 'first.txt', self.root / 'second.txt'
        try:
            first.symlink_to(second.name)
            second.symlink_to(first.name)
        except OSError as error:
            self.skipTest(f'Filesystem symlink unavailable: {error}')
        self.data['references']['capture']['path'] = first.name
        path = self.root / 'manifest.json'
        path.write_text(json.dumps(self.data), encoding='utf-8')
        result = subprocess.run([sys.executable, '-m',
                                 'research.clock_models.cross_timestamp_intake', str(path)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_external_symlink_is_rejected(self):
        outside = self.root.parent / (self.root.name + '-outside.txt')
        outside.write_bytes(b'outside synthetic fixture')
        self.addCleanup(outside.unlink)
        link = self.root / 'linked.txt'
        try:
            link.symlink_to(outside)
        except OSError as error:
            self.skipTest(f'Filesystem symlink unavailable: {error}')
        self.data['references']['capture'] = {
            'path': 'linked.txt', 'sha256': hashlib.sha256(outside.read_bytes()).hexdigest()}
        with self.assertRaises(ValueError):
            intake.audit(self.data, self.root)

    def test_checked_in_example_is_synthetic_and_blocked(self):
        path = Path(__file__).parent / 'fixtures/cross_timestamp_intake/manifest.json'
        result = intake.audit(json.loads(path.read_text(encoding='utf-8')), path.parent)
        self.assertEqual(result['provenance'], 'synthetic')
        self.assertEqual(result['verdict'], 'intake_blocked')
        self.assertEqual(result['conditions']['load']['failed'], 1)

    def test_existing_feasibility_baseline_unchanged(self):
        result = feasibility.baseline()
        self.assertEqual(result['verdict'], 'killed_at_gate1_no_qualified_capture_path')
        self.assertEqual(result['model_half_width_us'],
                         {'settled_v2_median_us': 133.371, 'settled_v3_median_us': 158.371,
                          'floor_us': 127})


if __name__ == '__main__':
    unittest.main()

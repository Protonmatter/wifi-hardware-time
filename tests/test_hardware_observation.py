"""Diagnostic TSF admission never promotes saved reports into clock inputs."""
import copy
import json
from pathlib import Path
import unittest

from research.evidence.hardware_observation import validate_observation

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures/synthetic/clock-evidence-v1.json'


def envelope():
    return {'schema': 'tsf-evidence-selection/v1',
            'bundle': json.loads(FIXTURE.read_text()), 'sequence': 1}


class ObservationTests(unittest.TestCase):
    def test_reads_counter_without_claiming_clock_quality(self):
        result = validate_observation(envelope())
        self.assertEqual(result['tsf_raw'], '1000000')
        self.assertEqual(result['evidence_kind'], 'synthetic')
        self.assertEqual(result['qualification'], 'diagnostic-only')
        self.assertFalse(result['clock_input_eligible'])
        self.assertIsNone(result['meaningful_bits'])
        self.assertIsNone(result['sampling_interval_qpc'])
        self.assertIsNone(result['sample_age_ns'])
        self.assertEqual(result['storage_bits'], 64)
        self.assertEqual(result['source_binding'], 'bundle-local-anonymized')

    def test_output_owns_nested_provenance(self):
        data = envelope()
        first = validate_observation(data)
        second = validate_observation(data)
        first['provenance']['input_sha256']['session.json'] = 'changed'
        data['bundle']['manifest']['source']['base_revision'] = 'changed'
        self.assertNotEqual(second['provenance']['input_sha256']['session.json'], 'changed')
        self.assertNotEqual(first['provenance']['source']['base_revision'], 'changed')

    def test_bundle_content_identity_includes_counter_values(self):
        data = envelope()
        first = validate_observation(data)
        data['bundle']['observations'][0]['tsf_raw'] = '1000001'
        second = validate_observation(data)
        self.assertNotEqual(first['bundle_sha256'], second['bundle_sha256'])
        self.assertNotEqual(first['capture_key'], second['capture_key'])
        self.assertEqual(first['bundle_id'], second['bundle_id'])

    def test_preserves_cached_and_capture_requested_soc_semantics(self):
        data = envelope()
        self.assertEqual(validate_observation(data)['soc_semantics'], 'cached_or_unknown')
        sample = data['bundle']['observations'][0]
        sample.update(action=4, soc_semantics='capture_requested_not_atomic')
        result = validate_observation(data)
        self.assertEqual(result['soc_semantics'], 'capture_requested_not_atomic')
        self.assertFalse(result['clock_input_eligible'])

    def test_rejects_unknown_fields_and_invalid_selection(self):
        for key, value in [('clock_input_eligible', True), ('schema', 'other'),
                           ('sequence', True), ('sequence', 0), ('sequence', 4),
                           ('sequence', '1')]:
            data = envelope()
            data[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_observation(data)

    def test_rejects_entire_bundle_even_when_bad_sample_is_not_selected(self):
        for key, value in [('sequence', 2), ('tsf_raw', '1'),
                           ('sampling_interval', [1, 2]), ('external_uncertainty_ns', 0)]:
            data = envelope()
            data['bundle']['observations'][2][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'invalid_evidence_bundle'):
                validate_observation(data)

    def test_existing_negative_contract_cases_remain_rejected(self):
        cases = json.loads(FIXTURE.with_name('clock-evidence-v1-rejections.json').read_text())
        for case in cases:
            data = envelope()
            target = data['bundle']
            for key in case['path'][:-1]:
                target = target[key]
            target[case['path'][-1]] = copy.deepcopy(case['value'])
            with self.subTest(case=case['name']), self.assertRaises(ValueError):
                validate_observation(data)


if __name__ == '__main__':
    unittest.main()

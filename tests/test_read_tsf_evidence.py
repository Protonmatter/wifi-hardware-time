"""Bounded saved-file TSF retrieval, strict JSON and CLI failure behavior."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.tsf.read_tsf_evidence import load_observations

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/synthetic/clock-evidence-v1.json'
CLI = ROOT / 'research/tsf/read_tsf_evidence.py'


class ReadTsfTests(unittest.TestCase):
    def test_returns_all_owned_diagnostic_observations(self):
        result = load_observations(FIXTURE)
        self.assertEqual([r['tsf_raw'] for r in result], ['1000000', '2000000', '3000000'])
        self.assertTrue(all(not r['clock_input_eligible'] for r in result))
        result[0]['provenance']['source']['base_revision'] = 'changed'
        self.assertNotEqual(result[1]['provenance']['source']['base_revision'], 'changed')

    def test_rejects_duplicate_keys_nan_truncation_and_oversize(self):
        for data in [b'{"a":1,"a":2}', b'{"a":NaN}', b'{', b' ' * (1048576 + 1), b'\xff']:
            with self.subTest(length=len(data)), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'bad.json'
                path.write_bytes(data)
                with self.assertRaises(ValueError):
                    load_observations(path)

    def test_cli_success_and_qualified_clock_rejection(self):
        for extra, expected in [([], 0), (['--require-clock-input'], 1), (['--sequence', '99'], 1)]:
            result = subprocess.run([sys.executable, str(CLI), str(FIXTURE), *extra],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, expected, result.stderr)
            parsed = json.loads(result.stdout)
            if expected == 0:
                self.assertEqual(parsed['observations'][0]['tsf_raw'], '1000000')
                self.assertEqual(parsed['status'], 'diagnostic-only')
            else:
                self.assertEqual(parsed['status'], 'rejected')
                self.assertNotIn('observations', parsed)

    def test_missing_input_is_structured_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(CLI), str(Path(folder) / 'absent.json')],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['reason'], 'input_unavailable')
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()

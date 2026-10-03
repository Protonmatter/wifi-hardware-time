"""Relocation contracts: no hardware access and no use of stale launch manifests."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LayoutTests(unittest.TestCase):
    def test_ignore_rules_include_authored_evidence_but_exclude_captures(self):
        # Exercise Git's rules in an isolated repository, not a hand-written parser.
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            subprocess.run(['git', 'init', '--quiet', str(folder)], check=True,
                           capture_output=True, timeout=20)
            (folder / '.gitignore').write_bytes((ROOT / '.gitignore').read_bytes())
            authored = {'docs/evidence/README.md',
                        'docs/evidence/diagrams/adoption-timestamp-path.mmd',
                        'research/evidence/export_clock_evidence.py',
                        'research/evidence/validate_research_bundle.py'}
            private = {'evidence/session.json', 'local/evidence/session.json',
                       'research/acquisition/evidence/session.json',
                       'artifacts/capture.json', 'vendor/driver.sys'}
            result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin', '-z'],
                                    cwd=folder, input='\0'.join(sorted(authored | private))+'\0',
                                    text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(set(result.stdout.rstrip('\0').split('\0')), private)

    def test_observer_changed_only_its_decoder_include(self):
        raw = (ROOT / 'research/acquisition/live_observer.c').read_bytes()
        self.assertEqual(raw.count(b'../tsf/decode_tsf_etl.c'), 1)
        original = raw.replace(b'../tsf/decode_tsf_etl.c', b'../../tools/decode_tsf_etl.c')
        self.assertEqual(hashlib.sha256(original).hexdigest(),
                         'cf405a1eddf2e08436a636e42d888e29537cebcf03b32718815e8ef832d2ef0b')

    def test_source_pins_resolve_and_old_path_set_is_not_current(self):
        from research.acquisition.run_passive_observation import PINNED_PATHS
        from research.acquisition.run_scan_comparison import PINNED_PATHS as SCAN_PINS
        for path in set(PINNED_PATHS) | set(SCAN_PINS):
            if path.startswith('artifacts/'):
                continue  # Proprietary/local native outputs are absent in CI.
            self.assertTrue((ROOT / path).is_file(), path)
            self.assertTrue(path.startswith('research/'), path)
        self.assertNotIn('experiments/qualcomm/run_passive_observation.py', PINNED_PATHS)

    def test_direct_cli_help_from_an_unrelated_directory(self):
        # --help exits before interface discovery, trace creation or private access.
        paths = ('research/tsf/qualcomm_probe.py',
                 'research/windows_timestamps/ndis_evidence.py',
                 'research/acquisition/run_scan_comparison.py',
                 'research/memory_ring/inspect_timing_boundaries.py',
                 'research/evidence/export_clock_evidence.py')
        with tempfile.TemporaryDirectory() as directory:
            for path in paths:
                with self.subTest(path=path):
                    result = subprocess.run([sys.executable, str(ROOT / path), '--help'],
                                            cwd=directory, capture_output=True, text=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()

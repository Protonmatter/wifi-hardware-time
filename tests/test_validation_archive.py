import hashlib
import json
from pathlib import Path
import unittest


class ArchiveTests(unittest.TestCase):
    def test_passive_acquisition_wrapper_matches_recorded_hash(self):
        root=Path(__file__).resolve().parents[1]/'docs/reproductions/2026-10-03-passive-launch'
        manifest=json.loads((root/'manifest.json').read_text())
        self.assertEqual(manifest['sha256'],'5875b8782861b166373d5f317e86e4c962d206c04be5fc1ff9e8144be1251c48')
        self.assertEqual(manifest['archive'],'Invoke-PassiveObservation.ps1.txt')
        self.assertEqual(hashlib.sha256((root/manifest['archive']).read_bytes()).hexdigest(),manifest['sha256'])

    def test_archive_hashes_and_nonentrypoint_containment(self):
        root=Path(__file__).resolve().parents[1]/'docs/reproductions/2026-10-03'
        manifest=json.loads((root/'manifest.json').read_text())
        self.assertEqual(manifest['schema'],'validation-source-archive/v1')
        self.assertEqual(len(manifest['entries']),36)
        self.assertEqual(len(manifest['excluded']),1)
        seen=set()
        for item in manifest['entries']:
            path=(root/item['archive']).resolve()
            self.assertTrue(path.is_relative_to(root.resolve()))
            self.assertTrue(path.name.endswith('.txt'))
            self.assertNotIn(path,seen);seen.add(path)
            raw=path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),item['archived_sha256'])
            self.assertNotIn(b'\r\n',raw)
            self.assertNotIn(b'C:\\Users\\',raw)
        self.assertEqual(seen,{p.resolve() for p in root.rglob('*.txt')})

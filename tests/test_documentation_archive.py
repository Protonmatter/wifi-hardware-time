"""Public documentation archives preserve committed-source bytes across checkouts."""
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DocumentationArchiveTests(unittest.TestCase):
    def test_public_snapshots_exclude_uncommitted_private_reports_and_match_hashes(self):
        manifests = sorted((ROOT/'archive').glob('*/manifest.json'))
        self.assertTrue(manifests)
        for manifest in manifests:
            data = json.loads(manifest.read_text(encoding='utf-8'))
            with self.subTest(snapshot=manifest.parent.name):
                self.assertEqual(data['source_kind'], 'git-blob')
                self.assertRegex(data['source_revision'], r'^[0-9a-f]{40}$')
            for row in data['files']:
                with self.subTest(snapshot=manifest.parent.name, source=row['source_path']):
                    self.assertEqual(row['source_commit'], data['source_revision'])
                    self.assertIsNone(row.get('local_base_commit'))
                    for field, digest in [('original_path', 'original_sha256'), ('reading_path', 'reading_sha256')]:
                        path = (manifest.parent/row[field]).resolve()
                        self.assertTrue(path.is_relative_to(manifest.parent.resolve()))
                        raw = path.read_bytes()
                        self.assertEqual(hashlib.sha256(raw).hexdigest(), row[digest])
                        if field == 'original_path':
                            self.assertEqual(len(raw), row['original_bytes'])

    def test_originals_are_not_subject_to_git_newline_conversion(self):
        paths = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'archive').glob('*/originals/*'))
        self.assertTrue(paths)
        result = subprocess.run(['git','check-attr','--stdin','text'], input='\n'.join(paths)+'\n',
                                cwd=ROOT, capture_output=True, text=True, timeout=20, check=True)
        self.assertEqual(len(result.stdout.splitlines()), len(paths))
        self.assertTrue(all(line.endswith(': text: unset') for line in result.stdout.splitlines()))


if __name__ == '__main__':
    unittest.main()

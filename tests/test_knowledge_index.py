import json
from pathlib import Path
import tempfile
import unittest
import os
import subprocess
import shutil
from research.evidence.build_knowledge_index import build, rendered_files


class KnowledgeIndexTests(unittest.TestCase):
    def test_file_order_uses_portable_ordinal_paths(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'research').mkdir()
            for file in ('a.py','B.py'):
                (root/'research'/file).write_text('pass\n')
            self.assertEqual([x['path'] for x in build(root)['files']],
                             ['research/B.py','research/a.py'])

    def test_authored_calls_are_indexed_but_private_artifacts_are_excluded(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for path, text in {'research/example.py': 'def read():\n    return api.get_value("TSF")\n',
                               'research/profile.wprp': '<WindowsPerformanceRecorder Version="1.0" />\n',
                               'research/artifacts/private.wprp': '<PrivateCapture />\n',
                               'research/artifacts/private.py': 'secret_call()\n',
                               'research/topic/evidence/private.py': 'private_evidence()\n',
                               'research/upper/Artifacts/private_upper.py': 'private_upper_artifact()\n',
                               'research/topic_upper/Evidence/private_upper.py': 'private_upper_evidence()\n',
                               'research/evidence/allowed.py': 'authored_evidence()\n',
                               'docs/reproductions/old.md': '`obsolete_token`\n',
                               'docs/guide.md': '# Guide\n\nUse `clock_id`.\n'}.items():
                p = root/path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
            result = build(root)
            indexed_paths = {x['path'] for x in result['files']}
            self.assertIn('research/profile.wprp', indexed_paths)
            self.assertNotIn('research/artifacts/private.wprp', indexed_paths)
            terms = {x['term'] for x in result['terms']}
            self.assertTrue({'read', 'api.get_value', 'TSF', 'clock_id'} <= terms)
            self.assertFalse({'secret_call', 'obsolete_token'} & terms)
            self.assertNotIn('private_evidence', terms)
            self.assertNotIn('private_upper_artifact', terms)
            self.assertNotIn('private_upper_evidence', terms)
            self.assertIn('authored_evidence', terms)
            self.assertEqual(result, build(root))

    def test_generated_files_do_not_enter_their_own_index(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root/'README.md').write_text('# Research\n\n`clock_id`\n')
            initial = build(root)
            for rel, text in rendered_files(initial).items():
                p = root/rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text)
            self.assertEqual(initial, build(root))

    @unittest.skipUnless(os.name == 'nt' and shutil.which('pwsh'), 'Windows and PowerShell 7 required')
    def test_external_junction_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)/'repo'; outside=Path(name)/'outside'
            (root/'research').mkdir(parents=True);outside.mkdir()
            (outside/'private.py').write_text('private_call()')
            link=root/'research'/'external'
            command="$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:WHT_LINK -Target $env:WHT_TARGET | Out-Null"
            subprocess.run([shutil.which('pwsh'),'-NoProfile','-Command',command],env={**os.environ,'WHT_LINK':str(link),'WHT_TARGET':str(outside)},check=True,capture_output=True)
            try:
                with self.assertRaisesRegex(ValueError, 'links'):
                    build(root)
            finally:
                os.rmdir(link)


if __name__ == '__main__':
    unittest.main()

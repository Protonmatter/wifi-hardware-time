"""Publication summaries must be reproducible from one versioned evidence source."""
import importlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HeadlineTests(unittest.TestCase):
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('research.evidence.sync_tsf_headlines'),
                             'Versioned headline synchronizer is required')
        return importlib.import_module('research.evidence.sync_tsf_headlines')

    def fixture(self, folder, api):
        source = json.loads((ROOT / 'docs/overview/pr-reconciliation-2026-10-08.json').read_text(encoding='utf-8'))
        path = folder / api.SOURCE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(source), encoding='utf-8')
        for name, sections in api.TARGETS.items():
            target = folder / name
            target.parent.mkdir(parents=True, exist_ok=True)
            body = '# Existing authored page\n\n'
            for key in sections:
                body += f'<!-- tsf-headlines:{key} -->\nSTALE\n<!-- /tsf-headlines:{key} -->\n'
            target.write_text(body + '\nKeep this original paragraph.\n', encoding='utf-8')
        return source, path

    def test_preview_is_read_only_and_write_is_idempotent(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            _, source = self.fixture(folder, api)
            before = {p: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            planned = api.synchronize(folder, write=False)
            self.assertEqual(set(planned), set(api.TARGETS))
            self.assertTrue(all(p.read_bytes() == data for p, data in before.items()))
            self.assertEqual(api.synchronize(folder, write=True), planned)
            self.assertEqual(api.synchronize(folder, write=False), [])
            self.assertEqual(api.synchronize(folder, write=True), [])
            self.assertEqual(source.read_bytes(), before[source])
            text = (folder / 'README.md').read_text(encoding='utf-8')
            self.assertIn('92.862589%', text)
            self.assertIn('297/297', text)
            self.assertIn('conditional', text)
            self.assertIn('Keep this original paragraph.', text)

    def test_invalid_source_or_markers_leave_every_page_unchanged(self):
        api = self.api()
        for case in ('schema', 'missing', 'nan', 'physical', 'duplicate-marker'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                folder = Path(d)
                source, path = self.fixture(folder, api)
                if case == 'schema': source['schema'] = 'unrecognized/v2'
                if case == 'missing': del source['runs']['persistent_smoke']['corrected']['tracking_percent_exact']
                if case == 'nan': source['runs']['persistent_smoke']['corrected']['settlement']['wait_s']['median'] = float('nan')
                if case == 'physical': source['physical_bound_proven'] = True
                path.write_text(json.dumps(source), encoding='utf-8')
                if case == 'duplicate-marker':
                    target = folder / 'README.md'
                    text = target.read_text(encoding='utf-8')
                    target.write_text(text + text, encoding='utf-8')
                before = {p: p.read_bytes() for p in folder.rglob('*') if p.is_file()}
                with self.assertRaises(ValueError):
                    api.synchronize(folder, write=True)
                self.assertTrue(all(p.read_bytes() == data for p, data in before.items()))

    def test_hour_numbers_and_source_links_come_from_corrected_results(self):
        api = self.api()
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            self.fixture(folder, api)
            api.synchronize(folder, write=True)
            text = (folder / 'docs/knowledge/current-findings.md').read_text(encoding='utf-8')
            self.assertIn('78.632051%', text)
            self.assertIn('72.349583%', text)
            self.assertIn('../overview/postmerge-corrections-2026-10-08.json', text)


if __name__ == '__main__':
    unittest.main()

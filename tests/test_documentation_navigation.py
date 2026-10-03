"""Offline navigation and diagram-source checks for the reorganized library."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def documents():
    return [ROOT / 'README.md', *sorted((ROOT / 'docs').rglob('*.md')),
            *sorted((ROOT / 'research').rglob('*.md'))]


class DocumentationTests(unittest.TestCase):
    def test_sequence_message_text_has_no_unescaped_statement_separators(self):
        # Mermaid uses a bare semicolon as a statement separator even in notes.
        # Entity codes such as #59; are valid literal text, not separators.
        for path in documents():
            text = path.read_text(encoding='utf-8-sig')
            for block in re.findall(r'```mermaid\n(.*?)\n```', text, re.S):
                if not block.lstrip().startswith('sequenceDiagram'):
                    continue
                for line in block.splitlines():
                    if ':' not in line or line.lstrip().startswith('%%'):
                        continue
                    message = re.sub(r'#[A-Za-z0-9]+;', '', line.split(':', 1)[1])
                    with self.subTest(document=str(path.relative_to(ROOT)), line=line):
                        self.assertNotIn(';', message,
                                         'Use a period, <br/>, or escaped #59; in sequence text')

    def test_relative_file_links_resolve(self):
        for path in documents():
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
                if '://' in target or target.startswith(('#', 'mailto:')):
                    continue
                file = target.split('#', 1)[0]
                with self.subTest(document=str(path.relative_to(ROOT)), target=target):
                    self.assertTrue((path.parent / file).exists())

    def test_canonical_diagrams_match_overview_embeds(self):
        overview = (ROOT / 'docs/clock-models/packet-to-clock-map.md').read_text(encoding='utf-8')
        blocks = re.findall(r'```mermaid\n(.*?)\n```', overview, re.S)
        sources = ('clock-models/diagrams/packets-timestamp-path.mmd',
                   'tsf/diagrams/qualcomm-timestamp-path.mmd',
                   'ftm/diagrams/ftm-timestamp-path.mmd',
                   'clock-models/diagrams/uncertainty-timestamp-path.mmd',
                   'evidence/diagrams/adoption-timestamp-path.mmd')
        self.assertEqual(len(blocks), len(sources))
        for block, name in zip(blocks, sources):
            with self.subTest(source=name):
                self.assertEqual(block.strip(), (ROOT / 'docs' / name).read_text(encoding='utf-8').strip())

    def test_documents_have_opening_synopsis_and_balanced_fences(self):
        for path in documents():
            text = path.read_text(encoding='utf-8-sig')
            with self.subTest(document=str(path.relative_to(ROOT))):
                self.assertTrue(text.startswith('# '))
                paragraphs = text.split('\n\n')
                self.assertGreater(len(paragraphs), 1)
                self.assertFalse(paragraphs[1].startswith(('#', '```', '|', '- ')))
                self.assertTrue(paragraphs[1].strip())
                self.assertEqual(text.count('```') % 2, 0)


if __name__ == '__main__':
    unittest.main()

"""Published Archify views must be visible without executing HTML or JSON."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'docs/overview/archify-tsf'


class ArchifyPreviewTests(unittest.TestCase):
    def test_static_export_has_no_dead_keyboard_controls(self):
        from research.evidence.publish_archify_previews import portable_svg
        svg = ET.fromstring(portable_svg('<svg viewBox="0 0 400 200" role="img">'
            '<g role="button" tabindex="0" aria-pressed="false" aria-label="Focus node">'
            '<text>Readable label</text></g></svg>', 'a'*64))
        group = svg.find('{http://www.w3.org/2000/svg}g')
        self.assertNotIn('tabindex', group.attrib)
        self.assertNotIn('role', group.attrib)
        self.assertNotIn('aria-pressed', group.attrib)
        self.assertNotIn('aria-label', group.attrib)
        self.assertEqual(svg.attrib['role'], 'img')
        self.assertIn('Readable label', ''.join(svg.itertext()))

    def test_failed_artifact_check_preserves_published_files(self):
        from research.evidence import publish_archify_previews as publisher
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root/'docs/overview/archify-tsf'
            (folder/'previews').mkdir(parents=True)
            cli = root/'tool/archify/bin/archify.mjs'
            cli.parent.mkdir(parents=True)
            cli.write_text('// test CLI boundary')
            spec = folder/'layers.json'
            spec.write_bytes(b'{}')
            manifest = folder/'manifest.json'
            manifest.write_text(json.dumps({'archify_revision':'b'*40,'diagrams':[{
                'slug':'layers','type':'architecture',
                'specification_sha256':hashlib.sha256(b'{}').hexdigest()}]}))
            preview = folder/'previews/layers.svg'
            preview.write_bytes(b'previous published image')
            before = (manifest.read_bytes(), preview.read_bytes())
            def run(command, **kwargs):
                if 'render' in command:
                    Path(command[5]).write_text('<svg viewBox="0 0 400 200"><text>Test</text></svg>')
                if 'check' in command:
                    raise subprocess.CalledProcessError(1, command)
                return subprocess.CompletedProcess(command, 0)
            with patch.object(publisher,'ROOT',root), patch.object(publisher,'FOLDER',folder), \
                 patch('sys.argv',['publisher','--write','--archify-cli',str(cli)]), \
                 patch.object(publisher.subprocess,'check_output',return_value='b'*40), \
                 patch.object(publisher.subprocess,'run',side_effect=run), \
                 patch('sys.stdout',new_callable=io.StringIO):
                result = publisher.main()
            self.assertEqual(result, 1)
            self.assertEqual((manifest.read_bytes(), preview.read_bytes()), before)

    def test_export_materializes_theme_and_keeps_labels_without_runtime(self):
        from research.evidence.publish_archify_previews import portable_svg
        source = '''<style>:root,[data-theme="dark"] {--text:white; --arrow:gray;}
        [data-theme="light"] {--text:#111827; --arrow:#334155;}
        .t-primary {fill:var(--text);} .a-default {stroke:var(--arrow);fill:none;}
        </style><svg viewBox="0 0 400 200"><title>Test</title>
        <path class="a-default" d="M 10 10 L 100 100"/>
        <text class="t-primary" x="20" y="40">Visible label</text></svg>'''
        data = portable_svg(source, 'a' * 64)
        svg = ET.fromstring(data)
        self.assertEqual(svg.attrib['width'], '400')
        self.assertEqual(svg.find('.//{http://www.w3.org/2000/svg}text').attrib['fill'], '#111827')
        self.assertEqual(svg.find('.//{http://www.w3.org/2000/svg}path').attrib['stroke'], '#334155')
        self.assertNotIn(b'var(', data)
        self.assertNotIn(b'<script', data)
        self.assertIn(b'Visible label', data)

    def test_export_rejects_unresolved_paint_and_external_resources(self):
        from research.evidence.publish_archify_previews import portable_svg
        for content in ('<path stroke="var(--missing)"/>',
                        '<image href="https://example.test/image.png"/>',
                        '<script>bad()</script>'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                portable_svg('<style>[data-theme="light"] {--text:black;}</style>'
                             '<svg viewBox="0 0 400 200">'+content+'</svg>', 'a'*64)

    def test_every_spec_has_a_self_contained_rendered_preview_and_embed(self):
        manifest = json.loads((FOLDER / 'manifest.json').read_text(encoding='utf-8'))
        page = (FOLDER / 'README.md').read_text(encoding='utf-8')
        for diagram in manifest['diagrams']:
            with self.subTest(diagram=diagram['slug']):
                path = FOLDER / 'previews' / (diagram['slug'] + '.svg')
                self.assertTrue(path.is_file(), 'Missing rendered preview; JSON is not a view')
                raw = path.read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), diagram['preview_sha256'])
                specification = (FOLDER / (diagram['slug'] + '.json')).read_bytes()
                self.assertEqual(hashlib.sha256(specification).hexdigest(), diagram['specification_sha256'])
                self.assertIn(diagram['specification_sha256'], raw.decode('utf-8'))
                svg = ET.fromstring(raw)
                self.assertEqual(svg.tag, '{http://www.w3.org/2000/svg}svg')
                self.assertGreater(float(svg.attrib['width']), 0)
                self.assertGreater(float(svg.attrib['height']), 0)
                self.assertIn('![' + diagram['title'] + '](previews/' + diagram['slug'] + '.svg)', page)
                for card in json.loads(specification).get('cards', []):
                    for explanation in card['items']:
                        self.assertIn(explanation, page)
                self.assertGreater(len(svg.findall('.//{http://www.w3.org/2000/svg}text')), 5)
                for element in svg.iter():
                    self.assertNotIn(element.tag.rsplit('}', 1)[-1], ('script', 'foreignObject', 'iframe', 'animate'))
                    for name, value in element.attrib.items():
                        self.assertFalse(name.lower().startswith('on'))
                        self.assertNotIn(name, ('tabindex', 'aria-pressed', 'aria-expanded', 'aria-controls'))
                        self.assertFalse(name == 'role' and value == 'button')
                        self.assertNotIn('var(', value)
                        if name.rsplit('}', 1)[-1] in ('href', 'src'):
                            self.assertTrue(value.startswith('#'))
                self.assertNotRegex(raw.decode('utf-8'), r'url\(["\s]*(?:https?:|file:|//)')


if __name__ == '__main__':
    unittest.main()

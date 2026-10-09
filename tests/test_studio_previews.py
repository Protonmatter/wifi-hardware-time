"""Static Studio exports retain evidence while removing inactive controls."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'docs/overview/archify-studio'


class StudioPreviewTests(unittest.TestCase):
    def test_packaging_overlay_is_idempotent_and_rejects_partial_patches(self):
        from research.evidence.apply_studio_export_policy import patched, ANCHOR, CALL
        policy = (FOLDER/'static-export-policy.js').read_text(encoding='utf-8')
        original = 'function exportSVG(){\n  const clone = source;\n' + ANCHOR + '\n}\n'
        applied = patched(original, policy)
        self.assertEqual(patched(applied, policy), applied)
        self.assertIn(CALL + ANCHOR, applied)
        for malformed in (applied.replace(CALL, ''), applied + CALL, original + original, 'unrecognized exporter'):
            with self.subTest(source=malformed[:50]), self.assertRaises(ValueError):
                patched(malformed, policy)

    def test_all_published_previews_are_static_images_with_complete_topology(self):
        manifest = json.loads((FOLDER/'manifest.json').read_text(encoding='utf-8'))
        routes = {r['id']: r for r in manifest['routes']}
        self.assertEqual(len(routes), 10)
        for item in manifest['previews']:
            with self.subTest(path=item['path']):
                raw = (FOLDER/item['path']).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), item['sha256'])
                root = ET.fromstring(raw)
                self.assertEqual(root.get('role'), 'img')
                self.assertNotIn('interactive', root.get('aria-label', '').lower())
                self.assertTrue(root.find('{http://www.w3.org/2000/svg}desc').text)
                route = routes[Path(item['path']).stem]
                self.assertEqual(sum('data-node' in e.attrib for e in root.iter()), route['nodes'])
                self.assertEqual(sum('data-edge' in e.attrib for e in root.iter()), route['edges'])
                self.assertIn(b'MIT License', raw)
                graph_rules = re.findall(r'[^{}]*\.graph-(?:node|edge)[^{]*\{[^{}]*\}', raw.decode('utf-8'))
                self.assertFalse(any(re.search(r':hover|:focus|\bcursor\s*:', rule) for rule in graph_rules))
                for element in root.iter():
                    self.assertNotEqual(element.get('role'), 'button')
                    for attr in ('tabindex', 'focusable', 'aria-pressed', 'aria-expanded', 'aria-controls'):
                        self.assertNotIn(attr, element.attrib)
                    if 'data-node' in element.attrib or 'data-edge' in element.attrib:
                        self.assertNotIn('aria-label', element.attrib)

    def test_html_and_policy_provenance_match_manifest(self):
        manifest = json.loads((FOLDER/'manifest.json').read_text(encoding='utf-8'))
        raw = (FOLDER/'index.html').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest['html']['sha256'])
        self.assertEqual(len(raw), manifest['html']['bytes'])
        policy = (FOLDER/'static-export-policy.js').read_bytes()
        self.assertEqual(hashlib.sha256(policy).hexdigest(), manifest['static_export_policy']['sha256'])
        self.assertIn(policy.decode('utf-8').strip(), raw.decode('utf-8'))
        self.assertIn('sanitizeStaticSvg(clone,r.title);', raw.decode('utf-8'))

    @unittest.skipUnless(shutil.which('node'), 'Node.js is required for the export-policy behavior check')
    def test_export_policy_strips_controls_even_without_selection_attributes(self):
        policy = FOLDER/'static-export-policy.js'
        program = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(process.argv[1],'utf8');
const context={};vm.createContext(context);vm.runInContext(source,context);
class Element {
  constructor(attrs){this.attrs={...attrs};this.textContent='Visible evidence';}
  setAttribute(k,v){this.attrs[k]=v;}
  getAttribute(k){return this.attrs[k]??null;}
  removeAttribute(k){delete this.attrs[k];}
}
const node=new Element({role:'button','aria-label':'Inspect node',tabindex:'0','aria-pressed':'false','data-node':'n1'});
const edge=new Element({role:'button','aria-label':'Inspect edge',focusable:'true','aria-expanded':'false','aria-controls':'panel','data-edge':'e1'});
const label=new Element({'aria-label':'Meaningful static note'});
const style=new Element({});style.tagName='style';style.textContent='.graph-node{cursor:pointer;outline:none}\n.graph-node:hover .node-box{stroke:red}\n.graph-edge:is(:hover,:focus-visible) .edge-path{stroke:blue}\n.node-box{fill:white}';
const root=new Element({role:'group','aria-label':'interactive diagram',tabindex:'0'});
root.querySelectorAll=selector=>{assert.equal(selector,'*');return[node,edge,label,style];};
context.sanitizeStaticSvg(root,'Research view');
assert.equal(root.attrs.role,'img');assert.equal(root.attrs['aria-label'],'Research view diagram');
for(const e of [root,node,edge])for(const attr of ['tabindex','focusable','aria-pressed','aria-expanded','aria-controls'])assert.equal(e.attrs[attr],undefined);
for(const e of [node,edge]){assert.equal(e.attrs.role,undefined);assert.equal(e.attrs['aria-label'],undefined);assert.equal(e.textContent,'Visible evidence');}
assert.equal(node.attrs['data-node'],'n1');assert.equal(edge.attrs['data-edge'],'e1');
assert.equal(label.attrs['aria-label'],'Meaningful static note');
assert.equal(style.textContent.trim(),'.node-box{fill:white}');
const before=JSON.stringify([root.attrs,node.attrs,edge.attrs,label.attrs]);
context.sanitizeStaticSvg(root,'Research view');
assert.equal(JSON.stringify([root.attrs,node.attrs,edge.attrs,label.attrs]),before);
'''
        result = subprocess.run([shutil.which('node'), '-e', program, str(policy)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()

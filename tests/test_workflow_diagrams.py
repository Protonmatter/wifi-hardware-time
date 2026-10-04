"""Every authored Mermaid embed must belong to a synchronized canonical source."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from research.evidence.sync_workflow_diagrams import updates

ROOT=Path(__file__).resolve().parents[1]


class WorkflowDiagramTests(unittest.TestCase):
    def test_every_embed_is_manifested_and_synchronized(self):
        manifest=json.loads((ROOT/'docs/knowledge/diagram-manifest.json').read_text())
        declared={(t['file'],t['block']) for d in manifest['diagrams'] for t in d['targets']}
        actual=set()
        for path in (ROOT/'docs').rglob('*.md'):
            for i,_ in enumerate(re.findall(r'```mermaid\n(.*?)\n```',path.read_text(encoding='utf-8'),re.S)):
                actual.add((path.relative_to(ROOT).as_posix(),i))
        self.assertEqual(declared,actual)
        self.assertEqual(updates(ROOT),{})

    def test_invalid_or_duplicate_target_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);(root/'docs/knowledge').mkdir(parents=True)
            (root/'docs/one.mmd').write_text('flowchart LR\n A --> B\n')
            (root/'docs/page.md').write_text('# Test\n\n```mermaid\nflowchart LR\n A --> B\n```\n')
            target={'file':'docs/page.md','block':0}
            manifest={'diagrams':[{'source':'docs/one.mmd','targets':[target,target]}]}
            path=root/'docs/knowledge/diagram-manifest.json';path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'duplicate'):
                updates(root)
            manifest['diagrams'][0]['targets']=[{'file':'../outside.md','block':0}]
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'inside docs'):
                updates(root)


if __name__=='__main__':
    unittest.main()

"""Portable contract fixture tests; no downstream checkout required."""

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import json
import unittest
from research.evidence.validate_research_bundle import validate_bundle

FIXTURES=Path(__file__).resolve().parents[1]/'fixtures/synthetic'


class EvidenceContractTests(unittest.TestCase):
    def test_positive_and_negative_fixtures(self):
        original=json.loads((FIXTURES/'clock-evidence-v1.json').read_text())
        self.assertEqual(validate_bundle(original).observation_count,3)
        for case in json.loads((FIXTURES/'clock-evidence-v1-rejections.json').read_text()):
            data=copy.deepcopy(original);target=data
            for key in case['path'][:-1]:target=target[key]
            target[case['path'][-1]]=case['value']
            with self.subTest(name=case['name']),self.assertRaises(ValueError):validate_bundle(data)


if __name__ == '__main__':unittest.main()

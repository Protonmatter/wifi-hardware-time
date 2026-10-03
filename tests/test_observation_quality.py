
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
import copy
import contextlib
import io
import json
import hashlib
import tempfile
from unittest.mock import patch
from research.clock_models.analyze_observation_quality import evaluate, evaluate_rate_transfer, main


def quality_fixture():
    path=Path(__file__).resolve().parents[1]/'fixtures/synthetic/clock-evidence-v1.json'
    data=json.loads(path.read_text())
    for observation in list(data['observations']):
        extra=copy.deepcopy(observation);extra['sequence']+=3
        for key in ('host_before_qpc','host_completed_qpc','report_qpc'):
            extra[key]=str(int(extra[key])+30000000)
        extra['tsf_raw']=str(int(extra['tsf_raw'])+3000000)
        data['observations'].append(extra)
        data['manifest']['input_sha256'][f"request-{extra['sequence']:03}.json"]='0'*64
    hashes=data['manifest']['input_sha256']
    data['manifest']['bundle_id']=hashlib.sha256((json.dumps(hashes,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
    return data


class QualityTests(unittest.TestCase):
    def test_holdout_predicts_linear_relation_without_accuracy_claim(self):
        result=evaluate([(10**16+i*10000, 10**15+i*1000) for i in range(12)],train_count=6)
        self.assertEqual(result['heldout']['affine_max_abs_raw_ticks'],0)
        self.assertGreater(result['heldout']['last_value_max_abs_raw_ticks'],0)
        self.assertIsNone(result['external_uncertainty_ns'])

    def test_constant_sampling_bias_is_invisible(self):
        points=[(i*10000,i*1000+500000) for i in range(12)]
        result=evaluate(points,train_count=6)
        self.assertEqual(result['heldout']['affine_max_abs_raw_ticks'],0)
        self.assertFalse(result['firmware_sampling_validated'])

    def test_holdout_shift_not_used_for_training(self):
        points=[(i*10000,i*1000+(100 if i>=6 else 0)) for i in range(12)]
        result=evaluate(points,train_count=6)
        self.assertEqual(result['heldout']['affine_max_abs_raw_ticks'],100)

    def test_bad_order_small_sample_and_degenerate_data_rejected(self):
        for points,n in [([(1,1)]*8,4), ([(i,i) for i in range(5)],4), ([(i,10-i) for i in range(8)],4)]:
            with self.assertRaises(ValueError): evaluate(points,train_count=n)

    def test_whole_run_rate_transfer_anchors_only_first_validation_point(self):
        train=[(i*10000,i*1000) for i in range(8)]
        heldout=[(10**12+i*10000, 10**9+i*1001) for i in range(8)]
        result=evaluate_rate_transfer(train,heldout)
        self.assertEqual(result['heldout']['affine_max_abs_raw_ticks'],7)
        self.assertEqual(result['validation_anchor_count'],1)
        self.assertEqual(result['heldout_count'],7)
        self.assertFalse(result['phase_continuity_assumed'])

    def test_cli_rejects_complete_contract_violations(self):
        base=quality_fixture()
        for mutation in ('unknown','float','bool','overflow','loss','qualification','identity','missing'):
            data=copy.deepcopy(base)
            if mutation == 'unknown':data['observations'][0]['hostname']='private'
            if mutation == 'float':data['observations'][0]['report_qpc']=1.9
            if mutation == 'bool':data['observations'][0]['report_qpc']=True
            if mutation == 'overflow':data['observations'][0]['report_qpc']=str(1 << 64)
            if mutation == 'loss':data['manifest']['trace_loss']=True
            if mutation == 'qualification':data['manifest']['qualification']='calibrated'
            if mutation == 'identity':data['manifest']['bundle_id']='0'*64
            if mutation == 'missing':del data['manifest']['association']
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'input.json';path.write_text(json.dumps(data))
                output=io.StringIO()
                with patch('sys.argv',['quality',str(path),'--train-count','3']),contextlib.redirect_stdout(output),contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(),1)
                self.assertEqual(output.getvalue(),'')

    def test_cli_accepts_valid_complete_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input.json';path.write_text(json.dumps(quality_fixture()))
            output=io.StringIO()
            with patch('sys.argv',['quality',str(path),'--train-count','3']),contextlib.redirect_stdout(output):
                self.assertEqual(main(),0)
            self.assertEqual(json.loads(output.getvalue())['heldout_count'],3)

    def test_loader_rejects_unknown_fields_before_any_model(self):
        from research.clock_models.analyze_observation_quality import _load
        fixture=Path(__file__).resolve().parents[1]/'fixtures/synthetic/clock-evidence-v1.json'
        data=json.loads(fixture.read_text());data['observations'][0]['hostname']='private'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'input.json';path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):_load(path)


if __name__ == '__main__': unittest.main()

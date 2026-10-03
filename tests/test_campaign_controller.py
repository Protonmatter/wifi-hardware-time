import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch,Mock
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tools'),str(Path(__file__).resolve().parents[1]/'experiments/qualcomm')]
from campaign_admission import transition
from run_acquisition_campaign import TraceOwner,finalize_run


class ControllerTests(unittest.TestCase):
    def test_abort_discovery_child_cannot_be_permitted_or_submitted(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control.json';path.write_text(json.dumps(dict(state='prepared',pid=123)))
            transition(path,'abort')
            for action in ('ready','permit','submit'):
                with self.assertRaises(ValueError):transition(path,action)
            self.assertEqual(json.loads(path.read_text())['pid'],123)

    def test_abort_submitted_child_preserves_drain_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control.json';path.write_text(json.dumps(dict(state='ready',pid=123)))
            transition(path,'permit');transition(path,'submit');transition(path,'abort')
            data=json.loads(path.read_text());self.assertEqual(data['state'],'submitted')
            self.assertTrue(data['abort_requested']);transition(path,'drained')
            with self.assertRaises(ValueError):transition(path,'permit')

    def test_trace_start_success_or_uncertain_outcome_always_stopped(self):
        for failure in ('write','timeout'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as folder:
                owner=TraceOwner('unique-test-session',Path(folder))
                calls=[]
                def fake(command,timeout=30):
                    calls.append(command)
                    if failure=='timeout' and command[1]=='start':raise TimeoutError('start uncertain')
                    return Mock(stdout='ok',returncode=0)
                with patch('run_acquisition_campaign.run',side_effect=fake):
                    try:
                        with patch('pathlib.Path.write_text',side_effect=OSError('disk')) if failure=='write' else __import__('contextlib').nullcontext():
                            owner.start([])
                    except (OSError,TimeoutError):pass
                    owner.stop()
                self.assertEqual(calls[-1],['logman','stop','unique-test-session','-ets'])

    def test_postcapture_failure_cannot_leave_success(self):
        for stage in ('decoder','parity','export'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'run-result.json';summary={'success':False,'validation':'pending'}
                with self.assertRaises(RuntimeError):
                    finalize_run(path,summary,lambda: (_ for _ in ()).throw(RuntimeError(stage)))
                result=json.loads(path.read_text())
                self.assertFalse(result['success']);self.assertEqual(result['validation'],'failed')


if __name__ == '__main__':unittest.main()

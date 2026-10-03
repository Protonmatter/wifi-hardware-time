"""Offline observer cleanup regressions; no Windows/device calls."""
import io
import json
from pathlib import Path
import queue
import sys
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'experiments/qualcomm'),str(Path(__file__).resolve().parents[1]/'tools')]
from campaign_gate import ReportGate
from run_acquisition_campaign import Observer


def observer(folder):
    item=object.__new__(Observer)
    item.folder=Path(folder);item.queue=queue.Queue();item.records=[];item.association=None
    item.ready=True;item.stopped=None;item.closing=False;item.stop=123
    item.clock=SimpleNamespace(frequency=10_000_000,k=Mock())
    item.clock.k.CloseHandle.return_value=1;item.clock.k.SetEvent.return_value=1
    item.file=(item.folder/'live-observer.jsonl').open('w')
    item.errors=(item.folder/'observer-stderr.txt').open('w')
    item.process=Mock(returncode=0,stdout=io.StringIO())
    item.process.wait.return_value=0;item.process.poll.return_value=0
    item.reader=Mock();item.reader.is_alive.return_value=False
    return item


def stopped():return dict(kind='observer_stopped',process_status=0,close_status=0,failed=False,qpc=200)


class DrainTests(unittest.TestCase):
    def test_failed_stop_signal_still_terminates_and_drains(self):
        with tempfile.TemporaryDirectory() as folder:
            item=observer(folder);gate=ReportGate();gate.quarantine('original-rejection')
            item.clock.k.SetEvent.return_value=0
            item.process.wait.side_effect=[subprocess.TimeoutExpired('observer',8),subprocess.TimeoutExpired('observer',8),0]
            item.queue.put((301,json.dumps(stopped())))
            with self.assertRaisesRegex(RuntimeError,'stop signal failed'):item.close(gate)
            receipt=json.loads((Path(folder)/'observer-cleanup.json').read_text())
            item.process.kill.assert_called_once()
            self.assertEqual(item.process.wait.call_count,3)
            self.assertTrue(receipt['evidence_drained']);self.assertTrue(receipt['forced_termination'])
            self.assertFalse(receipt['observer_clean_stop']);self.assertEqual(gate.reason,'original-rejection')

    def test_nonzero_stop_status_cannot_claim_clean_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            item=observer(folder);gate=ReportGate();gate.quarantine('original-rejection')
            event=stopped();event['process_status']=5
            item.queue.put((301,json.dumps(event)))
            with self.assertRaises(RuntimeError):item.close(gate)
            receipt=json.loads((Path(folder)/'observer-cleanup.json').read_text())
            self.assertFalse(receipt['observer_clean_stop'])

    def test_malformed_stop_cannot_prevent_final_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            item=observer(folder);gate=ReportGate();gate.quarantine('original-rejection')
            item.queue.put((300,json.dumps(dict(kind='observer_stopped'))))
            item.queue.put((301,json.dumps(stopped())))
            with self.assertRaises(ValueError):item.close(gate)
            self.assertTrue(item.file.closed)
            self.assertTrue((Path(folder)/'observer-cleanup.json').exists())
            self.assertEqual(item.stopped,dict(stopped(),received_qpc=301))

    def test_forced_observer_termination_still_writes_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            item=observer(folder);gate=ReportGate();gate.quarantine('original-rejection')
            item.process.wait.side_effect=[subprocess.TimeoutExpired('observer',8),subprocess.TimeoutExpired('observer',8),0]
            with self.assertRaises(RuntimeError):item.close(gate)
            receipt=json.loads((Path(folder)/'observer-cleanup.json').read_text())
            self.assertTrue(receipt['forced_termination']);self.assertFalse(receipt['observer_clean_stop'])
            item.process.kill.assert_called_once();self.assertTrue(item.file.closed)

    def test_existing_quarantine_drains_tail_without_admission(self):
        with tempfile.TemporaryDirectory() as folder:
            item=observer(folder);gate=ReportGate();gate.quarantine('original-rejection')
            for event in (dict(kind='report',raw_timestamp=100,vdev=0,tsf_raw=123),dict(kind='delay',raw_timestamp=101,vdev=0,tsf_delay_raw=2),stopped()):
                item.queue.put((300,json.dumps(event)))
            item.close(gate)
            saved=[json.loads(line) for line in (Path(folder)/'live-observer.jsonl').read_text().splitlines()]
            self.assertEqual([r['kind'] for r in saved],['report','delay','observer_stopped'])
            self.assertEqual(gate.reason,'original-rejection');self.assertFalse(gate.complete);self.assertEqual(gate.records,[])
            receipt=json.loads((Path(folder)/'observer-cleanup.json').read_text())
            self.assertTrue(receipt['evidence_drained']);self.assertTrue(receipt['observer_clean_stop'])
            self.assertTrue(receipt['admission_quarantined'])

    def test_new_rejection_during_close_preserves_remaining_records(self):
        with tempfile.TemporaryDirectory() as folder:
            item=observer(folder);gate=ReportGate()
            item.queue.put((300,json.dumps(dict(kind='report',raw_timestamp=100,vdev=0,tsf_raw=123))))
            item.queue.put((301,json.dumps(stopped())))
            with self.assertRaises(ValueError):item.close(gate)
            self.assertTrue(item.file.closed);self.assertTrue(item.errors.closed)
            self.assertIsNotNone(gate.reason)
            saved=[json.loads(line) for line in (Path(folder)/'live-observer.jsonl').read_text().splitlines()]
            self.assertEqual(saved[-1]['kind'],'observer_stopped')

    def test_malformed_tail_is_preserved_and_cannot_hide_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            item=observer(folder);gate=ReportGate();gate.quarantine('original-rejection')
            item.queue.put((300,'not-json'))
            item.queue.put((301,json.dumps(stopped())))
            with self.assertRaises(ValueError):item.close(gate)
            saved=[json.loads(line) for line in (Path(folder)/'live-observer.jsonl').read_text().splitlines()]
            self.assertEqual(saved[0]['kind'],'invalid_observer_line')
            self.assertEqual(saved[-1]['kind'],'observer_stopped')
            self.assertEqual(gate.reason,'original-rejection')

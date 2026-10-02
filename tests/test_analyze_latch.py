"""Synthetic latch evidence only; never sends requests to a device."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'qualcomm'))
from analyze_latch import EXPECTED_ACTIONS, analyze


class LatchAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name)
        self.events = [dict(kind='header', clock_type=1, perf_frequency_hz=10000000,
                            events_lost=0, buffers_lost=0)]
        soc = 100
        for i, action in enumerate(EXPECTED_ACTIONS):
            qpc = (i+1)*10000000
            request = dict(command='tsf_read_value', firmware_action=action, success=True,
                           handle_closed=True, qpc_frequency_hz=10000000,
                           qpc_request_before=qpc, qpc_request_completed=qpc+50,
                           driver_sha256='synthetic-build', interface_index=7)
            (self.run/f'request-{i+1:03}.json').write_text(json.dumps(request))
            if action==4:soc+=10
            tsf = 1000+i*10
            self.events.extend([
                dict(kind='command', raw_timestamp=qpc+10, vdev=0, action=action),
                dict(kind='report', raw_timestamp=qpc+100, vdev=0, tsf_raw=tsf),
                dict(kind='soc_timer', raw_timestamp=qpc+101, soc_timer_raw=soc),
                dict(kind='delay', raw_timestamp=qpc+102, vdev=0, tsf_delay_raw=(tsf-soc)&0xffffffff),
            ])
        self.events.append(dict(kind='summary', process_status=0, close_status=0))
        (self.run/'session.json').write_text(json.dumps(dict(SampleCount=11,Actions=EXPECTED_ACTIONS)))
        self.save_events()

    def save_events(self) -> None:
        (self.run/'raw-timing.jsonl').write_text('\n'.join(json.dumps(e) for e in self.events))

    def test_refreshed_captures_and_cached_reads(self) -> None:
        result=analyze(self.run)
        self.assertEqual(result['capture_count'],3)
        self.assertTrue(result['all_capture_soc_values_changed'])
        self.assertTrue(result['all_read_soc_values_reused_previous'])
        self.assertFalse(result['simultaneity_validated'])

    def test_trace_loss_rejected(self) -> None:
        self.events[0]['events_lost']=1;self.save_events()
        with self.assertRaises(ValueError):analyze(self.run)

    def test_missing_report_rejected(self) -> None:
        self.events.pop(2);self.save_events()
        with self.assertRaises(ValueError):analyze(self.run)

    def test_empty_capture_not_vacuously_successful(self) -> None:
        (self.run/'session.json').write_text(json.dumps(dict(SampleCount=0,Actions=[])))
        with self.assertRaises(ValueError):analyze(self.run)

    def test_mixed_identity_rejected(self) -> None:
        path=self.run/'request-002.json';request=json.loads(path.read_text())
        request['interface_index']=8;path.write_text(json.dumps(request))
        with self.assertRaises(ValueError):analyze(self.run)


if __name__=='__main__':unittest.main()

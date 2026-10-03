"""Passive-only qualification; synthetic records, no trace or adapter operations."""
from pathlib import Path
import sys
import unittest
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/qualcomm'))
from run_passive_observation import assess, reserve_capture


def controls():
    return [dict(kind='ready',health_schema='controller-query/v1',perf_frequency_hz=10000000),
        dict(kind='health',health_source='controller_query',query_status=0,events_lost=0,log_buffers_lost=0,real_time_buffers_lost=0),
        dict(kind='connection',query_status=0,connected=True,changed=False,association='synthetic'),
        dict(kind='observer_stopped',process_status=0,close_status=0,failed=False)]


def decoded(events=()):
    return [dict(kind='header',clock_type=1,perf_frequency_hz=10000000,events_lost=0,buffers_lost=0),
        *events,dict(kind='summary',process_status=0,close_status=0,matches=len(events))]


class PassiveTests(unittest.TestCase):
    def test_existing_capture_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent=Path(temporary);capture=reserve_capture(parent)
            evidence=capture/'result.json';evidence.write_text('original evidence')
            with self.assertRaises(FileExistsError):reserve_capture(parent)
            self.assertEqual(evidence.read_text(),'original evidence')

    def test_quiet_window_is_not_drain_or_clock_qualification(self):
        result=assess(controls(),decoded(),10000000)
        self.assertEqual(result['timing_records'],0)
        self.assertFalse(result['firmware_drain_proven'])
        self.assertFalse(result['clock_relationship_qualified'])

    def test_unsolicited_group_is_observed_without_association(self):
        events=[dict(kind='report',raw_timestamp=100,vdev=0,tsf_raw=1000),
                dict(kind='soc_timer',raw_timestamp=101,soc_timer_raw=500,g_tsf_raw=0),
                dict(kind='delay',raw_timestamp=102,vdev=0,tsf_delay_raw=500)]
        result=assess(controls()+events,decoded(events),10000000)
        self.assertEqual(result['unmatched_report_groups'],1)
        self.assertFalse(result['request_association_qualified'])

    def test_tail_health_lifecycle_and_connection_failures_reject(self):
        for bad in (dict(kind='lifecycle',invalidates=True),
                    dict(controls()[1],events_lost=1),
                    dict(controls()[2],query_status=5),
                    dict(controls()[2],association='different')):
            with self.subTest(bad=bad),self.assertRaises(ValueError):assess(controls()+[bad],decoded(),10000000)

    def test_missing_health_stop_clock_and_offline_mismatch_reject(self):
        for change in ('health','stop','clock','offline'):
            live=controls();offline=decoded()
            if change=='health':live.pop(1)
            if change=='stop':live.pop()
            if change=='clock':offline[0]['perf_frequency_hz']=1
            if change=='offline':live.append(dict(kind='report',raw_timestamp=100))
            with self.subTest(change=change),self.assertRaises(ValueError):assess(live,offline,10000000)

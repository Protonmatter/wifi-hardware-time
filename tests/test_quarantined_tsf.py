from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments/qualcomm'))
from analyze_quarantined_tsf import summarize_timing


def stream(extra=0):
    body=[dict(kind='command',raw_timestamp=100,vdev=0,action=3)]
    for i in range(1+extra):
        t=101+i*10
        body += [dict(kind='report',raw_timestamp=t,vdev=0,tsf_raw=1000+t),
                 dict(kind='soc_timer',raw_timestamp=t+1,g_tsf_raw=0,soc_timer_raw=500+t),
                 dict(kind='delay',raw_timestamp=t+2,vdev=0,tsf_delay_raw=500)]
    return [dict(kind='header',clock_type=1,perf_frequency_hz=10000000,events_lost=0,buffers_lost=0),*body,
            dict(kind='summary',process_status=0,close_status=0,matches=len(body))]


class TimingTests(unittest.TestCase):
    def test_counter_changes_do_not_establish_freshness(self):
        rows=stream(2)
        rows[6]['soc_timer_raw']=rows[3]['soc_timer_raw']
        result=summarize_timing(rows)
        reports=result['report_diagnostics']
        self.assertIsNone(reports[0]['soc_change_raw'])
        self.assertEqual(reports[1]['soc_change_raw'],0)
        self.assertEqual(reports[2]['soc_change_raw'],20)
        self.assertEqual(reports[2]['report_gap_qpc'],10)
        self.assertFalse(reports[1]['delay_matches_low_word_difference'])
        self.assertFalse(result['fresh_sampling_qualified'])

    def test_counter_decrease_is_signed_not_invented_wrap(self):
        rows=stream(1)
        rows[5]['tsf_raw']=1;rows[6]['soc_timer_raw']=2
        reports=summarize_timing(rows)['report_diagnostics']
        self.assertEqual(reports[1]['tsf_change_raw'],-1100)
        self.assertEqual(reports[1]['soc_change_raw'],-599)
        self.assertFalse(reports[1]['same_counter_tuple_as_previous'])

    def test_identical_values_and_other_vdev_are_distinguished(self):
        rows=stream(2)
        rows[5]['tsf_raw']=rows[2]['tsf_raw'];rows[6]['soc_timer_raw']=rows[3]['soc_timer_raw']
        rows[8]['vdev']=1;rows[10]['vdev']=1
        reports=summarize_timing(rows)['report_diagnostics']
        self.assertTrue(reports[1]['same_counter_tuple_as_previous'])
        self.assertIsNone(reports[2]['soc_change_raw'])
        self.assertIsNone(reports[2]['report_gap_qpc'])

    def test_unmatched_reports_remain_unassigned(self):
        result=summarize_timing(stream(2))
        self.assertEqual(result['command_groups'],1)
        self.assertEqual(result['unmatched_report_groups'],2)
        self.assertFalse(result['request_association_qualified'])
        self.assertFalse(result['firmware_origin_identified'])

    def test_complete_stream_still_does_not_prove_identity(self):
        result=summarize_timing(stream())
        self.assertEqual(result['unmatched_report_groups'],0)
        self.assertFalse(result['request_association_qualified'])

    def test_loss_incomplete_wrong_vdev_and_bad_counts_reject(self):
        for change in ('loss','missing','vdev','count','bool','order'):
            rows=stream()
            if change=='loss':rows[0]['events_lost']=1
            if change=='missing':rows.pop(-2);rows[-1]['matches']-=1
            if change=='vdev':rows[-2]['vdev']=2
            if change=='count':rows[-1]['matches']+=1
            if change=='bool':rows[1]['raw_timestamp']=True
            if change=='order':rows[2]['raw_timestamp']=99
            with self.subTest(change=change),self.assertRaises(ValueError):summarize_timing(rows)

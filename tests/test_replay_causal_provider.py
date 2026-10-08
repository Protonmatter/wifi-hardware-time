import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from research.clock_models.causal_provider import AvailableSample, CausalProvider
from research.clock_models.replay_causal_provider import SCREENING_LABEL, arrival_map, availability, replay, replay_run
from research.clock_models.sample_screen import Request, Sample, Screen

ROOT = Path(__file__).resolve().parents[1]
HZ = 10_000_000


def tsf(qpc):
    return 9_000_000_000 + qpc // 10


class ReplayTests(unittest.TestCase):
    def test_arrival_uses_the_last_required_record_and_request_completion(self):
        live = [dict(kind='command', raw_timestamp=100, received_qpc=5_000),
                dict(kind='report', raw_timestamp=3_000, received_qpc=6_000),
                dict(kind='soc_timer', raw_timestamp=3_001, received_qpc=6_100),
                dict(kind='delay', raw_timestamp=3_002, received_qpc=6_200)]
        delay_seen = arrival_map(live)
        self.assertEqual(delay_seen, {3_000: 6_200})
        item = Sample(1, 9_000_000, 0, 0, 3_000)
        self.assertEqual(availability(item, 'causal-arrival', delay_seen, {1: 4_000}), 6_200)
        self.assertEqual(availability(item, 'causal-arrival', delay_seen, {1: 9_999}), 9_999)
        self.assertEqual(availability(item, 'causal-etw', delay_seen, {1: 9_999}), 3_001)
        with self.assertRaises(ValueError):
            availability(Sample(2, 1, 0, 0, 7_000), 'causal-arrival', delay_seen, {2: 1})

    def test_exact_state_durations_on_a_known_timeline(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 1_004_001)
        second = AvailableSample(2, tsf(301_004_000), 301_000_000, 301_004_000, 301_004_001)  # 30 s gap
        start, end = 0, 400_000_000
        result = replay([('accepted', None, first), ('accepted', None, second)], HZ, start, end)
        probe = CausalProvider(HZ)
        probe.ingest(first)
        stale_one = probe.stale_from_qpc()
        probe.ingest(second)
        stale_two = probe.stale_from_qpc()
        expected_tracking = (stale_one - first.available_qpc) + (stale_two - second.available_qpc)
        durations = result['durations_ticks']
        self.assertEqual(Fraction(durations['acquiring']), first.available_qpc - start)
        self.assertEqual(Fraction(durations['tracking']), expected_tracking)
        self.assertEqual(sum(Fraction(v) for v in durations.values()), end - start)
        self.assertEqual(result['incompatible'], [])
        self.assertEqual(result['label'], SCREENING_LABEL)
        self.assertIn('conditions', result)
        self.assertEqual(Fraction(result['max_uncertainty_before_next_sample_exact']),
                         Fraction(result['max_half_width_before_next_sample_exact']) + Fraction(1, 2))
        self.assertEqual(result['rounding_allowance_us'], '1/2')

    def test_incompatible_sample_is_reported_and_latches(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 1_004_001)
        bad = AvailableSample(2, tsf(21_004_000) + 50_000, 21_000_000, 21_004_000, 21_004_001)
        result = replay([('accepted', None, first), ('accepted', None, bad)], HZ, 0, 40_000_000)
        self.assertEqual([item['sequence'] for item in result['incompatible']], [2])
        self.assertGreater(Fraction(result['durations_ticks']['invalid']), 0)

    def test_rejected_samples_are_checked_but_not_ingested(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 1_004_001)
        stale = AvailableSample(2, first.tsf_us, 21_000_000, 21_004_000, 21_004_001)
        good = AvailableSample(3, tsf(41_004_000), 41_000_000, 41_004_000, 41_004_001)
        result = replay([('accepted', None, first), ('rejected', 'stale_or_inconsistent', stale),
                         ('accepted', None, good)], HZ, 0, 50_000_000)
        self.assertEqual(result['rejected_checked'], [dict(sequence=2, reason='stale_or_inconsistent', compatible=False)])
        self.assertEqual(result['incompatible'], [])
        self.assertEqual(result['samples_ingested'], 2)

    def test_rejected_diagnostic_does_not_split_a_continuous_stale_interval(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 1_004_001)
        rejected = AvailableSample(2, 0, 200_000_000, 200_004_000, 200_004_001)
        baseline = replay([('accepted', None, first)], HZ, 0, 400_000_000)
        diagnostic = replay([('accepted', None, first), ('rejected', 'stale', rejected)], HZ, 0, 400_000_000)
        self.assertEqual(diagnostic['durations_ticks'], baseline['durations_ticks'])
        self.assertEqual(diagnostic['stale_interval_count'], baseline['stale_interval_count'])
        self.assertEqual(diagnostic['longest_stale_s'], baseline['longest_stale_s'])

    def _screened_replay(self, accepted, rejected=(), mode='causal-etw', live=(), receipts=None):
        data = dict(qpc_hz=HZ, records=[], requests=[Request(1, 0, True), Request(2, 20_000_000, True)],
                    identity=dict(folder='synthetic', session='synthetic'))
        screened = Screen(tuple(accepted), tuple((s.sequence, r) for r, s in rejected), 0, 0, 0,
                          Fraction(2), Fraction(0), tuple(rejected))
        if receipts is None:
            receipts = [dict(sequence=1, qpc_request_completed=1), dict(sequence=2, qpc_request_completed=20_000_001)]
        with tempfile.TemporaryDirectory() as directory, \
                patch('research.clock_models.replay_causal_provider.load_run', return_value=data), \
                patch('research.clock_models.replay_causal_provider.screen', return_value=screened), \
                patch('research.clock_models.replay_causal_provider._revision', return_value={}), \
                patch('research.clock_models.replay_causal_provider._lines',
                      side_effect=lambda p: live if p.name == 'live-observer.jsonl' else receipts):
            return replay_run(Path(directory), mode)

    def test_rejected_reports_with_missing_evidence_are_accounted_for(self):
        first = Sample(1, tsf(1_004_000), 0, 1_000_000, 1_004_000)
        second = Sample(2, tsf(21_004_000), 0, 21_000_000, 21_004_000)
        third = Sample(3, tsf(41_004_000), 0, 41_000_000, 41_004_000)
        live = [dict(kind='report', raw_timestamp=first.upper_qpc), dict(kind='delay', received_qpc=1_004_001),
                dict(kind='report', raw_timestamp=third.upper_qpc), dict(kind='delay', received_qpc=41_004_001)]
        for issue in ('missing_delay', 'missing_completion', 'invalid_sample'):
            with self.subTest(issue=issue):
                rejected = second if issue != 'invalid_sample' else Sample(2, second.tsf_us, 0, -1, second.upper_qpc)
                records = list(live)
                if issue != 'missing_delay':
                    records += [dict(kind='report', raw_timestamp=second.upper_qpc),
                                dict(kind='delay', received_qpc=21_004_001)]
                receipts = [dict(sequence=1, qpc_request_completed=1), dict(sequence=3, qpc_request_completed=40_000_001)]
                if issue != 'missing_completion':
                    receipts.append(dict(sequence=2, qpc_request_completed=20_000_001))
                result = self._screened_replay([first, third], [('late_report', rejected)], 'causal-arrival', records, receipts)
                self.assertEqual(result['screen']['rejected_with_reports'], 1)
                self.assertEqual(len(result['rejected_checked']) + len(result['rejected_uncheckable']), 1)
                item = result['rejected_uncheckable'][0]
                self.assertEqual((item['sequence'], item['reason']), (2, 'late_report'))
                self.assertTrue(item['error'])

    def test_zero_or_one_accepted_sample_omits_empty_review_interval(self):
        for accepted in ([], [Sample(1, tsf(1_004_000), 0, 1_000_000, 1_004_000)]):
            with self.subTest(count=len(accepted)):
                result = self._screened_replay(accepted)
                self.assertEqual(result['samples_ingested'], len(accepted))
                self.assertNotIn('review_interval_qpc', result)
                self.assertNotIn('coverage_review_interval', result)
                self.assertEqual(sum(Fraction(v) for v in result['durations_ticks'].values()), 70_000_000)

    def test_cli_handles_zero_and_one_accepted_sample_without_traceback(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_analyze_bound_run import write_run
        for accepted_count in (0, 1):
            with self.subTest(accepted_count=accepted_count), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                write_run(folder, count=1)
                if accepted_count == 0:
                    path = folder / 'raw-timing.jsonl'
                    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
                    path.write_text(''.join(json.dumps(r) + '\n' for r in records
                                            if r['kind'] in ('header', 'command')), encoding='utf-8')
                process = subprocess.run([sys.executable, str(ROOT / 'research/clock_models/replay_causal_provider.py'),
                                          str(folder), '--mode', 'causal-etw'],
                                         cwd=directory, capture_output=True, text=True, timeout=20)
                self.assertEqual(process.returncode, 0, process.stderr)
                result = json.loads(process.stdout)['causal-etw']
                self.assertEqual(result['screen']['accepted'], accepted_count)
                self.assertNotIn('coverage_review_interval', result)

    def test_cli_help_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'research/clock_models/replay_causal_provider.py'), '--help'],
                                    cwd=directory, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
from dataclasses import replace
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from research.clock_models.causal_provider import AvailableSample, CausalProvider
from research.clock_models.replay_causal_provider import SCREENING_LABEL, arrival_map, availability, replay, replay_run
from research.clock_models.sample_screen import ContinuityBreak, Request, Sample, Screen

ROOT = Path(__file__).resolve().parents[1]
HZ = 10_000_000


def tsf(qpc):
    return 9_000_000_000 + qpc // 10


class ReplayTests(unittest.TestCase):
    def test_late_historical_samples_are_skipped_without_changing_past_coverage(self):
        for arrivals, skipped in (((50_000_000, 22_000_000), [1]),
                                  ((2_000_000, 60_000_000, 42_000_000), [2])):
            with self.subTest(arrivals=arrivals):
                samples = [AvailableSample(i + 1, tsf(1_004_000 + i * 20_000_000),
                                           1_000_000 + i * 20_000_000, 1_004_000 + i * 20_000_000, arrival)
                           for i, arrival in enumerate(arrivals)]
                events = [('accepted', None, s) for s in samples]
                retained = [e for e in events if e[2].sequence not in skipped]
                baseline = replay(retained, HZ, 0, 80_000_000, (0, min(arrivals)))
                try:
                    result = replay(events, HZ, 0, 80_000_000, (0, min(arrivals)))
                except ValueError as error:
                    self.fail(f'Late history must be accounted for without aborting replay: {error}')
                self.assertEqual([s['sequence'] for s in result['late_history_skipped']], skipped)
                self.assertEqual(result['samples_ingested'], len(retained))
                self.assertEqual(result['incompatible'], [])
                self.assertEqual(result['durations_ticks'], baseline['durations_ticks'])
                self.assertEqual(result['coverage_review_interval'], baseline['coverage_review_interval'])
                self.assertEqual(sum(Fraction(v) for v in result['durations_ticks'].values()), 80_000_000)
                self.assertEqual(result['arrival_order_policy_version'], 'wht/arrival-order-v2')

    def test_equal_availability_ties_use_capture_order_without_backdating(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 30_000_000)
        second = AvailableSample(2, tsf(21_004_000), 21_000_000, 21_004_000, 30_000_000)
        expected = replay([('accepted', None, first), ('accepted', None, second)], HZ, 0, 40_000_000)
        try:
            result = replay([('accepted', None, second), ('accepted', None, first)], HZ, 0, 40_000_000)
        except ValueError as error:
            self.fail(f'Simultaneous available captures must use deterministic tie order: {error}')
        self.assertEqual(result, expected)
        self.assertEqual(result['samples_ingested'], 2)
        self.assertEqual(Fraction(result['durations_ticks']['acquiring']), 30_000_000)

    def test_cli_completes_reordered_arrivals_with_structured_skip_accounting(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_analyze_bound_run import write_run
        for order, skipped in (((2, 1), [1]), ((1, 3, 2), [2]), ((2, 1, 3), [])):
            with self.subTest(order=order), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                write_run(folder, count=len(order))
                records = [json.loads(line) for line in (folder / 'raw-timing.jsonl').read_text().splitlines()]
                latest = max(r.get('raw_timestamp', 0) for r in records)
                # Last case exercises exact receipt ties in the real CLI.
                arrivals = {seq: latest + (1 if order == (2, 1, 3) else rank + 1) * 10_000_000
                            for rank, seq in enumerate(order)}
                groups = [[r for r in records if r.get('kind') in ('report', 'soc_timer', 'delay')][i:i + 3]
                          for i in range(0, 3 * len(order), 3)]
                live = [dict(r, received_qpc=arrivals[seq]) for seq in order for r in groups[seq - 1]]
                (folder / 'live-observer.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in live))
                process = subprocess.run([sys.executable, '-B', str(ROOT / 'research/clock_models/replay_causal_provider.py'),
                                          directory, '--mode', 'causal-arrival'], cwd=directory,
                                         capture_output=True, text=True, timeout=20)
                self.assertEqual(process.returncode, 0, process.stderr)
                result = json.loads(process.stdout)['causal-arrival']
                self.assertEqual([s['sequence'] for s in result['late_history_skipped']], skipped)
                self.assertEqual(result['screen']['accepted'], len(order))
                self.assertEqual(result['samples_ingested'] + len(result['late_history_skipped']), len(order))
                self.assertEqual(sum(Fraction(v) for v in result['durations_ticks'].values()),
                                 (len(order) - 1) * 200_000_000 + 50_000_000)

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

    def _screened_replay(self, accepted, rejected=(), mode='causal-etw', live=(), receipts=None,
                         continuity_break=None):
        data = dict(qpc_hz=HZ, records=[], requests=[Request(1, 0, True), Request(2, 20_000_000, True)],
                    identity=dict(folder='synthetic', session='synthetic'))
        screened = Screen(tuple(accepted), tuple((s.sequence, r) for r, s in rejected), 0, 0, 0,
                          Fraction(2), Fraction(0), tuple(rejected))
        if continuity_break is not None:
            screened = replace(screened, continuity_closed=True, continuity_breaks=(continuity_break,))
        if receipts is None:
            receipts = [dict(sequence=1, qpc_request_completed=1), dict(sequence=2, qpc_request_completed=20_000_001)]
        with tempfile.TemporaryDirectory() as directory, \
                patch('research.clock_models.replay_causal_provider.load_run', return_value=data), \
                patch('research.clock_models.replay_causal_provider.screen', return_value=screened), \
                patch('research.clock_models.replay_causal_provider._revision', return_value={}), \
                patch('research.clock_models.replay_causal_provider._lines',
                      side_effect=lambda p: live if p.name == 'live-observer.jsonl' else receipts):
            return replay_run(Path(directory), mode)

    def test_continuity_break_invalidates_only_from_its_recorded_availability(self):
        first = Sample(1, tsf(1_004_000), 0, 1_000_000, 1_004_000)
        reset = Sample(2, 100, 0, 21_000_000, 21_004_000)
        later = Sample(3, 19_999_000, 0, 41_000_000, 41_004_000)
        live = []
        for s, at in ((first, 2_000_000), (reset, 30_000_000), (later, 50_000_000)):
            live.extend([dict(kind='report', raw_timestamp=s.upper_qpc), dict(kind='delay', received_qpc=at)])
        receipts = [dict(sequence=s.sequence, qpc_request_completed=s.upper_qpc + 1)
                    for s in (first, reset, later)]
        diagnostic = ContinuityBreak(1, 2, first.tsf_us, reset.tsf_us, reset.lower_qpc)
        result = self._screened_replay([first], [('suspected_tsf_discontinuity', reset),
                                               ('continuity_segment_closed', later)],
                                      'causal-arrival', live, receipts, diagnostic)
        self.assertEqual(Fraction(result['durations_ticks']['invalid']), 40_000_000)
        baseline = replay([('accepted', None, AvailableSample(1, first.tsf_us, first.lower_qpc,
                                                              first.upper_qpc, 2_000_000))], HZ, 0, 30_000_000)
        for state in ('acquiring', 'tracking', 'stale'):
            self.assertEqual(result['durations_ticks'][state], baseline['durations_ticks'][state])
        self.assertFalse(result['whole_recording_continuity_eligible'])
        self.assertTrue(result['screen']['continuity_closed'])
        self.assertEqual(result['screen']['continuity_breaks'][0]['sequence'], 2)
        self.assertEqual(result['continuity_invalidations'][0]['available_qpc'], 30_000_000)

    def test_unknown_break_availability_rejects_replay_instead_of_claiming_tracking(self):
        first = Sample(1, tsf(1_004_000), 0, 1_000_000, 1_004_000)
        reset = Sample(2, 100, 0, 21_000_000, 21_004_000)
        diagnostic = ContinuityBreak(1, 2, first.tsf_us, reset.tsf_us, reset.lower_qpc)
        live = [dict(kind='report', raw_timestamp=first.upper_qpc), dict(kind='delay', received_qpc=2_000_000)]
        with self.assertRaisesRegex(ValueError, 'continuity break availability'):
            self._screened_replay([first], [('suspected_tsf_discontinuity', reset)], 'causal-arrival', live,
                                  continuity_break=diagnostic)

    def test_continuity_diagnostic_waits_for_both_observations(self):
        first = Sample(1, tsf(1_004_000), 0, 1_000_000, 1_004_000)
        reset = Sample(2, 100, 0, 21_000_000, 21_004_000)
        diagnostic = ContinuityBreak(1, 2, first.tsf_us, reset.tsf_us, reset.lower_qpc)
        live = [dict(kind='report', raw_timestamp=first.upper_qpc), dict(kind='delay', received_qpc=40_000_000),
                dict(kind='report', raw_timestamp=reset.upper_qpc), dict(kind='delay', received_qpc=30_000_000)]
        result = self._screened_replay([first], [('suspected_tsf_discontinuity', reset)],
                                      'causal-arrival', live, continuity_break=diagnostic)
        self.assertEqual(Fraction(result['durations_ticks']['acquiring']), 40_000_000)
        self.assertEqual(Fraction(result['durations_ticks']['invalid']), 30_000_000)
        self.assertEqual(result['continuity_diagnostics'][0]['sample_available_qpc'], 30_000_000)
        self.assertEqual(result['continuity_diagnostics'][0]['previous_available_qpc'], 40_000_000)
        self.assertEqual(result['continuity_invalidations'][0]['available_qpc'], 40_000_000)

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

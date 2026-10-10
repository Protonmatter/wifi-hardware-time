import inspect
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import tempfile
import unittest
from unittest.mock import patch
from research.clock_models.causal_provider import PROVIDER_POLICY_VERSION, AvailableSample
from research.clock_models.rate_bound import DEFAULT_JUMP_US
from research.clock_models.replay_causal_provider import V3_MODES, replay, replay_run
from research.clock_models.replay_wander import replay_wander
from research.clock_models.sample_screen import LISTEN_TIMEOUT_S, ContinuityBreak, Request, Sample, Screen
from research.clock_models.settle import SETTLEMENT_POLICY_VERSION_V3
from research.clock_models.wander_provider import WANDER_POLICY_VERSION

HZ = 10_000_000


def tsf(qpc):
    return int(Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000))


def available(count=30, spacing=10_000_000, width=2_540, delay=40_000):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        out.append(AvailableSample(i, tsf(lower + width // 3), lower, lower + width, lower + width + delay))
    return out


def recorded(count=40, spacing=10_000_000, delivery=50_000):
    accepted, live, receipts, requests = [], [], [], []
    for i in range(1, count + 1):
        lower = i * spacing
        upper = lower + 2_540
        accepted.append(Sample(i, tsf(lower + 800), 0, lower, upper))
        live.extend([dict(kind='report', raw_timestamp=upper), dict(kind='delay', received_qpc=upper + delivery)])
        receipts.append(dict(sequence=i, qpc_request_completed=upper + 10))
        requests.append(Request(i, lower, True))
    return accepted, live, receipts, requests


def run_mode(mode, break_last=False, **kwargs):
    accepted, live, receipts, requests = recorded(**kwargs)
    data = dict(qpc_hz=HZ, records=[], requests=requests, identity=dict(folder='synthetic', session='synthetic'))
    rejected, breaks = (), ()
    if break_last:  # the final report goes backwards: screening closes the accepted segment there
        bad = accepted.pop()
        bad = Sample(bad.sequence, 100, 0, bad.lower_qpc, bad.upper_qpc)
        rejected = (('suspected_tsf_discontinuity', bad),)
        breaks = (ContinuityBreak(accepted[-1].sequence, bad.sequence, accepted[-1].tsf_us, bad.tsf_us,
                                  bad.lower_qpc),)
    screened = Screen(tuple(accepted), tuple((s.sequence, r) for r, s in rejected), 0, 0, 0,
                      Fraction(len(accepted)), Fraction(0), rejected, continuity_closed=bool(breaks),
                      continuity_breaks=breaks)
    with tempfile.TemporaryDirectory() as directory, \
            patch('research.clock_models.replay_causal_provider.load_run', return_value=data), \
            patch('research.clock_models.replay_causal_provider.screen', return_value=screened), \
            patch('research.clock_models.replay_causal_provider._revision', return_value={}), \
            patch('research.clock_models.replay_causal_provider._lines',
                  side_effect=lambda p: live if p.name == 'live-observer.jsonl' else receipts):
        return replay_run(Path(directory), mode)


class ReplayV3Tests(unittest.TestCase):
    def test_v3_mode_names(self):
        self.assertEqual(V3_MODES, ('settle-v3', 'causal-v3', 'wander'))

    def test_causal_v3_uses_arrival_availability_and_the_jump_allowance(self):
        v3, v2 = run_mode('causal-v3'), run_mode('causal-arrival')
        self.assertEqual(v3['jump_us'], str(DEFAULT_JUMP_US))
        self.assertEqual(v2['jump_us'], '0')
        self.assertEqual(v3['provider_policy_version'], PROVIDER_POLICY_VERSION)
        self.assertEqual(v3['availability_rule'], v2['availability_rule'])
        self.assertEqual(Fraction(v3['max_half_width_before_next_sample_exact']),
                         Fraction(v2['max_half_width_before_next_sample_exact']) + DEFAULT_JUMP_US)
        self.assertEqual(v3['incompatible'], [])

    def test_settle_v3_reports_its_policy(self):
        result = run_mode('settle-v3')
        self.assertEqual(result['settle']['settlement_policy_version'], SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual(result['settle']['states'], dict(settled=result['settle']['events']))

    def test_wander_mode_reports_holdout(self):
        result = run_mode('wander')['wander']
        self.assertEqual(result['policy_version'], WANDER_POLICY_VERSION)
        self.assertEqual(result['holdout_violations'], 0)
        self.assertLess(result['model_half_width_us']['median'], result['guaranteed_half_width_us']['median'])


class ReplayWanderTests(unittest.TestCase):
    def late_case(self, final_available, end=32 * HZ):
        rate = Fraction(1_000_037, 1_000_000)
        at = lambda q: int(Fraction(9_000_000_000) + Fraction(q, 10) * rate)
        items = [AvailableSample(i, at(i * HZ + 800), i * HZ, i * HZ + 2_540, i * HZ + 2_541) for i in range(1, 31)]
        lower = 31 * HZ
        bad = AvailableSample(31, at(lower + 800) + 700, lower, lower + 2_540, final_available)
        return replay_wander(items + [bad], HZ, HZ, end, wander_ppm=2)

    def test_arrival_between_last_grid_query_and_end_is_checked(self):
        normal = self.late_case(31 * HZ + 2_541)
        late = self.late_case(32 * HZ - 1)
        self.assertEqual(normal['holdout_violations'], 1)
        self.assertEqual(late['holdout_violations'], 1)
        self.assertEqual(late['holdout_checked'], normal['holdout_checked'])
        self.assertEqual(late['after_interval'], [])

    def test_sample_available_at_end_is_not_checked_and_is_listed(self):
        result = self.late_case(32 * HZ)
        self.assertEqual(result['holdout_violations'], 0)
        self.assertEqual(result['holdout_checked'], 25)
        self.assertEqual(result['after_interval'], [dict(sequence=31, available_qpc=32 * HZ, lower_qpc=31 * HZ,
                                                         upper_qpc=31 * HZ + 2_540)])

    def test_grid_results_unchanged_when_no_late_arrivals(self):
        items = available(30)
        end = items[-1].available_qpc + HZ
        result = replay_wander(items, HZ, items[0].lower_qpc, end, wander_ppm=2)
        self.assertEqual(result['after_interval'], [])
        self.assertEqual(result['queries'], 301)
        self.assertEqual(result['guaranteed_states'], dict(acquiring=1, tracking=300))
        self.assertEqual(result['model_states'], dict(acquiring=1, unavailable=40, tracking=260))
        self.assertEqual(result['guaranteed_half_width_us'],
                         dict(median=227.525, p90=307.525, p99=327.525, max=327.525))
        self.assertEqual(result['model_half_width_us'],
                         dict(median=137.317, p90=154.059, p99=180.57, max=193.324))
        self.assertEqual(result['holdout_checked'], 25)
        self.assertEqual(result['holdout_violations'], 0)

    def test_grid_replay_reports_both_layers_and_holdout(self):
        items = available(30)
        result = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc, wander_ppm=2, jump_us=0)
        self.assertEqual(result['holdout_violations'], 0)
        self.assertGreater(result['holdout_checked'], 20)
        self.assertGreater(result['guaranteed_tracking_share'], 0.9)
        self.assertLess(result['model_half_width_us']['median'], result['guaranteed_half_width_us']['median'])
        self.assertEqual(result['queries'], sum(result['guaranteed_states'].values()))
        with self.assertRaises(ValueError):
            replay_wander(items, HZ, 5, 5, wander_ppm=2)

    def test_holdout_violations_surface_in_replay_on_rate_step(self):
        cutover_qpc = 400_000_000
        fast_rate = Fraction(1_000_187, 1_000_000)  # +187 ppm: inside the 200-ppm prior
        def step_tsf(qpc):
            if qpc < cutover_qpc:
                return int(Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000))
            else:
                at_cutover = int(Fraction(9_000_000_000) + Fraction(cutover_qpc, 10) * Fraction(1_000_037, 1_000_000))
                return at_cutover + int(fast_rate * (qpc - cutover_qpc) // 10)
        items = []
        for i in range(60):
            lower = 1_000_000 + i * 10_000_000
            items.append(AvailableSample(i, step_tsf(lower + 2_540 // 3), lower, lower + 2_540, lower + 2_540 + 40_000))
        result = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc, wander_ppm=1, jump_us=0)
        self.assertGreater(result['holdout_violations'], 0, 'Expected violations with wander_ppm=1 on rate step')
        self.assertTrue(len(result['holdout_violation_sequences']) > 0, 'Violations should be non-empty')
        # All violations should come from samples after the cutover
        for seq in result['holdout_violation_sequences']:
            self.assertGreater(seq, cutover_qpc // 10_000_000, 'Violations should be after cutover sample')
        # Guaranteed provider should never go invalid despite rate step
        self.assertEqual(result['guaranteed_states'].get('invalid', 0), 0, 'Guaranteed provider should not invalidate')


class WanderContinuityTests(unittest.TestCase):
    def test_continuity_break_reaches_both_wander_layers_at_the_causal_boundary(self):
        causal, wander = run_mode('causal-v3', break_last=True), run_mode('wander', break_last=True)['wander']
        self.assertIn('invalid', wander['guaranteed_states'])
        self.assertIn('invalid', wander['model_states'])
        known_at = causal['continuity_diagnostics'][0]['available_qpc']
        self.assertEqual(wander['continuity_invalidations'][0]['available_qpc'], known_at)
        start, step = HZ, HZ // 10
        end = 40 * HZ + LISTEN_TIMEOUT_S * HZ
        queries = list(range(start, end, step))
        invalid = [q for q in queries if q >= known_at]
        self.assertEqual(wander['queries'], len(queries))
        self.assertEqual(wander['guaranteed_states']['invalid'], len(invalid))
        self.assertEqual(wander['model_states']['invalid'], len(invalid))
        # The invalid time starts at the same grid boundary as causal-v3's invalid duration.
        self.assertEqual(Fraction(causal['durations_ticks']['invalid']), end - known_at)
        # No width is recorded for post-boundary queries: the sum of non-invalid states bounds them.
        before = len(queries) - len(invalid)
        recorded_states = sum(n for state, n in wander['guaranteed_states'].items() if state != 'invalid')
        self.assertEqual(recorded_states, before)

    def test_no_holdout_checks_after_invalidation(self):
        items = available(30)
        flagged = dict(sequence=10, available_qpc=items[10].available_qpc)
        plain = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc + HZ, wander_ppm=2)
        broken = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc + HZ, wander_ppm=2,
                               continuity=[flagged])
        self.assertLess(broken['holdout_checked'], plain['holdout_checked'])
        self.assertEqual(broken['holdout_checked'], 5)
        self.assertEqual(broken['continuity_invalidations'], [flagged])

    def test_diagnostic_precedes_a_sample_with_equal_availability(self):
        items = available(30)
        tie = dict(sequence=10, available_qpc=items[10].available_qpc)
        result = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc + HZ, wander_ppm=2,
                               continuity=[tie])
        self.assertEqual(result['holdout_checked'], 5)  # samples 0..9 ingested; the model fits from 5 samples

    def test_no_continuity_means_no_invalid_state(self):
        items = available(30)
        result = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc, wander_ppm=2)
        self.assertNotIn('invalid', result['guaranteed_states'])
        self.assertEqual(result['continuity_invalidations'], [])
        self.assertEqual(result['late_history_skipped'], [])


class WanderHistoryTests(unittest.TestCase):
    def delivered(self, late=None, tie=False):
        out = []
        for i in range(1, 10):
            avail = i * HZ + 2_541
            if i == 6 and late:
                avail = 7 * HZ + 2_541 + (0 if tie else 1_000)
            out.append(AvailableSample(i, tsf(i * HZ + 800), i * HZ, i * HZ + 2_540, avail))
        return out

    def test_reversed_delivery_skips_the_historical_sample_with_accounting(self):
        items = self.delivered(late=True)
        result = replay_wander(items, HZ, HZ, 12 * HZ, wander_ppm=2)
        skipped = result['late_history_skipped']
        self.assertEqual([s['sequence'] for s in skipped], [6])
        self.assertEqual(skipped[0]['lower_qpc'], 6 * HZ)
        self.assertEqual(skipped[0]['upper_qpc'], 6 * HZ + 2_540)
        self.assertEqual(skipped[0]['available_qpc'], 7 * HZ + 2_541 + 1_000)
        self.assertEqual(skipped[0]['last_ingested_capture_end_qpc'], 7 * HZ + 2_540)
        full = replay_wander(self.delivered(), HZ, HZ, 12 * HZ, wander_ppm=2)
        self.assertEqual(full['late_history_skipped'], [])
        self.assertEqual(result['holdout_checked'], full['holdout_checked'] - 1)

    def test_equal_availability_ties_keep_capture_order(self):
        result = replay_wander(self.delivered(late=True, tie=True), HZ, HZ, 12 * HZ, wander_ppm=2)
        self.assertEqual(result['late_history_skipped'], [])

    def test_replay_run_wander_carries_accounting(self):
        result = run_mode('wander')['wander']
        self.assertEqual(result['late_history_skipped'], [])
        self.assertEqual(result['continuity_invalidations'], [])


class ReplaySignatureCompatibilityTests(unittest.TestCase):
    def test_historical_positional_call_still_binds_rate_prior_and_threshold(self):
        events = [('accepted', None, s) for s in available(count=10)]
        review = (events[0][2].available_qpc, events[-1][2].available_qpc)
        start, end = 1_000_000, 100_000_000
        positional = replay(events, HZ, start, end, review, 100, 500)
        keyword = replay(events, HZ, start, end, review_interval=review, rate_prior_ppm=100, threshold_us=500)
        self.assertEqual(positional['rate_prior_ppm'], 100)
        self.assertEqual(positional['threshold_us'], 500)
        self.assertEqual(positional, keyword)

    def test_request_interval_is_keyword_only(self):
        params = inspect.signature(replay).parameters
        self.assertIs(params['request_interval'].kind, inspect.Parameter.KEYWORD_ONLY)

    def test_positional_parameter_order_is_stable(self):
        positional = [name for name, p in inspect.signature(replay).parameters.items()
                      if p.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD]
        self.assertEqual(positional, ['events', 'qpc_hz', 'start', 'end', 'review_interval',
                                      'rate_prior_ppm', 'threshold_us', 'jump_us'])


class RequestIntervalCoverageTests(unittest.TestCase):
    def coverage(self, end, request_interval):
        samples = [AvailableSample(i, tsf(i * HZ + 800), i * HZ, i * HZ + 2_540, i * HZ + 2_541) for i in range(1, 11)]
        events = [('accepted', None, s) for s in samples]
        return replay(events, HZ, HZ, end, (samples[0].available_qpc, samples[-1].available_qpc),
                      request_interval=request_interval)

    def test_stale_tail_before_the_last_request_counts_and_later_time_is_excluded(self):
        short = self.coverage(30 * HZ, (HZ, 30 * HZ))
        self.assertEqual(short['request_interval_qpc'], [HZ, 30 * HZ])
        self.assertEqual(short['coverage_review_interval'], 1.0)  # ends at the last accepted sample
        self.assertLess(short['coverage_request_interval'], 0.5)  # the silent tail is stale
        # Time after the last request does not enter the figure.
        self.assertEqual(self.coverage(60 * HZ, (HZ, 30 * HZ))['coverage_request_interval'],
                         short['coverage_request_interval'])
        self.assertNotIn('coverage_request_interval', self.coverage(30 * HZ, None))

    def test_run_replay_reports_request_interval_for_causal_modes(self):
        result = run_mode('causal-v3')
        self.assertEqual(result['request_interval_qpc'], [HZ, 40 * HZ])
        self.assertGreater(result['coverage_request_interval'], 0.95)


class WanderLateDiagnosticTests(unittest.TestCase):
    def test_diagnostic_after_the_replay_end_is_recorded_without_changing_states(self):
        items = available(30)
        end = items[-1].available_qpc
        late = dict(sequence=99, available_qpc=end + HZ)
        base = replay_wander(items, HZ, items[0].lower_qpc, end, wander_ppm=2)
        result = replay_wander(items, HZ, items[0].lower_qpc, end, wander_ppm=2, continuity=[late])
        self.assertEqual(result['continuity_invalidations'], [late])
        self.assertEqual(result['guaranteed_states'], base['guaranteed_states'])
        self.assertEqual(result['model_states'], base['model_states'])


if __name__ == '__main__':
    unittest.main()

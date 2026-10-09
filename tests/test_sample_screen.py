import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.sample_screen import Request, Sample, freshness_filter, request_from_receipt, screen

HZ = 10_000_000
SPACING = 20_000_000  # two seconds


def tsf_at(qpc):
    return 7_000_000_000 + qpc // 10


def group(ts, tsf, vdev=0, soc=1_000_000):
    return [dict(kind='report', raw_timestamp=ts, vdev=vdev, tsf_raw=tsf),
            dict(kind='soc_timer', raw_timestamp=ts + 1, soc_timer_raw=soc, g_tsf_raw=0),
            dict(kind='delay', raw_timestamp=ts + 2, vdev=vdev, tsf_delay_raw=(tsf - soc) & 0xffffffff)]


def ours(lower, report_at=3_000, tsf=None, command=True):
    records = [dict(kind='command', raw_timestamp=lower + 500, vdev=0, action=4)] if command else []
    return records + group(lower + report_at, tsf if tsf is not None else tsf_at(lower + report_at))


def requests(count):
    return [Request(i + 1, 10_000_000 + i * SPACING, True) for i in range(count)]


class ScreenTests(unittest.TestCase):
    def test_fractional_upper_qpc_tick_is_admitted_at_positive_rate_limit(self):
        # Exact +100 ppm truth at U+0.99999 tick floors to TSF 10003.
        capture = Fraction(100_009) + Fraction(99_999, 100_000)
        truth = Fraction(99_999, 100_000) + Fraction(1_000_100, HZ) * capture
        self.assertEqual(int(truth), 10_003)
        samples = [Sample(1, 0, 0, 0, 0), Sample(2, int(truth), 0, 100_009, 100_009)]
        self.assertEqual(freshness_filter(samples, HZ), (samples, []))

    def test_previous_fractional_upper_tick_is_admitted_at_negative_rate_limit(self):
        capture = Fraction(99_999, 100_000)
        previous_truth = Fraction(100_000_001, 100_000)
        current_truth = previous_truth + Fraction(999_900, HZ) * (100_011 - capture)
        samples = [Sample(1, int(previous_truth), 0, 0, 0),
                   Sample(2, int(current_truth), 0, 100_011, 100_011)]
        self.assertEqual(freshness_filter(samples, HZ), (samples, []))

    def test_jittered_capture_edges_preserve_fresh_rate_limit_clocks(self):
        for ppm in (-100, 0, 100):
            for phase in (Fraction(0), Fraction(1, 2), Fraction(99_999, 100_000)):
                for edge in (Fraction(0), Fraction(10), Fraction(1_099_999, 100_000)):
                    samples = [Sample(i, int(10_000 + phase + Fraction(1_000_000 + ppm, HZ) * (lo + edge)),
                                      0, lo, lo + 10) for i, lo in enumerate((100, 100_011, 5_000_003))]
                    with self.subTest(ppm=ppm, phase=phase, edge=edge):
                        self.assertEqual(freshness_filter(samples, HZ), (samples, []))

    def test_noninteger_or_unordered_candidates_fail_closed(self):
        for samples, hz in (([Sample(1, True, 0, 0, 0)], HZ),
                            ([Sample(1, 0, 0, 0, 0)], True),
                            ([Sample(1, 0, 0, 0, 0)], 0),
                            ([Sample(1, 0, 0, 1, 1), Sample(2, 2, 0, 0, 0)], HZ)):
            with self.subTest(samples=samples, hz=hz), self.assertRaises(ValueError):
                freshness_filter(samples, hz)

    def test_backward_observation_latches_even_after_drift_allowance_grows(self):
        samples = [Sample(1, 1_000, 0, 0, 0), Sample(2, 100, 0, 11_000, 11_000),
                   Sample(3, 19_999_000, 0, 200_000_000, 200_000_000)]
        accepted, rejected = freshness_filter(samples, HZ)
        self.assertEqual(accepted, samples[:1])
        self.assertEqual(rejected, [(2, 'suspected_tsf_discontinuity'), (3, 'continuity_segment_closed')])
        # A caller must explicitly supply a new analysis segment to rearm.
        self.assertEqual(freshness_filter(samples[1:], HZ), (samples[1:], []))

    def test_repeated_stale_report_does_not_close_continuity(self):
        samples = [Sample(1, 1_000, 0, 0, 0), Sample(2, 1_000, 0, 11_000, 11_000),
                   Sample(3, 20_001_000, 0, 200_000_000, 200_000_000)]
        self.assertEqual(freshness_filter(samples, HZ),
                         ([samples[0], samples[2]], [(2, 'stale_or_inconsistent')]))

    def test_backward_counter_wrap_is_not_automatically_unwrapped(self):
        samples = [Sample(1, (1 << 64) - 10, 0, 0, 0), Sample(2, 10, 0, 200, 200)]
        self.assertEqual(freshness_filter(samples, HZ)[1], [(2, 'suspected_tsf_discontinuity')])

    def test_screen_preserves_closed_continuity_and_observations(self):
        reqs = requests(4)
        values = [1_000, 100, 4_001_000, 6_001_000]
        records = [r for req, value in zip(reqs, values) for r in ours(req.lower_qpc, tsf=value)]
        result = screen(records, reqs, HZ)
        self.assertEqual([s.sequence for s in result.accepted], [1])
        self.assertTrue(result.continuity_closed)
        self.assertEqual(result.policy_version, 'wht/sample-screen-v2')
        self.assertEqual(len(result.continuity_breaks), 1)
        discontinuity = result.continuity_breaks[0]
        self.assertEqual((discontinuity.previous_sequence, discontinuity.sequence), (1, 2))
        self.assertEqual((discontinuity.previous_tsf_us, discontinuity.tsf_us), (1_000, 100))
        self.assertEqual(discontinuity.reason, 'backward_tsf_observation')
        self.assertEqual([reason for reason, _ in result.rejected_samples],
                         ['suspected_tsf_discontinuity', 'continuity_segment_closed', 'continuity_segment_closed'])

    def test_structurally_rejected_backward_report_does_not_latch(self):
        reqs = requests(3)
        records = [r for req in reqs for r in ours(req.lower_qpc)]
        records += group(reqs[1].lower_qpc + 1_000, 0)
        result = screen(records, reqs, HZ)
        self.assertEqual([s.sequence for s in result.accepted], [1, 3])
        self.assertFalse(result.continuity_closed)

    def test_one_owned_group_per_window_is_accepted(self):
        reqs = requests(3)
        records = [r for q in reqs for r in ours(q.lower_qpc)]
        result = screen(records, reqs, HZ)
        self.assertEqual([s.sequence for s in result.accepted], [1, 2, 3])
        self.assertEqual((result.foreign_groups, result.own_losses), (0, 0))
        self.assertEqual(result.accepted[0].upper_qpc, reqs[0].lower_qpc + 3_000)

    def test_foreign_group_in_gap_is_counted_not_fatal(self):
        reqs = requests(3)
        records = [r for q in reqs for r in ours(q.lower_qpc)]
        records += group(reqs[0].lower_qpc + 10_000_000, tsf_at(reqs[0].lower_qpc + 10_000_000))
        result = screen(records, reqs, HZ)
        self.assertEqual(len(result.accepted), 3)
        self.assertEqual(result.foreign_groups, 1)

    def test_second_report_inside_acceptance_window_rejects_sample(self):
        reqs = requests(2)
        records = [r for q in reqs for r in ours(q.lower_qpc)]
        records += group(reqs[0].lower_qpc + 1_000, tsf_at(reqs[0].lower_qpc + 1_000))
        result = screen(records, reqs, HZ)
        self.assertIn((1, 'multiple_reports_in_window'), result.rejected)
        self.assertEqual(result.foreign_groups, 1)

    def test_collided_groups_contribute_to_misattribution_with_an_own_loss(self):
        reqs = requests(2)
        records = ours(reqs[0].lower_qpc)
        records += group(reqs[0].lower_qpc + 1_000, tsf_at(reqs[0].lower_qpc + 1_000))
        records += [dict(kind='command', raw_timestamp=reqs[1].lower_qpc + 500, vdev=0, action=4)]
        result = screen(records, reqs, HZ)
        self.assertEqual((result.foreign_groups, result.own_losses), (1, 1))
        self.assertEqual(result.expected_misattributed, Fraction(1, 500) / result.duration_s)

    def test_own_loss_late_report_and_misattribution_estimate(self):
        reqs = requests(3)
        records = ours(reqs[0].lower_qpc) + ours(reqs[1].lower_qpc, report_at=5_000_000)
        records += [dict(kind='command', raw_timestamp=reqs[2].lower_qpc + 500, vdev=0, action=4)]
        records += group(reqs[2].lower_qpc + 60_000_000, tsf_at(reqs[2].lower_qpc + 60_000_000))  # after every listen interval
        result = screen(records, reqs, HZ)
        self.assertIn((2, 'late_report'), result.rejected)
        self.assertIn((3, 'own_loss'), result.rejected)
        self.assertEqual(result.own_losses, 2)
        self.assertEqual(result.foreign_groups, 1)
        expected = 2 * Fraction(1) / result.duration_s * Fraction(2_000, 1_000_000)
        self.assertEqual(result.expected_misattributed, expected)

    def test_foreign_substitution_for_a_lost_report_is_only_estimated(self):
        # Known limitation: if our report is lost and a foreign report lands in the acceptance window, the
        # sample is accepted; the misattribution estimate is the only safeguard, so it must count this risk.
        reqs = requests(3)
        records = ours(reqs[0].lower_qpc) + ours(reqs[2].lower_qpc)
        records += [dict(kind='command', raw_timestamp=reqs[1].lower_qpc + 500, vdev=0, action=4)]
        records += group(reqs[1].lower_qpc + 1_500, tsf_at(reqs[1].lower_qpc + 1_500))  # foreign, inside the window
        records += ours(reqs[2].lower_qpc + 30_000_000, command=False)  # a foreign group elsewhere sets the rate
        result = screen(records, reqs, HZ)
        self.assertEqual([s.sequence for s in result.accepted], [1, 2, 3])
        self.assertEqual(result.own_losses, 0)

    def test_rejected_samples_with_reports_are_returned_for_diagnostics(self):
        reqs = requests(3)
        first = ours(reqs[0].lower_qpc)
        late = ours(reqs[1].lower_qpc, report_at=5_000_000)
        stale = ours(reqs[2].lower_qpc, tsf=first[1]['tsf_raw'])
        result = screen(first + late + stale, reqs, HZ)
        kinds = {reason: sample.sequence for reason, sample in result.rejected_samples}
        self.assertEqual(kinds, {'late_report': 2, 'stale_or_inconsistent': 3})
        late_sample = dict((r, s) for r, s in result.rejected_samples)['late_report']
        self.assertEqual(late_sample.upper_qpc, reqs[1].lower_qpc + 5_000_000)

    def test_missing_command_record_rejects_sample(self):
        reqs = requests(1)
        result = screen(ours(reqs[0].lower_qpc, command=False), reqs, HZ)
        self.assertEqual(result.rejected, ((1, 'command_record_missing_or_extra'),))

    def test_stale_repeat_is_rejected_by_freshness(self):
        reqs = requests(2)
        first = ours(reqs[0].lower_qpc)
        stale = ours(reqs[1].lower_qpc, tsf=first[1]['tsf_raw'])
        result = screen(first + stale, reqs, HZ)
        self.assertEqual([s.sequence for s in result.accepted], [1])
        self.assertIn((2, 'stale_or_inconsistent'), result.rejected)

    def test_vdev_mismatch_and_bad_delay_are_rejected(self):
        reqs = requests(2)
        bad_vdev = [dict(kind='command', raw_timestamp=reqs[0].lower_qpc + 500, vdev=1, action=4)]
        bad_vdev += group(reqs[0].lower_qpc + 3_000, tsf_at(reqs[0].lower_qpc + 3_000))
        bad_delay = ours(reqs[1].lower_qpc)
        bad_delay[3]['tsf_delay_raw'] += 1
        result = screen(bad_vdev + bad_delay, reqs, HZ)
        self.assertIn((1, 'vdev_mismatch'), result.rejected)
        self.assertIn((2, 'delay_arithmetic'), result.rejected)

    def test_malformed_group_raises(self):
        reqs = requests(1)
        records = ours(reqs[0].lower_qpc)
        del records[2]
        with self.assertRaises(ValueError):
            screen(records, reqs, HZ)

    def test_receipt_conversion_admits_only_action_four(self):
        receipt = dict(qpc_request_before=5, success=True, handle_closed=True, cancel_requested=False, firmware_action=4)
        self.assertEqual(request_from_receipt(1, receipt), Request(1, 5, True))
        with self.assertRaises(ValueError):
            request_from_receipt(1, dict(receipt, firmware_action=3))

    def test_freshness_filter_on_samples(self):
        good = [Sample(i, tsf_at(i * SPACING + 3_000), 0, i * SPACING, i * SPACING + 3_000) for i in range(3)]
        accepted, rejected = freshness_filter(good, HZ)
        self.assertEqual(len(accepted), 3)
        self.assertEqual(rejected, [])


if __name__ == '__main__':
    unittest.main()

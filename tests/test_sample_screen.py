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

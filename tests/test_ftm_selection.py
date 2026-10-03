"""Synthetic edge cases and sanitized numeric replay from a saved local trace."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'qualcomm'))
from model_ftm_selection import EMPTY, select_postfilter


def slots(*values: int) -> list[int]:
    return list(values) + [EMPTY] * (8 - len(values))


class SelectionTests(unittest.TestCase):
    def test_saved_trace_callback_replay(self) -> None:
        # WifiFtm-83d68ef1a7aa, ordered post-filter log groups / callback records.
        # No endpoint identifiers or raw trace/binary content is included.
        cases = [
            ([4148, 2195, 1609], [2586, 1413], 2, 1999, 2389),
            ([3172, 2194, 1999], [3367, 1219, 1023], 3, 1869, 2162),
            ([18602, 17625, 16454, 15477], [16063, 15673, 15281, 13329], 4, 15086, 16062),
            ([], [0], 0, -1, 0),
        ]
        for left, right, count, rtt, auxiliary in cases:
            with self.subTest(rtt=rtt):
                result = select_postfilter(slots(*left), slots(*right))
                self.assertEqual((result.selected_count, result.selected_rtt_raw,
                                  result.auxiliary_raw), (count, rtt, auxiliary))

    def test_empty_channel_can_win(self) -> None:
        result = select_postfilter(slots(50), slots())
        self.assertEqual((result.selected_channel, result.selected_count,
                          result.selected_rtt_raw), (1, 0, -1))

    def test_tie_selects_channel_zero(self) -> None:
        result = select_postfilter(slots(10, 10), slots(10))
        self.assertEqual((result.selected_channel, result.selected_count), (0, 2))

    def test_negative_mean_truncates_toward_zero(self) -> None:
        result = select_postfilter(slots(-4, -3), slots(20))
        self.assertEqual(result.selected_rtt_raw, -3)

    def test_negative_auxiliary_uses_unsigned_division(self) -> None:
        result = select_postfilter(slots(-4), slots(-2))
        self.assertEqual(result.auxiliary_raw, ((1 << 64) - 6) // 2)

    def test_all_empty_is_separate_branch(self) -> None:
        result = select_postfilter(slots(), slots())
        self.assertIsNone(result.selected_channel)
        self.assertEqual((result.selected_count, result.selected_rtt_raw), (0, 0))

    def test_invalid_inputs(self) -> None:
        for bad in ([], [0]*9, [True]*8, [1.0]*8, [1 << 31]*8, [EMPTY-1]*8):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                select_postfilter(bad, slots())


if __name__ == '__main__':
    unittest.main()

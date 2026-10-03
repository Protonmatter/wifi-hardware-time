"""Adversarial model tests; these never inspect driver memory."""

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest

from research.memory_ring.model_ring_publication import schedules, simulate, assess_model


class PublicationTests(unittest.TestCase):
    def test_all_order_preserving_interleavings(self):
        cases = list(schedules(('reserve', 'prefix', 'payload'), ('copy1', 'copy2')))
        self.assertEqual(len(cases), 10)
        self.assertEqual(len(set(cases)), 10)
        for case in cases:
            self.assertLess(case.index('reserve'), case.index('prefix'))
            self.assertLess(case.index('prefix'), case.index('payload'))
            self.assertLess(case.index('copy1'), case.index('copy2'))

    def test_equal_copies_and_cursor_can_be_unwritten(self):
        result = simulate(('reserve', 'copy1', 'copy2', 'prefix', 'payload'))
        self.assertTrue(result['naive_double_copy_accepts'])
        self.assertFalse(result['complete_at_second_copy'])
        self.assertEqual(result['snapshots'][0], result['snapshots'][1])

    def test_equal_copies_and_cursor_can_be_torn(self):
        result = simulate(('reserve', 'prefix', 'copy1', 'copy2', 'payload'))
        self.assertTrue(result['naive_double_copy_accepts'])
        self.assertEqual(result['snapshots'][1]['bytes'], 'ned!')
        self.assertFalse(result['complete_at_second_copy'])

    def test_copy_after_publication_is_complete_in_model(self):
        result = simulate(('reserve', 'prefix', 'payload', 'copy1', 'copy2'))
        self.assertTrue(result['naive_double_copy_accepts'])
        self.assertTrue(result['complete_at_second_copy'])

    def test_invalid_schedules_reject(self):
        for case in ((), ('reserve',) * 5, ('prefix', 'reserve', 'payload', 'copy1', 'copy2')):
            with self.assertRaises(ValueError):
                simulate(case)

    def test_model_reports_counterexamples_without_hardware_claim(self):
        result = assess_model()
        self.assertEqual(result['interleavings'], 10)
        self.assertEqual(len(result['false_acceptance_schedules']), 2)
        self.assertFalse(result['live_torn_copy_observed'])
        self.assertFalse(result['retrieval_qualified'])


if __name__ == '__main__':
    unittest.main()

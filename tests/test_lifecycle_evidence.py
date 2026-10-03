
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from research.acquisition.observation_lifecycle import Lifecycle


class LifecycleTests(unittest.TestCase):
    def test_timeout_quarantines_even_plausible_late_report(self):
        state = Lifecycle(max_age_ticks=10)
        state.start('source', 'build', 0)
        state.request(1, 1)
        state.invalidate('timeout', 2)
        with self.assertRaises(ValueError): state.report(1, 3, 100)
        with self.assertRaises(ValueError): state.request(2, 4)
        self.assertFalse(state.usable(4))

    def test_new_epoch_after_restart_even_if_counter_increases(self):
        state = Lifecycle(10)
        state.start('source', 'build', 0)
        state.request(1, 1); state.report(1, 2, 100)
        epoch = state.epoch
        state.invalidate('reassociation', 3)
        state.start('source', 'build', 4)
        state.request(1, 5); state.report(1, 6, 200)
        self.assertGreater(state.epoch, epoch)
        self.assertTrue(state.usable(6))

    def test_stale_duplicate_and_regression_invalidate(self):
        for reason in ('expiry', 'duplicate', 'regression'):
            with self.subTest(reason=reason):
                state = Lifecycle(10); state.start('s', 'b', 0)
                state.request(1, 1); state.report(1, 2, 100)
                if reason == 'expiry': self.assertFalse(state.usable(13))
                if reason == 'duplicate':
                    with self.assertRaises(ValueError): state.report(1, 3, 100)
                if reason == 'regression':
                    state.request(2, 3)
                    with self.assertRaises(ValueError): state.report(2, 4, 99)
                self.assertFalse(state.usable(14))

    def test_every_discontinuity_invalidates(self):
        for reason in ('disconnect','reassociation','restart','suspend','resume','collector_loss','trace_loss','build_change','unknown_continuity'):
            state=Lifecycle(10);state.start('s','b',0)
            state.request(1,1);state.report(1,2,100)
            state.invalidate(reason,3)
            self.assertFalse(state.usable(3))


if __name__ == '__main__': unittest.main()

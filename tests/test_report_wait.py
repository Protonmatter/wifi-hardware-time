import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from research.acquisition.report_wait import FLUSH_RETRY_S, MAX_FLUSHES, wait_for_report


class FakeTime:
    def __init__(self):
        self.t = 100.0

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class ReportWaitTests(unittest.TestCase):
    def test_flushes_immediately_then_stops_when_report_arrives(self):
        clock, calls = FakeTime(), []
        arrived = lambda: len(calls) >= 1 and clock.t >= 100.01
        flushes = wait_for_report(arrived, pump=lambda: None, monotonic=clock.monotonic, sleep=clock.sleep,
                                  flush=lambda: calls.append(clock.t) or dict(status=0))
        self.assertEqual(calls, [100.0])
        self.assertEqual(flushes, [dict(status=0)])
        self.assertLess(clock.t, 100.05)

    def test_retries_at_most_max_flushes_then_listens_until_timeout(self):
        clock, calls = FakeTime(), []
        flushes = wait_for_report(lambda: False, pump=lambda: None, monotonic=clock.monotonic, sleep=clock.sleep,
                                  flush=lambda: calls.append(clock.t) or dict(status=0), listen_s=1.0)
        self.assertEqual(len(flushes), MAX_FLUSHES)
        self.assertEqual(MAX_FLUSHES, 5)
        self.assertGreaterEqual(calls[1] - calls[0], FLUSH_RETRY_S)
        self.assertGreaterEqual(clock.t, 101.0)

    def test_without_flush_behaves_like_the_retained_wait(self):
        clock, pumps = FakeTime(), []
        arrived = lambda: clock.t >= 100.5
        flushes = wait_for_report(arrived, pump=lambda: pumps.append(clock.t), monotonic=clock.monotonic,
                                  sleep=clock.sleep)
        self.assertEqual(flushes, [])
        self.assertTrue(pumps)
        self.assertGreaterEqual(clock.t, 100.5)

    def test_rejects_invalid_bounds(self):
        for kwargs in (dict(listen_s=0), dict(retry_s=0), dict(max_flushes=-1)):
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                wait_for_report(lambda: True, pump=lambda: None, monotonic=lambda: 0.0, sleep=lambda s: None, **kwargs)


if __name__ == '__main__':
    unittest.main()

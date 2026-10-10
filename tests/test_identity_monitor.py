import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import threading
import time
import unittest

from research.acquisition import persistent_sampler as api


class Harness:
    """Fake monotonic clock, counter QPC and an injected start that stores or runs the check."""

    def __init__(self, check=None, run_now=False):
        self.now, self.qpc, self.pending, self.calls = [100.0], [0], [], []
        self.check_impl = check or (lambda: None)

        def start(fn):
            self.pending.append(fn)
            if run_now:
                self.pending.pop()()
        self.monitor = api.IdentityMonitor(self.check, lambda: self.now[0], self.next_qpc, start=start)

    def check(self):
        self.calls.append(self.now[0])
        self.check_impl()

    def next_qpc(self):
        self.qpc[0] += 1
        return self.qpc[0]

    def advance(self, seconds):
        self.now[0] += seconds


class IdentityMonitorTests(unittest.TestCase):
    def test_constants(self):
        self.assertEqual((api.IDENTITY_EVERY_S, api.IDENTITY_MAX_AGE_S, api.IDENTITY_CHECK_DEADLINE_S),
                         (30.0, 60.0, 60.0))

    def test_starts_on_the_30_second_cadence_and_never_twice_while_running(self):
        h = Harness()
        h.advance(29.99)
        self.assertFalse(h.monitor.maybe_start())
        self.assertEqual(h.pending, [])
        h.advance(0.01)
        self.assertTrue(h.monitor.maybe_start())
        self.assertEqual(len(h.pending), 1)
        self.assertEqual(h.monitor.next_due, 160.0)
        h.advance(40.0)  # due again, but the first check is still running
        self.assertFalse(h.monitor.maybe_start())
        self.assertEqual(len(h.pending), 1)
        h.pending.pop()()
        self.assertTrue(h.monitor.maybe_start())
        self.assertEqual(h.monitor.next_due, 200.0)

    def test_success_ages_from_the_check_start(self):
        def slow():
            h.advance(5.0)  # the check itself takes 5 s
        h = Harness(slow, run_now=True)
        h.advance(30.0)
        self.assertTrue(h.monitor.maybe_start())  # runs 130 -> 135, success counted at 130
        self.assertEqual(h.monitor.last_success, 130.0)
        h.now[0] = 190.0
        self.assertTrue(h.monitor.gate())
        h.now[0] = 190.01
        self.assertFalse(h.monitor.gate())

    def test_failure_is_raised_by_the_gate_and_stops_further_starts(self):
        def bad():
            raise RuntimeError('Identity/state changed: Status')
        h = Harness(bad, run_now=True)
        h.advance(30.0)
        self.assertTrue(h.monitor.maybe_start())
        self.assertEqual(h.monitor.failure, 'RuntimeError: Identity/state changed: Status')
        with self.assertRaisesRegex(RuntimeError, 'Identity check failed: RuntimeError: Identity/state changed'):
            h.monitor.gate()
        h.advance(60.0)
        self.assertFalse(h.monitor.maybe_start())
        self.assertEqual(len(h.calls), 1)

    def test_hung_check_is_overdue_after_the_deadline(self):
        h = Harness()
        h.advance(30.0)
        self.assertTrue(h.monitor.maybe_start())  # stored, never run: a hung check
        h.advance(60.0)
        self.assertFalse(h.monitor.gate())  # exactly 60 s running: not overdue; age 90 s is stale
        h.advance(0.01)
        with self.assertRaisesRegex(RuntimeError, 'Identity check overdue'):
            h.monitor.gate()

    def test_gate_is_false_once_the_newest_success_is_older_than_60_seconds(self):
        h = Harness()
        h.advance(60.0)
        self.assertTrue(h.monitor.gate())  # construction instant counts as the first success
        self.assertTrue(h.monitor.maybe_start())
        h.advance(0.01)
        self.assertFalse(h.monitor.gate())  # check started at 160 has not finished yet
        h.pending.pop()()
        self.assertTrue(h.monitor.gate())
        self.assertAlmostEqual(h.monitor.last_success, 160.01)  # the check began when its runner called it

    def test_exception_outside_the_check_is_recorded_and_clears_running(self):
        h = Harness(run_now=True)
        h.monitor.now_qpc = lambda: (_ for _ in ()).throw(OSError('qpc unavailable'))
        h.advance(30.0)
        h.monitor.maybe_start()
        self.assertIsNone(h.monitor.running_since)
        self.assertIn('qpc unavailable', h.monitor.failure)
        with self.assertRaisesRegex(RuntimeError, 'Identity check failed'):
            h.monitor.gate()

    def test_start_failure_is_recorded_not_raised(self):
        h = Harness()
        def boom(fn):
            raise RuntimeError("can't start new thread")
        h.monitor.start = boom
        h.advance(30.0)
        self.assertFalse(h.monitor.maybe_start())
        self.assertIsNone(h.monitor.running_since)
        self.assertIn('Identity check start failed: RuntimeError', h.monitor.failure)
        with self.assertRaisesRegex(RuntimeError, 'Identity check failed'):
            h.monitor.gate()
        self.assertFalse(h.monitor.maybe_start())

    def test_drain_completed_returns_each_record_once(self):
        outcomes = [None, RuntimeError('mismatch')]
        def check():
            error = outcomes.pop(0)
            if error:
                raise error
        h = Harness(check, run_now=True)
        h.advance(30.0)
        h.monitor.maybe_start()
        records = h.monitor.drain_completed()
        self.assertEqual(records, [dict(started_qpc=1, finished_qpc=2, ok=True, error=None)])
        self.assertEqual(h.monitor.drain_completed(), [])
        h.advance(30.0)
        h.monitor.maybe_start()
        self.assertEqual(h.monitor.drain_completed(),
                         [dict(started_qpc=3, finished_qpc=4, ok=False, error='RuntimeError: mismatch')])

    def test_wait_idle_times_out_on_a_running_check(self):
        h = Harness()
        self.assertTrue(h.monitor.wait_idle(h.advance, 1.0))  # idle: no wait
        h.advance(30.0)
        h.monitor.maybe_start()
        self.assertFalse(h.monitor.wait_idle(h.advance, 1.0))
        h.pending.pop()()
        self.assertTrue(h.monitor.wait_idle(h.advance, 1.0))

    def real_thread_monitor(self, clock, release):
        entered = threading.Event()
        def check():
            entered.set()
            if not release.wait(10.0):
                raise RuntimeError('test check never released')
        monitor = api.IdentityMonitor(check, lambda: clock[0], lambda: int(clock[0] * 1000), interval_s=0.0)
        clock[0] = 30.0
        self.assertTrue(monitor.maybe_start())
        self.assertTrue(entered.wait(5.0))
        return monitor

    def test_check_finishing_after_its_deadline_latches_without_a_gate_call(self):
        clock, release = [0.0], threading.Event()
        monitor = self.real_thread_monitor(clock, release)
        clock[0] = 91.0
        release.set()
        deadline = time.monotonic() + 5.0
        while monitor.running_since is not None and time.monotonic() < deadline:
            time.sleep(0.005)
        self.assertIsNone(monitor.running_since)
        self.assertIn('overran its 60 s deadline (61.000 s)', monitor.failure)
        self.assertEqual(monitor.last_success, 0.0)
        records = monitor.drain_completed()
        self.assertEqual([r['ok'] for r in records], [False])
        self.assertIn('overran', records[0]['error'])
        with self.assertRaisesRegex(RuntimeError, 'Identity check failed: Identity check overran'):
            monitor.gate()

    def test_check_finishing_exactly_at_the_deadline_is_a_success(self):
        def check():
            h.advance(60.0)
        h = Harness(check, run_now=True)
        h.advance(30.0)
        self.assertTrue(h.monitor.maybe_start())
        self.assertIsNone(h.monitor.failure)
        self.assertEqual(h.monitor.last_success, 130.0)
        self.assertEqual([r['ok'] for r in h.monitor.drain_completed()], [True])

    def test_overrun_keeps_the_first_failure(self):
        def check():
            h.advance(61.0)
        h = Harness(check, run_now=True)
        h.monitor.failure = 'earlier failure'
        h.monitor.running_since = h.now[0]
        h.monitor._run()
        self.assertEqual(h.monitor.failure, 'earlier failure')
        self.assertEqual([r['ok'] for r in h.monitor.drain_completed()], [False])

    def test_wait_idle_gives_up_at_the_running_checks_own_deadline(self):
        h = Harness()
        h.advance(30.0)
        h.monitor.maybe_start()  # stored, never run
        started = h.now[0]
        self.assertFalse(h.monitor.wait_idle(h.advance, 1000.0))
        self.assertAlmostEqual(h.now[0] - started, 60.0, delta=0.05)

    def test_default_start_runs_the_check_on_a_thread(self):
        release, entered = threading.Event(), threading.Event()
        def check():
            entered.set()
            if not release.wait(10.0):
                raise RuntimeError('test check never released')
        monitor = api.IdentityMonitor(check, time.monotonic, time.perf_counter_ns, interval_s=0.0)
        before = time.monotonic()
        self.assertTrue(monitor.maybe_start())
        self.assertLess(time.monotonic() - before, 0.5)
        self.assertTrue(entered.wait(5.0))
        self.assertTrue(monitor.gate())
        release.set()
        self.assertTrue(monitor.wait_idle(time.sleep, 5.0))
        records = monitor.drain_completed()
        self.assertEqual(len(records), 1)
        self.assertIs(records[0]['ok'], True)
        self.assertIsNone(records[0]['error'])


if __name__ == '__main__':
    unittest.main()

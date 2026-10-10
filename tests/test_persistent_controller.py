import contextlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.acquisition.run_bound_campaign import parse


class ControllerTests(unittest.TestCase):
    def run_execute(self, root, observer_fails=False, fail_identity_call=None, duration_s='60', starter=None):
        """Drive _execute with fakes only; identity checks run synchronously through the patched starter."""
        import research.acquisition.run_bound_campaign as bound
        import research.acquisition.run_acquisition_campaign as acquisition
        import research.acquisition.bss_reader as bss
        api = self.api()
        now, submitted, checks, closed = [1.0], [], [], []
        class Clock:
            frequency = 10_000_000
            def now(self): return round(now[0] * self.frequency)
        clock = Clock()
        class Trace:
            def __init__(self, session, folder): self.folder = folder
            def start(self, options): (self.folder / 'tsf.etl').touch()
            def stop(self): pass
        class Observer:
            ready, association = True, 'fixture'
            report_due = None
            def __init__(self, *args): pass
            def pump(self, gate):
                if submitted and observer_fails:
                    raise RuntimeError('observer lifecycle failure')
                if self.report_due is not None and now[0] >= self.report_due:
                    gate.consume(dict(kind='report', raw_timestamp=round(submitted[-1] * clock.frequency) + 100,
                                      received_qpc=clock.now(), vdev=0))
                    self.report_due = None
            def wait(self, seconds, gate):
                now[0] += max(0, seconds)
                self.pump(gate)
            def close(self, gate): pass
        class Reader:
            def __init__(self, *args): pass
            def read(self, qpc): raise bss.CacheEntryUnavailable(0)
            def close(self): pass
        class Client:
            def __init__(self, *args): self.observer, self.gate = args[-2:]
            def start(self): pass
            def pulse(self): self.observer.pump(self.gate) if hasattr(self, 'gate') else None
            def submit(self, number):
                submitted.append(now[0])
                self.gate.consume(dict(kind='command', raw_timestamp=clock.now(), action=4, vdev=0))
                self.observer.report_due = now[0] + 1.96
                return dict(sequence=number, qpc_request_before=clock.now(), qpc_request_completed=clock.now(),
                            success=True, schema='wht/persistent-tsf-request-v1')
            def close(self, failed=False):
                closed.append(failed)
                return not failed
        def identity(index):
            checks.append(now[0])
            now[0] += 1.1
            if len(checks) == fail_identity_call:
                raise RuntimeError('Identity/state changed: Status')
            return dict(InterfaceGuid='fixture')
        args = parse(['--if-index', '7', '--condition', 'idle', '--duration-s', duration_s, '--sampler', 'persistent'])
        with contextlib.ExitStack() as stack:
            for obj, name, value in ((bound.time, 'monotonic', lambda: now[0]),
                                     (bound.time, 'sleep', lambda seconds: now.__setitem__(0, now[0] + seconds)),
                                     (acquisition, 'ROOT', root), (acquisition, 'TraceOwner', Trace),
                                     (acquisition, 'Observer', Observer), (acquisition, 'identity', identity),
                                     (acquisition, 'same_identity', lambda *args: None),
                                     (bss, 'BssReader', Reader), (api, 'PersistentClient', Client),
                                     (api, 'start_identity_check', starter or (lambda fn: fn())),
                                     (bound, 'finalize', lambda *args: None)):
                stack.enter_context(patch.object(obj, name, value))
            code = bound._execute(args, clock, dict(InterfaceGuid='fixture'), {}, root / 'marker.json')
        return code, submitted, checks, closed, now[0]

    def test_persistent_campaign_keeps_report_wait_and_stops_on_observer_failure(self):
        for observer_fails in (False, True):
            with self.subTest(observer_fails=observer_fails), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                code, submitted, checks, closed, _ = self.run_execute(root, observer_fails=observer_fails)
                self.assertEqual(code, 1 if observer_fails else 0)
                self.assertEqual(closed, [observer_fails])
                if observer_fails:
                    self.assertEqual(len(submitted), 1)
                else:
                    self.assertGreater(len(submitted), 10)
                    self.assertTrue(all(b - a >= 1.96 for a, b in zip(submitted, submitted[1:])))
                    # Was 3: the pre-loop synchronous check that validates the monitor's first success
                    # is new, plus the 30-second background checks and the final identity check.
                    self.assertLessEqual(len(checks), 4)
                    schedules = list((root / 'artifacts').rglob('sampler-schedule.jsonl'))
                    rows = [json.loads(line) for line in schedules[0].read_text().splitlines()]
                    self.assertEqual(len(rows), len(submitted))
                    # Unchanged: slots are skipped because each 1.96 s report wait overruns the 1 s spacing.
                    self.assertTrue(any(row['skipped_slots'] > 0 for row in rows))
                    self.assertTrue(all(row['report_received_qpc'] >= row['qpc_request_completed'] for row in rows))
                    background = [record for row in rows for record in row['background_identity_checks']]
                    self.assertTrue(background)
                    self.assertTrue(all(record['ok'] for record in background))
                    # Equality holds only with the synchronous test starter; with real threads a check
                    # started in one cycle can complete in a later one.
                    self.assertEqual(sum(row['identity_checked'] for row in rows), len(background))
                    self.assertTrue((schedules[0].parent / 'background-identity-tail.json').exists())
                    self.assertTrue(all(row['slot_identity_checks'] == [] and row['identity_started_qpc'] is None
                                        and row['identity_finished_qpc'] is None for row in rows))

    def test_failed_background_identity_check_stops_before_any_later_submission(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            # Call 1 is the pre-loop synchronous check; calls 2 and 3 are the first two background
            # checks (about 30 s and 60 s into a 120 s run). The second background check fails.
            code, submitted, checks, closed, _ = self.run_execute(root, fail_identity_call=3, duration_s='120')
            self.assertEqual(code, 1)
            self.assertTrue((root / 'marker.json').exists())
            self.assertEqual(closed, [True])
            tail = json.loads(next((root / 'artifacts').rglob('background-identity-tail.json')).read_text())
            self.assertEqual(tail['schema'], 'wht/background-identity-tail-v1')
            # With the synchronous starter the failing record finishes inside the last cycle's maybe_start and
            # is drained into that cycle's schedule row, so the tail is empty; it must be in exactly one place.
            rows = [json.loads(line) for path in (root / 'artifacts').rglob('sampler-schedule.jsonl')
                    for line in path.read_text().splitlines()]
            persisted = [record for row in rows for record in row['background_identity_checks']] + tail['checks']
            self.assertEqual([record['ok'] for record in persisted].count(False), 1)
            self.assertIn('Identity/state changed', tail['monitor_failure'])
            failed_at = checks[2]
            self.assertTrue(any(moment > checks[1] for moment in submitted))  # sampling ran past check 2
            self.assertTrue(all(moment < failed_at for moment in submitted))
            self.assertEqual(len(checks), 4)  # the final synchronous identity check still runs

    def test_hung_background_check_never_lets_sampling_continue_on_stale_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            hung = []
            # The background starter records the check but never runs it: a check that hangs forever.
            code, submitted, checks, closed, finished = self.run_execute(root, duration_s='300', starter=hung.append)
            self.assertEqual(code, 1)
            self.assertTrue((root / 'marker.json').exists())
            self.assertEqual(len(hung), 1)  # never a second check while one is running
            validated = checks[0]  # pre-loop synchronous check; its start is the monitor's first success
            self.assertTrue(submitted)
            self.assertTrue(all(moment - validated <= 60.0 for moment in submitted))
            # The overdue check (about 30 + 60 s after construction) stops the run long before 300 s.
            self.assertLess(finished, validated + 30 + 60 + 60 + 10)
            self.assertEqual(len(checks), 2)  # pre-loop and final; the final check waited for the deadline
            tail = json.loads(next((root / 'artifacts').rglob('background-identity-tail.json')).read_text())
            self.assertEqual(tail['checks'], [])  # written even when empty

    def test_post_loop_wait_timeout_is_not_repeated_during_teardown(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            hung = []
            # The loop ends about 61 s after the pre-loop check (duration 60 s) with the hung check started
            # at about +30 s and not yet overdue. The post-loop wait_idle then times out after 60 s, so the
            # final check runs at about +61 + 2 + 60 = +123 s. The old fallback waited another 60 s (+183 s).
            code, submitted, checks, closed, finished = self.run_execute(root, duration_s='60', starter=hung.append)
            self.assertEqual(code, 1)
            self.assertEqual(len(checks), 2)
            self.assertLess(checks[1] - checks[0], 130.0)

    def test_mode_defaults_and_limits(self):
        base = ['--if-index', '7', '--condition', 'idle']
        legacy = parse(base)
        self.assertEqual(getattr(legacy, 'sampler', None), 'per-request')
        self.assertEqual(legacy.spacing_s, 2.0)
        self.assertEqual(parse(base + ['--sampler', 'persistent']).spacing_s, 1.0)
        self.assertEqual(parse(base + ['--sampler', 'persistent', '--spacing-s', '0.5']).spacing_s, 0.5)
        with self.assertRaises(SystemExit):
            parse(base + ['--sampler', 'persistent', '--spacing-s', 'nan'])

    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('research.acquisition.persistent_sampler'), 'controller support missing')
        return importlib.import_module('research.acquisition.persistent_sampler')

    def test_fixed_slots_skip_delay_and_never_catch_up(self):
        api = self.api()
        slots = api.RequestSlots(100.0, 1.0)
        self.assertEqual(slots.reserve(100.0), (100.0, 0))
        slots.submitted(100.2)
        self.assertEqual(slots.reserve(102.96), (103.0, 2))
        slots.submitted(103.1)
        # 103.1 + 1.0 * 0.9 = 104.0 is exactly slot 4, so a 0.1 s late submission skips nothing.
        self.assertEqual(slots.reserve(103.2), (104.0, 0))
        slots.submitted(104.0)
        # Idle until 137.0: slot 37 is next, slots 5..36 (32 of them) are skipped, never caught up.
        self.assertEqual(slots.reserve(137.0), (137.0, 32))

    def test_submission_jitter_does_not_skip_slots(self):
        api = self.api()
        slots = api.RequestSlots(100.0, 1.0)
        previous = None
        for i in range(20):
            scheduled, skipped = slots.reserve(100.0 + i + 0.004)
            if i:
                self.assertEqual(skipped, 0)
                self.assertEqual(scheduled - previous, 1.0)
            previous = scheduled
            slots.submitted(scheduled + 0.006)

    def test_late_submission_beyond_tolerance_still_skips(self):
        api = self.api()
        slots = api.RequestSlots(100.0, 1.0)
        self.assertEqual(slots.reserve(100.0), (100.0, 0))
        slots.submitted(100.15)
        # 100.15 + 0.9 = 101.05 > 101, so slot 1 is too soon and slot 2 is chosen.
        self.assertEqual(slots.reserve(100.2), (102.0, 1))

    def test_identity_timer_is_monotonic_not_request_count(self):
        api = self.api()
        timer = api.IdentityTimer(100.0)
        self.assertFalse(timer.due(129.99))
        self.assertTrue(timer.due(130.0))
        timer.checked(135.0)
        self.assertFalse(timer.due(164.99))
        self.assertTrue(timer.due(165.0))

    def test_long_slot_wait_renews_lease_and_checks_identity_without_submitting(self):
        api = self.api()
        self.assertTrue(hasattr(api, 'wait_for_slot'), 'slot wait must maintain control and identity')
        now, pulses, checks = [101.98], [], []
        slots, timer = api.RequestSlots(100.0, 60.0), api.IdentityTimer(100.0)
        slots.reserve(100.0)
        slots.submitted(100.02)
        def identity():
            checks.append(now[0])
            now[0] += 1.1
        scheduled, skipped = api.wait_for_slot(slots, 300.0, timer, lambda: pulses.append(now[0]), identity,
                                               lambda seconds: now.__setitem__(0, now[0] + seconds),
                                               lambda: now[0])
        # 100.02 + 60 * 0.9 = 154.02 <= 160, so slot 160 is eligible and nothing is skipped.
        self.assertEqual((scheduled, skipped), (160.0, 0))
        # The 30 s timer (created at 100) fires at ~130 and next at ~161, after slot 160: exactly one check.
        self.assertGreaterEqual(len(checks), 1)
        self.assertLess(max(b - a for a, b in zip(pulses, pulses[1:])), 2.0)
        self.assertGreaterEqual(now[0], 160.0)

    def test_fresh_permit_consumed_once_and_revoke_serialized(self):
        api = self.api()
        class Lock:
            locked = contextlib.nullcontext
        # Use a real file protocol with an injected mutex and process liveness.
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'control.json'
            now, alive = [10.0], [True]
            record = dict(schema=api.CONTROL_SCHEMA, session_id='s', controller_pid=1,
                          state='permitted', sequence=1, heartbeat=10.0)
            api.durable_save(path, record)
            owner = api.ControllerOwner(path, Lock(), lambda: alive[0], lambda: now[0], 's', 1)
            with owner.authorize(1):
                self.assertEqual(json.loads(path.read_text())['state'], 'submitted')
            with self.assertRaises(RuntimeError):
                with owner.authorize(1):
                    self.fail('permit reused')
            record['state'] = 'abort'
            api.durable_save(path, record)
            with self.assertRaises(RuntimeError):
                owner.check()
            record['state'] = 'permitted'
            api.durable_save(path, record)
            alive[0] = False
            with self.assertRaises(RuntimeError):
                with owner.authorize(1):
                    self.fail('dead controller admitted')

    def test_missing_corrupt_expired_communication_fails_closed(self):
        api = self.api()
        class Lock:
            locked = contextlib.nullcontext
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'control.json'
            owner = api.ControllerOwner(path, Lock(), lambda: True, lambda: 100.0, 's', 1)
            for text in ('', '{}', 'broken', json.dumps(dict(schema=api.CONTROL_SCHEMA, session_id='s',
                                                           controller_pid=1, state='ready', sequence=0, heartbeat=0))):
                path.write_text(text)
                with self.assertRaises((RuntimeError, ValueError)):
                    owner.check()


if __name__ == '__main__':
    unittest.main()

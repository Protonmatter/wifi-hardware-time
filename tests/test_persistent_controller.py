import contextlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.acquisition.run_bound_campaign import parse


class ControllerTests(unittest.TestCase):
    def test_persistent_campaign_keeps_report_wait_and_stops_on_observer_failure(self):
        import research.acquisition.run_bound_campaign as bound
        import research.acquisition.run_acquisition_campaign as acquisition
        import research.acquisition.bss_reader as bss
        api = self.api()
        for observer_fails in (False, True):
            with self.subTest(observer_fails=observer_fails), tempfile.TemporaryDirectory() as d:
                root = Path(d)
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
                    return dict(InterfaceGuid='fixture')
                args = parse(['--if-index', '7', '--condition', 'idle', '--duration-s', '60', '--sampler', 'persistent'])
                with contextlib.ExitStack() as stack:
                    for obj, name, value in ((bound.time, 'monotonic', lambda: now[0]),
                                             (bound.time, 'sleep', lambda seconds: now.__setitem__(0, now[0] + seconds)),
                                             (acquisition, 'ROOT', root), (acquisition, 'TraceOwner', Trace),
                                             (acquisition, 'Observer', Observer), (acquisition, 'identity', identity),
                                             (acquisition, 'same_identity', lambda *args: None),
                                             (bss, 'BssReader', Reader), (api, 'PersistentClient', Client),
                                             (bound, 'finalize', lambda *args: None)):
                        stack.enter_context(patch.object(obj, name, value))
                    code = bound._execute(args, clock, dict(InterfaceGuid='fixture'), {}, root / 'marker.json')
                self.assertEqual(code, 1 if observer_fails else 0)
                self.assertEqual(closed, [observer_fails])
                if observer_fails:
                    self.assertEqual(len(submitted), 1)
                else:
                    self.assertGreater(len(submitted), 10)
                    self.assertTrue(all(b - a >= 1.96 for a, b in zip(submitted, submitted[1:])))
                    self.assertLessEqual(len(checks), 3)  # 30-second timer plus final identity
                    schedules = list((root / 'artifacts').rglob('sampler-schedule.jsonl'))
                    rows = [json.loads(line) for line in schedules[0].read_text().splitlines()]
                    self.assertEqual(len(rows), len(submitted))
                    self.assertTrue(any(row['skipped_slots'] > 0 for row in rows))
                    self.assertTrue(all(row['report_received_qpc'] >= row['qpc_request_completed'] for row in rows))

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
        self.assertEqual(slots.reserve(103.2), (105.0, 1))
        slots.submitted(105.0)
        self.assertEqual(slots.reserve(137.0), (137.0, 31))

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
        self.assertEqual((scheduled, skipped), (220.0, 1))
        self.assertGreaterEqual(len(checks), 3)
        self.assertLess(max(b - a for a, b in zip(pulses, pulses[1:])), 2.0)
        self.assertGreaterEqual(now[0], 220.0)

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

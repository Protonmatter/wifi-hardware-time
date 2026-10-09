"""Post-merge acquisition regressions; fake I/O only, local files/locks permitted."""
import copy
import ctypes as ct
import inspect
import contextlib
import json
import sys
import tempfile
import threading
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_tsf_sampler import Clock, Kernel, Owner
from test_sampler_win32 import Fn
from research.tsf import tsf_sampler as api
from research.tsf.sampler_worker import Journal
from research.tsf.sampler_win32 import Win32Kernel
from research.acquisition import persistent_sampler as persistent
from research.acquisition.run_bound_campaign import persist_outcome


def identity():
    return dict(identity_validated=True, driver_sha256=api.QUALIFIED_SHA256,
                interface_index=7, adapter_guid='fixture', mac_hex='020000000001')


def native(*, pending=False):
    calls = []
    dll = SimpleNamespace(
        CreateFileW=Fn(lambda *args: 42), CreateEventW=Fn(lambda *args: 43),
        CloseHandle=Fn(lambda handle: calls.append(('close', handle)) or 1),
        DeviceIoControl=Fn(lambda *args: 0 if pending else 1),
        WaitForSingleObject=Fn(lambda *args: calls.append(('wait', args[1])) or 0xffffffff),
        GetOverlappedResult=Fn(lambda *args: calls.append(('result', args[-1])) or 1),
        CancelIoEx=Fn(lambda *args: calls.append(('cancel',)) or 1))
    return Win32Kernel(api=dll, last_error=lambda: 997 if pending else 0), calls


class OwnershipCorrections(unittest.TestCase):
    def test_additive_event_close_evidence_cannot_contradict_success(self):
        from test_persistent_receipts import evidence
        from research.tsf.sampler_receipts import normalize
        request, session = evidence()
        self.assertTrue(normalize(1, request, session)[1])  # Older v1 receipts remain valid.
        self.assertTrue(normalize(1, dict(request, event_close_attempted=True, event_closed=True), session)[1])
        for values in (dict(event_close_attempted=True, event_closed=False),
                       dict(event_close_attempted=False, event_closed=True),
                       dict(event_close_attempted='true', event_closed=True), dict(event_closed=True)):
            with self.subTest(values=values), self.assertRaises(ValueError):
                normalize(1, dict(request, **values), session)

    def test_finalized_request_bytes_survive_later_session_and_device_failures(self):
        for reason in ('observer failed', 'controller disappeared', 'device close failed'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as d:
                folder, clock = Path(d), Clock()
                kernel = Kernel(api, clock)
                sampler = api.Sampler(kernel, clock, Owner(), Journal(folder, folder / 'marker'),
                                      identity, session_id='s')
                sampler.start(); sampler.submit(1)
                path = folder / 'sampler-request-00001.json'
                before = path.read_bytes()
                receipt = copy.deepcopy(sampler.receipt)
                if reason == 'device close failed':
                    kernel.close_ok = False
                    self.assertFalse(sampler.close())
                else:
                    sampler.stop(reason)
                self.assertEqual(before, path.read_bytes())
                self.assertEqual(receipt, sampler.receipt)
                self.assertTrue(json.loads((folder / 'sampler-session.json').read_text())['failed'])

    def test_active_terminal_evidence_and_event_close_failures_still_fail_request(self):
        for fault in ('extent', 'event'):
            with self.subTest(fault=fault):
                clock = Clock(); kernel = Kernel(api, clock)
                sampler = api.Sampler(kernel, clock, Owner(), lambda row: None, identity, session_id='s')
                sampler.start()
                if fault == 'extent': kernel.initial = api.IoResult(True, 0, 101, b'x' * 101)
                else: kernel.release = lambda operation: False
                sampler.submit(1)
                self.assertFalse(sampler.receipt['success'])
                self.assertIsNotNone(sampler.failure)

    def test_failed_wait_can_drain_terminal_result_but_stays_failed(self):
        for terminal, error in ((True, 0), (False, 995)):
            with self.subTest(terminal=terminal):
                kernel, calls = native(pending=True)
                clock = Clock()
                sampler = api.Sampler(kernel, clock, Owner(), lambda row: None, identity, session_id='s')
                sampler.start(); sampler.submit(1)
                kernel.k.GetOverlappedResult = Fn(lambda *args: calls.append(('result', args[-1])) or terminal)
                kernel.error = lambda: error
                sampler.step()
                self.assertFalse(sampler.pending)
                self.assertFalse(sampler.receipt['success'])
                self.assertTrue(sampler.receipt['completion_established'])
                self.assertEqual(calls.count(('cancel',)), 1)
                self.assertEqual(calls.count(('close', 43)), 1)
                self.assertIn(('result', False), calls)
                self.assertTrue(sampler.close())
                with self.assertRaises(RuntimeError): sampler.submit(2)

    def test_failed_wait_unresolved_queries_retain_all_resources_and_throttle(self):
        for error in (996, 6, 87):
            with self.subTest(error=error):
                kernel, calls = native(pending=True)
                clock = Clock()
                sampler = api.Sampler(kernel, clock, Owner(), lambda row: None, identity, session_id='s')
                sampler.start(); sampler.submit(1)
                kernel.k.GetOverlappedResult = Fn(lambda *args: calls.append(('result', args[-1])) or 0)
                kernel.error = lambda: error
                for _ in range(3): sampler.step()
                self.assertTrue(sampler.pending)
                self.assertFalse(sampler.close())
                self.assertEqual(calls.count(('result', False)), 3)
                self.assertEqual(calls.count(('cancel',)), 1)
                self.assertNotIn(('close', 43), calls)
                self.assertGreaterEqual(clock.monotonic(), 1.15)

    def test_interrupt_after_successful_native_close_never_retries_same_handle(self):
        for target in ('event', 'device'):
            with self.subTest(target=target):
                kernel, calls = native()
                sampler = api.Sampler(kernel, Clock(), Owner(), lambda row: None, identity, session_id='s')
                sampler.start()
                method = Win32Kernel.release if target == 'event' else Win32Kernel.close
                source, start = inspect.getsourcelines(method)
                close_line = next(start + index for index, line in enumerate(source) if 'self.k.CloseHandle(' in line)
                injected = [False]
                def interrupt(frame, event, arg):
                    if frame.f_code is method.__code__ and event == 'line' and frame.f_lineno > close_line and not injected[0]:
                        injected[0] = True
                        raise KeyboardInterrupt('after native close')
                    return interrupt
                if target == 'device': sampler.submit(1)
                sys.settrace(interrupt)
                try:
                    if target == 'event': sampler.submit(1)
                    else: sampler.close()
                finally: sys.settrace(None)
                sampler.close(); sampler.close()
                self.assertTrue(injected[0])
                self.assertEqual(calls.count(('close', 43 if target == 'event' else 42)), 1)
                self.assertIsNotNone(sampler.failure)

    def test_native_false_and_interrupt_before_close_are_never_blindly_retried(self):
        for raises in (False, True):
            with self.subTest(raises=raises):
                kernel, calls = native()
                def close(handle):
                    calls.append(('close', handle))
                    if raises: raise KeyboardInterrupt('native outcome unknown')
                    return 0
                kernel.k.CloseHandle = Fn(close)
                sampler = api.Sampler(kernel, Clock(), Owner(), lambda row: None, identity, session_id='s')
                sampler.start(); sampler.submit(1)
                self.assertFalse(sampler.close()); self.assertFalse(sampler.close())
                self.assertEqual(calls.count(('close', 43)), 1)
                self.assertIsNotNone(sampler.operation)
                self.assertFalse(sampler.receipt['success'])

    def test_interrupt_after_released_flag_preserves_uncertain_cleanup_without_retry(self):
        kernel, calls = native()
        sampler = api.Sampler(kernel, Clock(), Owner(), lambda row: None, identity, session_id='s')
        sampler.start()
        lines, start = inspect.getsourcelines(Win32Kernel.release)
        boundary = start + next(i for i, line in enumerate(lines) if 'self.operation = None' in line)
        def interrupt(frame, event, arg):
            if event == 'line' and frame.f_code is Win32Kernel.release.__code__ and frame.f_lineno == boundary:
                raise KeyboardInterrupt('released flag set; owner bookkeeping interrupted')
            return interrupt
        sys.settrace(interrupt)
        try: sampler.submit(1)
        finally: sys.settrace(None)
        self.assertTrue(kernel.operation.released)
        self.assertFalse(sampler.close())
        self.assertFalse(sampler.close())
        self.assertEqual(calls.count(('close', 43)), 1)
        self.assertNotIn(('close', 42), calls)
        self.assertFalse(sampler.receipt['event_closed'])
        self.assertIsNotNone(sampler.failure)


class QuarantineCorrections(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows sharing regression')
    def test_controller_worker_interleaving_never_opens_marker_for_direct_write(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d); marker = folder / 'marker.json'
            journal = Journal(folder, marker)
            snapshot = dict(session=dict(state='QUARANTINED_DRAIN_PENDING', failed=True,
                            failure='worker pending', session_id='s', outstanding_operations=1), request=None)
            original = Path.write_text
            def interleaved(path, data, *args, **kwargs):
                if path == marker:
                    with path.open('w', encoding='utf-8') as stream:
                        journal(snapshot)  # Real Windows destination handle rejects replacement.
                        return stream.write(data)
                return original(path, data, *args, **kwargs)
            with patch.object(Path, 'write_text', interleaved):
                persist_outcome(folder, marker, {}, 'controller timeout', lambda: 'now')
            journal(snapshot)
            result = json.loads(marker.read_text())
            self.assertEqual({item['reason'] for item in result['causes']}, {'controller timeout', 'worker pending'})
            self.assertTrue(json.loads((folder / 'sampler-session.json').read_text())['failed'])

    def test_marker_failure_does_not_suppress_final_worker_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            journal = Journal(folder, folder / 'marker')
            snapshot = dict(session=dict(state='STOPPED', failed=True, failure='lost owner',
                            session_id='s', outstanding_operations=0), request=dict(sequence=1, success=False))
            original = persistent.durable_save
            def fail_marker(path, data):
                if path == folder / 'marker': raise OSError('marker unavailable')
                return original(path, data)
            with patch('research.tsf.sampler_worker.durable_save', fail_marker), \
                 patch.object(persistent, 'durable_save', fail_marker):
                with self.assertRaises(OSError): journal(snapshot)
            self.assertEqual(json.loads((folder / 'sampler-session.json').read_text()), snapshot['session'])
            self.assertEqual(json.loads((folder / 'sampler-request-00001.json').read_text()), snapshot['request'])
            self.assertEqual(len((folder / 'sampler-events.jsonl').read_text().splitlines()), 1)

    def test_repeated_marker_failure_retries_marker_without_duplicate_snapshots(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d); marker = folder / 'marker'
            journal = Journal(folder, marker)
            snapshot = dict(session=dict(state='QUARANTINED_DRAIN_PENDING', failed=True,
                            failure='deadline', session_id='s', outstanding_operations=1), request=None)
            with patch('research.tsf.sampler_worker.record_quarantine', side_effect=OSError('marker busy')) as writer:
                for _ in range(5):
                    with self.assertRaises(OSError): journal(snapshot)
            self.assertEqual(writer.call_count, 5)
            self.assertEqual(len((folder / 'sampler-events.jsonl').read_text().splitlines()), 1)
            journal(snapshot)
            self.assertTrue(marker.exists())
            self.assertEqual(len((folder / 'sampler-events.jsonl').read_text().splitlines()), 1)

    def test_controller_result_survives_marker_failure(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            with patch('research.acquisition.run_bound_campaign.record_quarantine', side_effect=OSError('marker busy')):
                with self.assertRaises(OSError): persist_outcome(folder, folder / 'marker', {}, 'failed', lambda: 'now')
            result = json.loads((folder / 'run-result.json').read_text())
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'failed')

    def test_concurrent_distinct_causes_are_preserved_and_reader_serialized(self):
        self.assertTrue(hasattr(persistent, 'record_quarantine'))
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / 'marker'
            barrier = threading.Barrier(3)
            errors = []
            def writer(origin):
                try:
                    barrier.wait(5)
                    for number in range(10):
                        persistent.record_quarantine(marker, dict(reason=f'{origin}-{number}'))
                except BaseException as error: errors.append(error)
            threads = [threading.Thread(target=writer, args=(origin,)) for origin in ('worker', 'controller')]
            for thread in threads: thread.start()
            barrier.wait(5)
            for thread in threads: thread.join(10)
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(errors, [])
            self.assertEqual(len(json.loads(marker.read_text())['causes']), 20)

    def test_cross_process_marker_writer_and_reader_protocol(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d); marker = folder / 'marker'
            # Local child interpreters use only stdlib files/locks, never device/trace APIs.
            program = '''
import json, sys, time
from pathlib import Path
from research.acquisition.persistent_sampler import record_quarantine, quarantine_locked
marker, origin, signal = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
signal.with_name(origin + '.ready').touch()
deadline = time.monotonic() + 10
while not signal.exists():
    if time.monotonic() >= deadline: raise RuntimeError('test startup deadline')
    time.sleep(.005)
for number in range(15):
    record_quarantine(marker, dict(reason=origin + '-' + str(number)))
    with quarantine_locked(marker):
        assert isinstance(json.loads(marker.read_text())['causes'], list)
'''
            signal = folder / 'go'
            children = [subprocess.Popen([sys.executable, '-B', '-c', program, str(marker), origin, str(signal)],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        cwd=Path(__file__).resolve().parents[1]) for origin in ('worker', 'controller')]
            try:
                signal.touch()
                for child in children:
                    stdout, stderr = child.communicate(timeout=15)
                    self.assertEqual(child.returncode, 0, stdout + stderr)
            finally:
                for child in children:
                    if child.poll() is None: child.kill(); child.wait()
            self.assertEqual(len(json.loads(marker.read_text())['causes']), 30)

    def test_marker_lock_timeout_keeps_existing_marker_and_unfinished_record(self):
        import errno
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d); marker = folder / 'marker'; unfinished = folder / 'unfinished'
            marker.write_text('{"reason":"original"}'); unfinished.write_text('retained')
            before = marker.read_bytes()
            target = 'msvcrt.locking' if sys.platform == 'win32' else 'fcntl.flock'
            with patch(target, side_effect=OSError(errno.EACCES, 'busy')) as acquire, \
                 patch.object(persistent.time, 'sleep') as sleep:
                with self.assertRaises(TimeoutError):
                    persistent.record_quarantine(marker, dict(reason='new'))
            self.assertEqual(acquire.call_count, 101)
            self.assertEqual(sleep.call_count, 100)
            self.assertEqual(marker.read_bytes(), before)
            self.assertTrue(unfinished.exists())

    def test_prior_marker_cause_survives_migration_and_corruption_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / 'marker'
            marker.write_text('{"reason":"legacy"}')
            persistent.record_quarantine(marker, dict(reason='new'))
            self.assertEqual([item['reason'] for item in json.loads(marker.read_text())['causes']], ['legacy', 'new'])
            marker.write_text('broken')
            with self.assertRaises(ValueError): persistent.record_quarantine(marker, dict(reason='new'))
            self.assertEqual(marker.read_text(), 'broken')


class LossAndTraceCorrections(unittest.TestCase):
    def test_final_loss_policy_integer_boundaries_and_zero_requests(self):
        from research.acquisition.run_bound_campaign import loss_budget_exceeded
        for losses, count, exceeded in ((0, 0, True), (0, 1, False), (1, 99, True),
                                         (1, 100, False), (2, 100, True), (1, 101, False)):
            with self.subTest(losses=losses, count=count):
                self.assertEqual(loss_budget_exceeded(losses, count, final=True), exceeded)
        self.assertFalse(loss_budget_exceeded(99, 99))
        self.assertTrue(loss_budget_exceeded(100, 100))

    def test_short_run_final_loss_failure_in_both_modes(self):
        import research.acquisition.run_bound_campaign as bound
        import research.acquisition.run_acquisition_campaign as acquisition
        import research.acquisition.bss_reader as bss
        for mode in ('per-request', 'persistent'):
            for lost in (False, True, None):
                with self.subTest(mode=mode, lost=lost), tempfile.TemporaryDirectory() as d:
                    root, clock, timing = Path(d), Clock(), []
                    class Trace:
                        def __init__(self, session, folder): self.folder = folder
                        def start(self, options): (self.folder / 'tsf.etl').write_bytes(b'')
                        def stop(self): pass
                    class Observer:
                        ready, association = True, 'fixture'
                        def __init__(self, *args): pass
                        def pump(self, gate): pass
                        def wait(self, seconds, gate): clock.sleep(seconds)
                        def close(self, gate): pass
                    class Reader:
                        def __init__(self, *args): pass
                        def read(self, *args): raise bss.CacheEntryUnavailable(0)
                        def close(self): pass
                    def submit(root, folder, number, index, frequency, observer, gate):
                        qpc = clock.now()
                        rows = [dict(kind='command', raw_timestamp=qpc + 1, action=4, vdev=0),
                                dict(kind='report', raw_timestamp=qpc + (30_000 if lost else 10), vdev=0)]
                        for row in rows: gate.consume(row)
                        timing.extend(rows)
                        return dict(success=True, qpc_request_before=qpc, qpc_request_completed=qpc + 1)
                    class Client:
                        def __init__(self, *args): self.observer, self.gate = args[-2:]
                        def start(self): pass
                        def pulse(self): pass
                        def submit(self, number): return submit(None, None, number, 7, clock.frequency, self.observer, self.gate)
                        def close(self, failed=False): return True
                    def decoder(command, **kwargs):
                        rows = [dict(kind='header', events_lost=0, buffers_lost=0), *timing]
                        return subprocess.CompletedProcess(command, 0, '\n'.join(json.dumps(row) for row in rows), '')
                    args = bound.parse(['--if-index', '7', '--condition', 'idle', '--duration-s', '60',
                                        '--spacing-s', '1', '--sampler', mode])
                    if lost is None: args.duration_s = 0  # Inject an empty collection into the internal finalizer.
                    with contextlib.ExitStack() as stack:
                        for obj, name, value in ((bound.time, 'monotonic', clock.monotonic), (bound.time, 'sleep', clock.sleep),
                            (acquisition, 'ROOT', root), (acquisition, 'TraceOwner', Trace), (acquisition, 'Observer', Observer),
                            (acquisition, 'identity', lambda index: {}), (acquisition, 'same_identity', lambda *args: None),
                            (bss, 'BssReader', Reader), (bound, 'submit', submit), (acquisition, 'run', decoder),
                            (persistent, 'PersistentClient', Client)):
                            stack.enter_context(patch.object(obj, name, value))
                        code = bound._execute(args, clock, dict(InterfaceGuid='fixture'), {}, root / 'marker')
                    result = json.loads(next(root.rglob('run-result.json')).read_text())
                    failed = lost is not False
                    self.assertEqual(code, int(failed))
                    self.assertEqual(result['success'], not failed)
                    if lost is None: self.assertEqual(result['request_count'], 0)
                    else: self.assertGreater(result['request_count'], 0)
                    self.assertLess(result['request_count'], 100)
                    self.assertEqual((root / 'marker').exists(), failed)

    def test_trace_stop_retries_exact_session_and_retains_unproven_state(self):
        from research.acquisition.run_acquisition_campaign import TraceOwner
        for success_at in (None, 2):
            with self.subTest(success_at=success_at), tempfile.TemporaryDirectory() as d:
                folder, calls = Path(d), []
                owner = TraceOwner('fixture-exact-session', folder); owner.attempted = True
                def run(command, timeout=30):
                    calls.append((command, timeout))
                    if len(calls) != success_at: raise RuntimeError('injected stop failure')
                    return subprocess.CompletedProcess(command, 0, 'stopped', '')
                with patch('research.acquisition.run_acquisition_campaign.run', run):
                    if success_at is None:
                        with self.assertRaises(RuntimeError): owner.stop()
                    else: owner.stop()
                self.assertEqual(len(calls), success_at or 3)
                self.assertTrue(all(command == ['logman', 'stop', 'fixture-exact-session', '-ets'] for command, _ in calls))
                self.assertTrue(all(timeout <= 5 for _, timeout in calls))
                self.assertEqual(owner.attempted, success_at is None)
                receipts = json.loads((folder / 'trace-stop-attempts.json').read_text())
                self.assertEqual(len(receipts['attempts']), success_at or 3)
                self.assertEqual(receipts['stopped'], success_at is not None)

    def test_trace_stop_timeout_interruption_and_receipt_failure_keep_attempted(self):
        from research.acquisition.run_acquisition_campaign import TraceOwner
        for fault in ('timeout', 'interrupt', 'receipt'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                owner = TraceOwner('exact-session', Path(d)); owner.attempted = True
                calls = []
                def run(command, timeout=30):
                    calls.append(command)
                    if fault == 'timeout': raise subprocess.TimeoutExpired(command, timeout)
                    if fault == 'interrupt': raise KeyboardInterrupt('interrupted')
                    return subprocess.CompletedProcess(command, 0, 'stopped', '')
                with patch('research.acquisition.run_acquisition_campaign.run', run), \
                     (patch.object(Path, 'write_text', side_effect=OSError('receipt disk failure'))
                      if fault == 'receipt' else contextlib.nullcontext()):
                    with self.assertRaises(BaseException): owner.stop()
                self.assertTrue(owner.attempted)
                self.assertEqual(len(calls), 3 if fault == 'timeout' else 1)
                self.assertFalse(json.loads((Path(d) / 'trace-stop-attempts.json').read_text())['stopped'])

    def test_trace_stop_journal_failure_cannot_prevent_owned_trace_cleanup(self):
        from research.acquisition.run_acquisition_campaign import TraceOwner
        for failed_writes in ({1}, {1, 2}, {2}):
            with self.subTest(failed_writes=failed_writes), tempfile.TemporaryDirectory() as d:
                owner = TraceOwner('exact-owned-session', Path(d)); owner.attempted = True
                writes, calls = [], []
                def journal(path, data):
                    writes.append(copy.deepcopy(data))
                    if len(writes) in failed_writes: raise OSError('attempt journal unavailable')
                    persistent.durable_save(path, data)
                def run(command, timeout=30):
                    calls.append((command, timeout))
                    return subprocess.CompletedProcess(command, 0, 'stopped', '')
                with patch('research.acquisition.run_acquisition_campaign.durable_save', journal), \
                     patch('research.acquisition.run_acquisition_campaign.run', run):
                    with self.assertRaisesRegex(RuntimeError, 'evidence incomplete'): owner.stop()
                self.assertEqual(calls, [(['logman', 'stop', 'exact-owned-session', '-ets'], 5)])
                self.assertEqual(len(writes), 2)
                self.assertTrue(owner.attempted)
                self.assertEqual((Path(d) / 'trace-stop.txt').read_text(), 'stopped')
                if failed_writes == {1}:
                    record = json.loads((Path(d) / 'trace-stop-attempts.json').read_text())
                    self.assertFalse(record['stopped'])
                    self.assertFalse(record['evidence_complete'])
                    self.assertEqual(record['attempts'][0]['state'], 'stopped')

    def test_trace_retry_continues_without_journal_and_preserves_command_failure(self):
        from research.acquisition.run_acquisition_campaign import TraceOwner
        for success_at in (2, None):
            with self.subTest(success_at=success_at), tempfile.TemporaryDirectory() as d:
                owner = TraceOwner('exact-owned-session', Path(d)); owner.attempted = True
                calls = []
                command_error = RuntimeError('original stop command failure')
                def run(command, timeout=30):
                    calls.append(command)
                    if len(calls) != success_at: raise command_error
                    return subprocess.CompletedProcess(command, 0, 'stopped', '')
                with patch('research.acquisition.run_acquisition_campaign.durable_save', side_effect=OSError('disk')) as journal, \
                     patch('research.acquisition.run_acquisition_campaign.run', run):
                    with self.assertRaises(RuntimeError) as caught: owner.stop()
                self.assertEqual(len(calls), success_at or 3)
                self.assertEqual(journal.call_count, 2 * len(calls))
                self.assertTrue(all(command == ['logman', 'stop', 'exact-owned-session', '-ets'] for command in calls))
                self.assertTrue(owner.attempted)
                if success_at: self.assertIn('evidence incomplete', str(caught.exception))
                else: self.assertIs(caught.exception, command_error)


if __name__ == '__main__': unittest.main()

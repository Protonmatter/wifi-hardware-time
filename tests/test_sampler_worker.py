"""Worker/process ownership using real control files and a deterministic fake kernel."""
import contextlib
import copy
import json
from pathlib import Path
import tempfile
import unittest
import threading
import sys
import uuid
from unittest.mock import patch

from test_tsf_sampler import Clock, Kernel
from research.tsf import tsf_sampler as api
from research.tsf.sampler_worker import Journal, serve
from research.acquisition.persistent_sampler import (CONTROL_SCHEMA, ControllerOwner, PersistentClient, durable_save)


class Mutex:
    locked = contextlib.nullcontext


class WorkerTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Native Windows mutex/file-sharing verification')
    def test_windows_concurrent_control_and_snapshot_io_uses_real_mutex(self):
        from research.acquisition.campaign_admission import Admission
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            path = folder / 'control.json'
            control = dict(schema=CONTROL_SCHEMA, session_id='s', controller_pid=1, state='ready', sequence=0, heartbeat=1.0)
            durable_save(path, control)
            admission = Admission(path, 'Local\\WifiSamplerTest-' + uuid.uuid4().hex, create=True)
            journal = Journal(folder, folder / 'marker.json', admission)
            owner = ControllerOwner(path, admission, lambda: True, lambda: 1.0, 's', 1)
            client = PersistentClient(folder, folder, 7, 10_000_000, {}, folder / 'marker.json',
                                      folder / 'unfinished', None, None, None)
            client.admission = admission
            snapshot = dict(session=dict(state='READY', failed=False, request_count=0), request=None)
            journal(snapshot)
            errors, reads = [], []
            barrier = threading.Barrier(2)
            def writer():
                try:
                    barrier.wait(5)
                    for number in range(1, 201):
                        with admission.locked():
                            durable_save(path, control)
                        snapshot['session']['request_count'] = number
                        journal(snapshot)
                except BaseException as error: errors.append(error)
            def reader():
                try:
                    barrier.wait(5)
                    for _ in range(300):
                        owner.check()
                        reads.append(client.read_snapshot(folder / 'sampler-session.json')['request_count'])
                except BaseException as error: errors.append(error)
            first, second = threading.Thread(target=writer), threading.Thread(target=reader)
            try:
                first.start(); second.start()
                first.join(15); second.join(15)
                self.assertFalse(first.is_alive() or second.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(len(reads), 300)
                self.assertEqual(reads, sorted(reads))
                self.assertEqual(client.read_snapshot(folder / 'sampler-session.json')['request_count'], 200)
                self.assertFalse((folder / 'marker.json').exists())
            finally:
                first.join(); second.join()
                admission.close()

    def test_unchanged_indefinite_drain_does_not_grow_journal(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            journal = Journal(folder, folder / 'marker.json')
            snapshot = dict(session=dict(state='QUARANTINED_DRAIN_PENDING', failed=True,
                            failure='deadline', session_id='s', outstanding_operations=1), request=None)
            for _ in range(100):
                journal(snapshot)
            self.assertEqual(len((folder / 'sampler-events.jsonl').read_text().splitlines()), 1)
            snapshot['session']['state'] = 'STOPPED'
            snapshot['session']['outstanding_operations'] = 0
            journal(snapshot)
            self.assertEqual(len((folder / 'sampler-events.jsonl').read_text().splitlines()), 2)

    def test_owner_and_snapshot_reads_serialize_against_writers(self):
        # Holding a real Windows read handle across an atomic replace is unsafe.
        # Prove writers cannot enter the shared critical section during either reader.
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            lock = threading.RLock()
            class Admission:
                def locked(self): return lock
            admission = Admission()
            client = PersistentClient(folder, folder, 7, 10_000_000, {}, folder / 'marker', folder / 'unfinished',
                                      None, None, None)
            client.admission = admission
            path = client.path
            durable_save(path, dict(schema=CONTROL_SCHEMA, session_id=client.session_id,
                                    controller_pid=1, state='ready', sequence=0, heartbeat=1.0))
            owner = ControllerOwner(path, admission, lambda: True, lambda: 1.0, client.session_id, 1)
            self.assertTrue(hasattr(client, 'read_snapshot'), 'snapshot reader must share the admission mutex')
            for read in (owner.check, lambda: client.read_snapshot(path)):
                opened, release, entering, entered = (threading.Event() for _ in range(4))
                errors = []
                original = Path.read_text
                def held_read(target, *args, **kwargs):
                    if target == path and threading.current_thread().name == 'sampler-reader':
                        with target.open('r', encoding='utf-8') as stream:
                            opened.set()
                            if not release.wait(2): raise RuntimeError('test release timeout')
                            return stream.read()
                    return original(target, *args, **kwargs)
                def reader():
                    try: read()
                    except BaseException as error: errors.append(error)
                def writer():
                    entering.set()
                    with admission.locked(): entered.set()
                with patch.object(Path, 'read_text', held_read):
                    first = threading.Thread(target=reader, name='sampler-reader')
                    second = threading.Thread(target=writer)
                    try:
                        first.start()
                        self.assertTrue(opened.wait(2))
                        second.start()
                        self.assertTrue(entering.wait(2))
                        self.assertFalse(entered.wait(0.05), 'writer entered while read handle was open')
                    finally:
                        release.set()
                        first.join(2)
                        if second.ident is not None: second.join(2)
                self.assertFalse(errors)
                self.assertTrue(entered.is_set())

    def test_concurrent_quarantine_writers_do_not_share_temporary_file(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'marker.json'
            replace = os.replace
            nested = [False]
            def race(source, destination):
                if not nested[0]:
                    nested[0] = True
                    durable_save(path, dict(reason='worker failure'))
                replace(source, destination)
            with patch('research.acquisition.persistent_sampler.os.replace', race):
                durable_save(path, dict(reason='controller failure'))
            self.assertEqual(json.loads(path.read_text())['reason'], 'controller failure')
            self.assertEqual(list(Path(d).iterdir()), [path])

    def test_worker_retains_pending_resources_across_controller_death_and_disk_failure(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            path, marker = folder / 'control.json', folder / 'quarantine.json'
            clock = Clock()
            live = [True]
            owner = ControllerOwner(path, Mutex(), lambda: live[0], clock.monotonic, 's', 1)
            durable_save(path, dict(schema=CONTROL_SCHEMA, session_id='s', controller_pid=1,
                                    state='permitted', sequence=1, heartbeat=clock.monotonic()))
            kernel = Kernel(api, clock)
            kernel.initial = api.IoResult(False, 997, 0, b'')
            snapshots = []
            journal = Journal(folder, marker)
            failed_once = [False]
            def sink(snapshot):
                snapshots.append(copy.deepcopy(snapshot))
                if snapshot['session']['outstanding_operations']:
                    live[0] = False
                    if not failed_once[0]:
                        failed_once[0] = True
                        raise OSError('synthetic disk failure')
                journal(snapshot)
            poll_count = [0]
            original_poll = kernel.poll
            def poll(operation, ms):
                poll_count[0] += 1
                if poll_count[0] <= 20:
                    self.assertEqual((kernel.releases, kernel.closes), (0, 0))
                if poll_count[0] == 21:
                    kernel.polls.append(api.PollResult(0, api.IoResult(False, 995, 0, b'')))
                return original_poll(operation, ms)
            kernel.poll = poll
            identity = lambda: dict(identity_validated=True, driver_sha256=api.QUALIFIED_SHA256,
                                    interface_index=7, adapter_guid='fixture', mac_hex='020000000001')
            sampler = api.Sampler(kernel, clock, owner, sink, identity, session_id='s')
            self.assertEqual(serve(sampler, owner, clock), 1)
            self.assertEqual((kernel.submissions, kernel.releases, kernel.closes), (1, 1, 1))
            self.assertEqual(poll_count[0], 21)
            self.assertTrue(marker.exists())
            final = json.loads((folder / 'sampler-session.json').read_text())
            self.assertTrue(final['failed'])
            self.assertTrue(final['handle_closed'])
            self.assertEqual(final['outstanding_operations'], 0)
            self.assertTrue(any(row['session']['state'] == 'QUARANTINED_DRAIN_PENDING' for row in snapshots))

    def test_worker_rejects_dead_controller_before_open(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            clock = Clock()
            owner = ControllerOwner(folder / 'control.json', Mutex(), lambda: False, clock.monotonic, 's', 1)
            kernel = Kernel(api, clock)
            sampler = api.Sampler(kernel, clock, owner, Journal(folder, folder / 'marker.json'),
                                  lambda: self.fail('identity lookup after controller death'), session_id='s')
            self.assertEqual(serve(sampler, owner, clock), 1)
            self.assertEqual((kernel.opens, kernel.submissions), (0, 0))

    def test_close_timeout_retains_worker_and_writes_quarantine(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            clock = Clock()
            class Process:
                pid = 123
                def poll(self): return None
                def kill(self): raise AssertionError('worker killed')
                def terminate(self): raise AssertionError('worker terminated')
            class Admission(Mutex):
                def close(self): pass
            client = PersistentClient(folder, folder, 7, clock.frequency, {}, folder / 'marker.json',
                                      folder / 'in-progress.json', clock, None, None)
            client.process, client.admission = Process(), Admission()
            durable_save(client.path, dict(schema=CONTROL_SCHEMA, session_id=client.session_id,
                                           controller_pid=1, state='submitted', sequence=1, heartbeat=clock.monotonic()))
            with patch('research.acquisition.persistent_sampler.time.monotonic', clock.monotonic), \
                 patch('research.acquisition.persistent_sampler.time.sleep', clock.sleep):
                self.assertFalse(client.close(failed=True))
            marker = json.loads((folder / 'marker.json').read_text())
            self.assertTrue(marker['still_running'])
            self.assertEqual(marker['worker_pid'], 123)
            self.assertEqual(json.loads(client.path.read_text())['state'], 'abort')


if __name__ == '__main__':
    unittest.main()

"""Controller failure paths with injected processes, clock and trace; no device I/O."""
import contextlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from research.acquisition import run_bound_campaign as bound
from research.acquisition import run_acquisition_campaign as acquisition
from research.acquisition import bss_reader as bss


class BoundCleanupTests(unittest.TestCase):
    def execute(self, root, *, condition='load', stop_error=False, kill_error=False, report_ticks=3000):
        now, actions = [1.0], []

        class Clock:
            frequency = 10_000_000
            def now(self): return round(now[0] * self.frequency)
        clock = Clock()

        class Trace:
            def __init__(self, session, folder): self.folder = folder
            def start(self, options): (self.folder / 'tsf.etl').write_bytes(b'')
            def stop(self): actions.append('trace-stopped')

        class Observer:
            ready, association = True, 'fixture'
            def __init__(self, *args): self.waits = 0
            def pump(self, gate): pass
            def wait(self, seconds, gate):
                self.waits += 1
                now[0] += seconds
                if condition == 'load' and self.waits == 2:
                    raise RuntimeError('injected collection failure')
            def close(self, gate): actions.append('observer-closed')

        class Reader:
            def __init__(self, *args): pass
            def read(self, qpc): raise bss.CacheEntryUnavailable(0)
            def close(self): actions.append('reader-closed')

        class Worker:
            returncode = None
            def wait(self, timeout):
                actions.append('worker-wait')
                if self.returncode is None:
                    raise subprocess.TimeoutExpired('injected workload', timeout)
            def poll(self): return self.returncode
            def kill(self):
                actions.append('worker-kill')
                if kill_error:
                    raise OSError('injected kill failure')
                self.returncode = -1

        def submit(root, folder, number, index, frequency, observer, gate):
            lower = clock.now()
            for row in (
                dict(kind='command', raw_timestamp=lower + 1, action=4, vdev=0),
                dict(kind='report', raw_timestamp=lower + report_ticks, tsf_raw=lower // 10, vdev=0),
                dict(kind='soc_timer', raw_timestamp=lower + report_ticks + 1, soc_timer_raw=0, g_tsf_raw=0),
                dict(kind='delay', raw_timestamp=lower + report_ticks + 2, tsf_delay_raw=(lower // 10) & 0xffffffff, vdev=0),
            ):
                gate.consume(row)
            return dict(qpc_request_before=lower, qpc_request_completed=lower + 10, success=True,
                        firmware_action=4, handle_closed=True, cancel_requested=False)

        touch = Path.touch
        def touch_stop(path, *args, **kwargs):
            if stop_error and path.name == 'workload-stop':
                raise OSError('injected stop file failure')
            return touch(path, *args, **kwargs)

        def identity(index):
            actions.append('identity-checked')
            return dict(InterfaceGuid='fixture')

        args = bound.parse(['--if-index', '7', '--condition', condition, '--duration-s', '60', '--spacing-s', '0.5'])
        with contextlib.ExitStack() as stack:
            for obj, name, value in (
                (bound.time, 'monotonic', lambda: now[0]),
                (bound.time, 'sleep', lambda seconds: now.__setitem__(0, now[0] + seconds)),
                (acquisition, 'ROOT', root), (acquisition, 'TraceOwner', Trace),
                (acquisition, 'Observer', Observer), (acquisition, 'identity', identity),
                (acquisition, 'same_identity', lambda *args: None), (bss, 'BssReader', Reader),
                (bound.subprocess, 'Popen', lambda *args, **kwargs: Worker()),
                (bound, 'finalize', lambda *args: None), (bound, 'submit', submit), (Path, 'touch', touch_stop),
            ):
                stack.enter_context(patch.object(obj, name, value))
            code = bound._execute(args, clock, dict(InterfaceGuid='fixture'), {}, root / 'marker.json')
        result_path = next((root / 'artifacts').rglob('run-result.json'))
        return code, actions, json.loads(result_path.read_text())

    def test_workload_cleanup_errors_do_not_skip_trace_observer_or_persistence(self):
        for stop_error, kill_error in ((True, False), (False, True), (True, True)):
            with self.subTest(stop_error=stop_error, kill_error=kill_error), tempfile.TemporaryDirectory() as d:
                code, actions, result = self.execute(Path(d), stop_error=stop_error, kill_error=kill_error)
                self.assertEqual(code, 1)
                self.assertFalse(result['success'])
                self.assertTrue((Path(d) / 'marker.json').exists())
                for action in ('reader-closed', 'worker-wait', 'worker-kill', 'trace-stopped',
                               'observer-closed', 'identity-checked'):
                    self.assertIn(action, actions)
                self.assertEqual(result['error'], 'injected collection failure')
                self.assertTrue(result['cleanup_errors'])
                if kill_error:
                    self.assertTrue(any('termination' in error for error in result['cleanup_errors']))

    def test_late_reports_count_as_losses_and_stop_at_the_live_budget(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, result = self.execute(Path(d), condition='idle', report_ticks=30_000)
            self.assertEqual(code, 1)
            self.assertEqual(result['request_count'], 100)
            self.assertEqual(result['own_losses_live'], 100)
            self.assertEqual(result['error'], 'Own-loss budget exceeded')

    def test_report_at_acceptance_boundary_does_not_count_as_a_loss(self):
        with tempfile.TemporaryDirectory() as d:
            code, _, result = self.execute(Path(d), condition='idle', report_ticks=20_000)
            self.assertEqual(code, 0)
            self.assertEqual(result['own_losses_live'], 0)


if __name__ == '__main__':
    unittest.main()

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contextlib
import json
import tempfile
import unittest
from unittest.mock import patch

from research.acquisition.run_bound_campaign import parse


class FlushExecuteTests(unittest.TestCase):
    def run_campaign(self, flush_fails):
        """Drive _execute with fakes only; no adapter, trace session or ETW API is touched."""
        import research.acquisition.run_bound_campaign as bound
        import research.acquisition.run_acquisition_campaign as acquisition
        import research.acquisition.bss_reader as bss
        import research.acquisition.etw_flush as etw_flush
        import research.acquisition.persistent_sampler as api
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            now, submitted, constructed = [1.0], [], []

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
                def pulse(self): self.observer.pump(self.gate)
                def submit(self, number):
                    submitted.append(now[0])
                    self.gate.consume(dict(kind='command', raw_timestamp=clock.now(), action=4, vdev=0))
                    self.observer.report_due = now[0] + 1.96
                    return dict(sequence=number, qpc_request_before=clock.now(), qpc_request_completed=clock.now(),
                                success=True, schema='wht/persistent-tsf-request-v1')
                def close(self, failed=False): return not failed

            class FakeFlusher:
                def __init__(self, session, now_fn, **kwargs):
                    self.kwargs = kwargs
                    constructed.append(self)
                    self.count = 0
                def flush(self):
                    if flush_fails:
                        raise RuntimeError('fake flush failure')
                    self.count += 1
                    return dict(source='fake-flusher', status=0, ordinal=self.count)

            def identity(index):
                now[0] += 1.1
                return dict(InterfaceGuid='fixture')

            args = parse(['--if-index', '7', '--condition', 'idle', '--duration-s', '60',
                          '--sampler', 'persistent', '--etw-flush'])
            marker = root / 'marker.json'
            with contextlib.ExitStack() as stack:
                for obj, name, value in ((bound.time, 'monotonic', lambda: now[0]),
                                         (bound.time, 'sleep', lambda seconds: now.__setitem__(0, now[0] + seconds)),
                                         (acquisition, 'ROOT', root), (acquisition, 'TraceOwner', Trace),
                                         (acquisition, 'Observer', Observer), (acquisition, 'identity', identity),
                                         (acquisition, 'same_identity', lambda *a: None),
                                         (bss, 'BssReader', Reader), (api, 'PersistentClient', Client),
                                         (etw_flush, 'TraceFlusher', FakeFlusher),
                                         (bound, 'finalize', lambda *a: None)):
                    stack.enter_context(patch.object(obj, name, value))
                code = bound._execute(args, clock, dict(InterfaceGuid='fixture'), {}, marker)
            rows = []
            for schedule in (root / 'artifacts').rglob('sampler-schedule.jsonl'):
                rows += [json.loads(line) for line in schedule.read_text().splitlines()]
            return code, rows, marker.exists(), constructed

    def test_flushes_are_recorded_in_every_schedule_row(self):
        code, rows, marker_written, constructed = self.run_campaign(flush_fails=False)
        self.assertEqual(code, 0)
        self.assertFalse(marker_written)
        self.assertEqual(len(constructed), 1)
        self.assertIs(constructed[0].kwargs.get('live'), True)  # recorded only; the fake never goes live
        self.assertGreater(len(rows), 10)
        for row in rows:
            self.assertIsInstance(row['etw_flushes'], list)
            self.assertTrue(row['etw_flushes'])
            self.assertTrue(all(receipt['source'] == 'fake-flusher' for receipt in row['etw_flushes']))

    def test_failed_flush_stops_the_campaign_and_quarantines(self):
        code, rows, marker_written, constructed = self.run_campaign(flush_fails=True)
        self.assertEqual(len(constructed), 1)
        self.assertNotEqual(code, 0)
        self.assertTrue(marker_written)


if __name__ == '__main__':
    unittest.main()

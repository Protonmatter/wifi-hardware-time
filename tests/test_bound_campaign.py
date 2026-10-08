import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess
import tempfile
import unittest
import json
import threading
from research.acquisition.run_bound_campaign import (DOWNLOAD_URLS, TRACE_BUFFER_OPTIONS, BoundGate, CampaignBusy,
                                                     CampaignLock, CampaignQuarantined, admit, complete,
                                                     download_stalled, finalize, in_progress_path, loss_budget_exceeded,
                                                     parse, persist_outcome, remaining_sleep)

HEADER = dict(kind='header', clock_type=1, perf_frequency_hz=10_000_000, events_lost=0, buffers_lost=0)
LIVE = [dict(kind='report', raw_timestamp=10, vdev=0, tsf_raw=1, received_qpc=99)]


class Decoded:
    def __init__(self, stdout: str):
        self.stdout = stdout


def decoder(stdout=None, error=None):
    def run_fn(command, timeout):
        if error is not None:
            raise error
        return Decoded(stdout)
    return run_fn

ROOT = Path(__file__).resolve().parents[1]


class BoundCampaignTests(unittest.TestCase):
    def test_gate_retains_foreign_groups_without_failing(self):
        gate = BoundGate()
        for record in (dict(kind='report', raw_timestamp=10, vdev=0, tsf_raw=1),
                       dict(kind='soc_timer', raw_timestamp=11, soc_timer_raw=1, g_tsf_raw=0),
                       dict(kind='delay', raw_timestamp=12, vdev=0, tsf_delay_raw=0)):
            gate.consume(record)
        self.assertIsNone(gate.reason)
        self.assertEqual(len(gate.timing), 3)
        self.assertTrue(gate.report_after(10))
        self.assertFalse(gate.report_after(11))

    def test_gate_still_fails_on_trace_loss_and_malformed_timing(self):
        gate = BoundGate()
        with self.assertRaises(ValueError):
            gate.consume(dict(kind='health', health_source='controller_query', query_status=0,
                              events_lost=1, log_buffers_lost=0, real_time_buffers_lost=0))
        with self.assertRaises(ValueError):
            BoundGate().consume(dict(kind='report', raw_timestamp='x'))

    def test_live_report_presence_rejects_late_foreign_and_ambiguous_records(self):
        lower, hz = 1_000_000, 10_000_000
        command = dict(kind='command', raw_timestamp=lower + 1, vdev=0, action=4)
        report = dict(kind='report', raw_timestamp=lower + 20_000, vdev=0)
        for events, accepted in (
            ([command, report], True),
            ([command, dict(report, raw_timestamp=lower + 20_001)], False),
            ([report], False),
            ([command, dict(report, vdev=1)], False),
            ([command, report, report], False),
            ([command, dict(command, action=3), report], False),
        ):
            with self.subTest(events=events):
                gate = BoundGate()
                for event in events:
                    gate.consume(event)
                self.assertEqual(gate.report_in_window(lower, hz), accepted)

    def test_spacing_and_loss_budget(self):
        self.assertEqual(remaining_sleep(2.0, 0.5), 1.5)
        self.assertEqual(remaining_sleep(2.0, 3.0), 0.0)
        self.assertFalse(loss_budget_exceeded(5, 50))
        self.assertFalse(loss_budget_exceeded(1, 100))
        self.assertTrue(loss_budget_exceeded(2, 100))

    def test_download_stall_detection_fails_fast(self):
        self.assertFalse(download_stalled(last_progress=100.0, now=159.9))
        self.assertTrue(download_stalled(last_progress=100.0, now=160.1))
        self.assertTrue(all(url.startswith('https://') for url in DOWNLOAD_URLS))
        self.assertGreaterEqual(len(DOWNLOAD_URLS), 2)

    def test_trace_buffers_are_explicit_and_bounded(self):
        size_kb = int(TRACE_BUFFER_OPTIONS[TRACE_BUFFER_OPTIONS.index('-bs') + 1])
        maximum = int(TRACE_BUFFER_OPTIONS[TRACE_BUFFER_OPTIONS.index('-nb') + 2])
        self.assertLessEqual(size_kb * maximum, 32 * 1024)  # at most 32 MiB of trace buffers
        # ETL files are whole buffers flushed every second, so file growth scales with buffer size;
        # 8 KB measured about 12 MiB/min, while 256 KB measured about 103 MiB/min.
        self.assertEqual(size_kb, 8)
        self.assertGreaterEqual(int(TRACE_BUFFER_OPTIONS[TRACE_BUFFER_OPTIONS.index('-nb') + 1]), 256)

    def test_finalize_turns_every_decoding_failure_into_a_reason(self):
        good = json.dumps(HEADER) + '\n' + json.dumps({k: v for k, v in LIVE[0].items() if k != 'received_qpc'}) + '\n'
        cases = dict(decoder_error=decoder(error=RuntimeError('decoder exit 1')),
                     timeout=decoder(error=subprocess.TimeoutExpired('decode', 600)),
                     empty=decoder(''), malformed=decoder('not json\n'),
                     no_header=decoder(json.dumps(LIVE[0]) + '\n'),
                     lossy=decoder(json.dumps(dict(HEADER, events_lost=3)) + '\n'),
                     mismatch=decoder(json.dumps(HEADER) + '\n'))
        with tempfile.TemporaryDirectory() as d:
            for name, run_fn in cases.items():
                with self.subTest(case=name):
                    reason = finalize(Path('decode.exe'), Path(d) / 'tsf.etl', Path(d) / 'raw.jsonl', LIVE, run_fn)
                    self.assertIsInstance(reason, str)
            self.assertIsNone(finalize(Path('decode.exe'), Path(d) / 'tsf.etl', Path(d) / 'raw.jsonl', LIVE, decoder(good)))

    def test_failure_persists_marker_and_result(self):
        with tempfile.TemporaryDirectory() as d:
            folder, marker = Path(d) / 'run', Path(d) / 'marker.json'
            folder.mkdir()
            persist_outcome(folder, marker, dict(condition='idle'), 'Post-collection decoding failed: boom', lambda: 'now')
            self.assertTrue(marker.exists())
            result = json.loads((folder / 'run-result.json').read_text(encoding='utf-8'))
            self.assertFalse(result['success'])
            self.assertIn('decoding failed', result['error'])
            persist_outcome(folder, Path(d) / 'other.json', dict(condition='idle'), None, lambda: 'now')
            self.assertFalse((Path(d) / 'other.json').exists())

    @unittest.skipUnless(sys.platform == 'win32', 'Named mutexes are Windows-only')
    def test_adapter_lock_excludes_a_second_controller(self):
        guid = '{01234567-89AB-CDEF-0123-456789ABCDEF}'
        outcome = {}

        def contend(key):
            try:
                with CampaignLock(guid, namespace='Local'):
                    outcome[key] = 'acquired'
            except CampaignBusy:
                outcome[key] = 'busy'

        with CampaignLock(guid, namespace='Local'):
            thread = threading.Thread(target=contend, args=('while_held',))
            thread.start(); thread.join()
        thread = threading.Thread(target=contend, args=('after_release',))
        thread.start(); thread.join()
        self.assertEqual(outcome, dict(while_held='busy', after_release='acquired'))

    @unittest.skipUnless(sys.platform == 'win32', 'Named mutexes are Windows-only')
    @unittest.skipUnless(sys.platform == 'win32', 'Named mutexes are Windows-only')
    def test_abandoned_lock_stays_quarantined_on_every_later_attempt(self):
        guid = '{89ABCDEF-0123-4567-89AB-CDEF01234567}'
        with tempfile.TemporaryDirectory() as d:
            marker, state = Path(d) / 'marker.json', Path(d)
            holder = CampaignLock(guid, namespace='Local')
            thread = threading.Thread(target=holder.acquire)  # The owning thread exits without releasing.
            thread.start(); thread.join()
            for attempt in (1, 2):
                with self.subTest(attempt=attempt), self.assertRaises(CampaignBusy):
                    admit(guid, marker, state, namespace='Local')
            self.assertTrue(marker.exists())
            holder.close_handle()

    @unittest.skipUnless(sys.platform == 'win32', 'Named mutexes are Windows-only')
    def test_killed_controller_blocks_admission_until_reconciled(self):
        guid = '{13572468-0123-4567-89AB-CDEF01234567}'
        with tempfile.TemporaryDirectory() as d:
            marker, state = Path(d) / 'marker.json', Path(d)
            child = ('import os, sys; from pathlib import Path; sys.path.insert(0, sys.argv[1]); '
                     'from research.acquisition.run_bound_campaign import admit; '
                     'admit(sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), namespace="Local"); os._exit(3)')
            result = subprocess.run([sys.executable, '-c', child, str(ROOT), guid, str(marker), str(state)], timeout=60)
            self.assertEqual(result.returncode, 3)  # Exited while holding the lock, without cleanup.
            for attempt in (1, 2):
                with self.subTest(attempt=attempt), self.assertRaises(CampaignQuarantined):
                    admit(guid, marker, state, namespace='Local')
            in_progress_path(state, guid).unlink()  # Explicit reconciliation.
            lock = admit(guid, marker, state, namespace='Local')
            complete(lock, in_progress_path(state, guid))
            self.assertFalse(in_progress_path(state, guid).exists())

    @unittest.skipUnless(sys.platform == 'win32', 'Named mutexes are Windows-only')
    def test_marker_blocks_admission_and_releases_the_lock(self):
        guid = '{24681357-0123-4567-89AB-CDEF01234567}'
        with tempfile.TemporaryDirectory() as d:
            marker, state = Path(d) / 'marker.json', Path(d)
            marker.write_text('{}', encoding='utf-8')
            with self.assertRaises(CampaignQuarantined):
                admit(guid, marker, state, namespace='Local')
            marker.unlink()
            complete(admit(guid, marker, state, namespace='Local'), in_progress_path(state, guid))

    def test_argument_limits(self):
        base = ['--if-index', '5', '--condition', 'idle']
        self.assertEqual(parse(base).duration_s, 3600)
        self.assertFalse(parse(base).execute)
        for extra in (['--duration-s', '30'], ['--duration-s', '3601'], ['--spacing-s', '0.1']):
            with self.subTest(extra=extra), self.assertRaises(SystemExit):
                parse(base + extra)
        with self.assertRaises(SystemExit):
            parse(['--condition', 'idle'])

    def test_cli_help_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'research/acquisition/run_bound_campaign.py'), '--help'],
                                    cwd=directory, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()

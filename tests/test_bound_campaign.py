import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess
import tempfile
import unittest
from research.acquisition.run_bound_campaign import (DOWNLOAD_URLS, TRACE_BUFFER_OPTIONS, BoundGate, download_stalled,
                                                     loss_budget_exceeded, parse, remaining_sleep)

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

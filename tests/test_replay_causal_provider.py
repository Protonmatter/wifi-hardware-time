import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import subprocess
import tempfile
import unittest
from research.clock_models.causal_provider import AvailableSample, CausalProvider
from research.clock_models.replay_causal_provider import SCREENING_LABEL, arrival_map, availability, replay
from research.clock_models.sample_screen import Sample

ROOT = Path(__file__).resolve().parents[1]
HZ = 10_000_000


def tsf(qpc):
    return 9_000_000_000 + qpc // 10


class ReplayTests(unittest.TestCase):
    def test_arrival_uses_the_last_required_record_and_request_completion(self):
        live = [dict(kind='command', raw_timestamp=100, received_qpc=5_000),
                dict(kind='report', raw_timestamp=3_000, received_qpc=6_000),
                dict(kind='soc_timer', raw_timestamp=3_001, received_qpc=6_100),
                dict(kind='delay', raw_timestamp=3_002, received_qpc=6_200)]
        delay_seen = arrival_map(live)
        self.assertEqual(delay_seen, {3_000: 6_200})
        item = Sample(1, 9_000_000, 0, 0, 3_000)
        self.assertEqual(availability(item, 'causal-arrival', delay_seen, {1: 4_000}), 6_200)
        self.assertEqual(availability(item, 'causal-arrival', delay_seen, {1: 9_999}), 9_999)
        self.assertEqual(availability(item, 'causal-etw', delay_seen, {1: 9_999}), 3_001)
        with self.assertRaises(ValueError):
            availability(Sample(2, 1, 0, 0, 7_000), 'causal-arrival', delay_seen, {2: 1})

    def test_exact_state_durations_on_a_known_timeline(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 1_004_001)
        second = AvailableSample(2, tsf(301_004_000), 301_000_000, 301_004_000, 301_004_001)  # 30 s gap
        start, end = 0, 400_000_000
        result = replay([('accepted', None, first), ('accepted', None, second)], HZ, start, end)
        probe = CausalProvider(HZ)
        probe.ingest(first)
        stale_one = probe.stale_from_qpc()
        probe.ingest(second)
        stale_two = probe.stale_from_qpc()
        expected_tracking = (stale_one - first.available_qpc) + (stale_two - second.available_qpc)
        durations = result['durations_ticks']
        self.assertEqual(Fraction(durations['acquiring']), first.available_qpc - start)
        self.assertEqual(Fraction(durations['tracking']), expected_tracking)
        self.assertEqual(sum(Fraction(v) for v in durations.values()), end - start)
        self.assertEqual(result['incompatible'], [])
        self.assertEqual(result['label'], SCREENING_LABEL)
        self.assertIn('conditions', result)

    def test_incompatible_sample_is_reported_and_latches(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 1_004_001)
        bad = AvailableSample(2, tsf(21_004_000) + 50_000, 21_000_000, 21_004_000, 21_004_001)
        result = replay([('accepted', None, first), ('accepted', None, bad)], HZ, 0, 40_000_000)
        self.assertEqual([item['sequence'] for item in result['incompatible']], [2])
        self.assertGreater(Fraction(result['durations_ticks']['invalid']), 0)

    def test_rejected_samples_are_checked_but_not_ingested(self):
        first = AvailableSample(1, tsf(1_004_000), 1_000_000, 1_004_000, 1_004_001)
        stale = AvailableSample(2, first.tsf_us, 21_000_000, 21_004_000, 21_004_001)
        good = AvailableSample(3, tsf(41_004_000), 41_000_000, 41_004_000, 41_004_001)
        result = replay([('accepted', None, first), ('rejected', 'stale_or_inconsistent', stale),
                         ('accepted', None, good)], HZ, 0, 50_000_000)
        self.assertEqual(result['rejected_checked'], [dict(sequence=2, reason='stale_or_inconsistent', compatible=False)])
        self.assertEqual(result['incompatible'], [])
        self.assertEqual(result['samples_ingested'], 2)

    def test_cli_help_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'research/clock_models/replay_causal_provider.py'), '--help'],
                                    cwd=directory, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()

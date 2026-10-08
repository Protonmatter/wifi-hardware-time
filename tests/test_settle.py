import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.causal_provider import AvailableSample
from research.clock_models.settle import settle, settle_replay

HZ = 10_000_000
NOMINAL = Fraction(1, 10)


class VariableClock:
    """Rate alternates between +150 and -150 ppm every 0.7 s: inside the 200 ppm limit."""

    rates = (NOMINAL * Fraction(1_000_150, 1_000_000), NOMINAL * Fraction(999_850, 1_000_000))

    def at(self, qpc):
        value, t, k = Fraction(9_000_000_000), 0, 0
        while t + 7_000_000 <= qpc:
            value += self.rates[k % 2] * 7_000_000
            t += 7_000_000
            k += 1
        return value + self.rates[k % 2] * (qpc - t)


def series(clock_at, count=12, spacing=30_000_000, delay=20_000_000):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        capture = lower + 700 + (i * 991) % 3_000
        out.append(AvailableSample(i + 1, int(clock_at(capture)), lower, lower + 4_000, lower + 4_001 + delay))
    return out


class SettleTests(unittest.TestCase):
    def test_settled_interval_contains_a_variable_rate_clock(self):
        clock = VariableClock()
        samples = series(clock.at)
        now = samples[-1].available_qpc
        for event in range(samples[0].upper_qpc + 1, samples[-1].lower_qpc, 7_654_321):
            result = settle(event, samples, now, HZ)
            self.assertEqual(result.state, 'settled')
            self.assertLessEqual(result.low_us, clock.at(event))
            self.assertGreaterEqual(result.high_us, clock.at(event))
            self.assertLess(result.half_width_us, 1_000)

    def test_affine_estimate_contains_a_constant_rate_clock(self):
        clock_at = lambda q: 9_000_000_000 + q * NOMINAL * Fraction(999_956, 1_000_000)  # -44 ppm
        samples = series(clock_at, count=20, spacing=20_000_000)
        event = samples[9].upper_qpc + 7_000_000
        result = settle(event, samples, samples[-1].available_qpc, HZ)
        self.assertIsNotNone(result.affine_low_us)
        self.assertLessEqual(result.affine_low_us, clock_at(event))
        self.assertGreaterEqual(result.affine_high_us, clock_at(event))
        self.assertLessEqual(result.affine_half_width_us, result.half_width_us)

    def test_pending_until_the_bracketing_sample_arrives(self):
        samples = series(lambda q: 9_000_000_000 + q * NOMINAL)
        event = samples[3].upper_qpc + 10_000_000
        before = settle(event, samples, samples[4].available_qpc - 1, HZ)
        self.assertEqual(before.state, 'pending')
        self.assertIsNone(before.low_us)
        after = settle(event, samples, samples[4].available_qpc, HZ)
        self.assertEqual(after.state, 'settled')
        self.assertEqual(after.settled_at_qpc, samples[4].available_qpc)

    def test_unbracketed_before_the_first_sample(self):
        samples = series(lambda q: 9_000_000_000 + q * NOMINAL)
        self.assertEqual(settle(0, samples, samples[-1].available_qpc, HZ).state, 'unbracketed')

    def test_inconsistent_neighbours_are_reported(self):
        samples = series(lambda q: 9_000_000_000 + q * NOMINAL, count=3)
        bad = AvailableSample(2, samples[1].tsf_us + 50_000, samples[1].lower_qpc, samples[1].upper_qpc,
                              samples[1].available_qpc)
        result = settle(samples[0].upper_qpc + 5_000_000, [samples[0], bad, samples[2]], samples[2].available_qpc, HZ)
        self.assertEqual(result.state, 'inconsistent')

    def test_replay_summarises_waits_and_bounds(self):
        samples = series(lambda q: 9_000_000_000 + q * NOMINAL, count=10, spacing=30_000_000, delay=20_000_000)
        summary = settle_replay(samples, HZ, step_qpc=5_000_000)
        self.assertEqual(summary['states'].get('settled'), summary['events'])
        self.assertGreater(summary['wait_s']['max'], 2.0)  # at least the 2 s delivery delay
        self.assertLess(summary['wait_s']['max'], 5.1)     # at most one spacing plus the delay
        self.assertLess(summary['half_width_us']['max'], 1_000)
        self.assertEqual(summary['sub_millisecond_share'], 1.0)


    def test_settle_mode_on_a_run_folder(self):
        import json, tempfile
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_analyze_bound_run import write_run
        from research.clock_models.replay_causal_provider import replay_run
        with tempfile.TemporaryDirectory() as a:
            folder = Path(a)
            write_run(folder, count=10)
            live = []
            for line in (folder / 'raw-timing.jsonl').read_text(encoding='utf-8').splitlines():
                record = json.loads(line)
                if record['kind'] in ('report', 'soc_timer', 'delay'):
                    live.append(dict(record, received_qpc=record['raw_timestamp'] + 15_000_000))
            (folder / 'live-observer.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in live), encoding='utf-8')
            result = replay_run(folder, 'settle')
            self.assertEqual(result['settle']['states'], {'settled': result['settle']['events']})
            self.assertGreater(result['settle']['wait_s']['median'], 1.5)
            self.assertIn('worst_settled_half_width_any_instant_us', result)
            self.assertIn('conditioned on offline sample screening', result['label'])


if __name__ == '__main__':
    unittest.main()

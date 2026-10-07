import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import subprocess
import tempfile
import unittest
from research.clock_models.analyze_bound_run import analyze_run, evaluate, frequency

ROOT = Path(__file__).resolve().parents[1]
HZ = 10_000_000


def write_run(folder: Path, count=40, foreign=0, success=True):
    records, receipts, beacons = [dict(kind='header', clock_type=1, perf_frequency_hz=HZ, events_lost=0, buffers_lost=0)], [], []
    for i in range(count):
        lower = 10_000_000 + i * 20_000_000
        receipts.append(dict(sequence=i + 1, qpc_request_before=lower, qpc_request_completed=lower + 500, success=True,
                             handle_closed=True, cancel_requested=False, firmware_action=4))
        tsf = 7_000_000_000 + (lower + 3_000) // 10
        records += [dict(kind='command', raw_timestamp=lower + 500, vdev=0, action=4),
                    dict(kind='report', raw_timestamp=lower + 3_000, vdev=0, tsf_raw=tsf),
                    dict(kind='soc_timer', raw_timestamp=lower + 3_001, soc_timer_raw=5, g_tsf_raw=0),
                    dict(kind='delay', raw_timestamp=lower + 3_002, vdev=0, tsf_delay_raw=(tsf - 5) & 0xffffffff)]
        if i % 10 == 5:
            beacons.append(dict(qpc_before=lower + 10_000_000, qpc_after=lower + 10_001_000,
                                ap_tsf_us=7_000_000_000 + lower // 10 - 30_000))
    for j in range(foreign):
        ts = 10_000_000 + j * 20_000_000 + 10_000_000
        records += [dict(kind='report', raw_timestamp=ts, vdev=0, tsf_raw=1), dict(kind='soc_timer', raw_timestamp=ts + 1, soc_timer_raw=1, g_tsf_raw=0),
                    dict(kind='delay', raw_timestamp=ts + 2, vdev=0, tsf_delay_raw=0)]
    (folder / 'raw-timing.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
    (folder / 'requests.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in receipts), encoding='utf-8')
    (folder / 'beacons.jsonl').write_text(''.join(json.dumps(b) + '\n' for b in beacons), encoding='utf-8')
    (folder / 'run-result.json').write_text(json.dumps(dict(success=success, qpc_frequency_hz=HZ)), encoding='utf-8')


class AnalyzeTests(unittest.TestCase):
    def test_clean_run_passes_every_criterion(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write_run(Path(a)); write_run(Path(b), foreign=3)
            idle, load = analyze_run(Path(a)), analyze_run(Path(b))
            self.assertEqual(idle['screen']['accepted_count'], 40)
            self.assertEqual(load['screen']['foreign_groups'], 3)
            verdict = evaluate(idle, load)
            self.assertTrue(verdict['passed'], verdict)

    def test_stopped_run_fails(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write_run(Path(a)); write_run(Path(b), success=False)
            verdict = evaluate(analyze_run(Path(a)), analyze_run(Path(b)))
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['load']['run_completed'])

    def test_beacon_received_during_the_cache_call_is_not_a_violation(self):
        with tempfile.TemporaryDirectory() as a:
            write_run(Path(a))
            lower = 10_000_000 + 20 * 20_000_000
            station_at_call_start = 7_000_000_000 + (lower + 10_000_000) // 10
            beacon = dict(qpc_before=lower + 10_000_000, qpc_after=lower + 10_100_000,  # a 10 ms call
                          ap_tsf_us=station_at_call_start + 3_000)  # stamped 3 ms into the call
            (Path(a) / 'beacons.jsonl').write_text(json.dumps(beacon) + '\n', encoding='utf-8')
            check = analyze_run(Path(a))['analysis']['beacon_check']
            self.assertEqual((check['checked'], check['violations']), (1, 0))

    def test_frequency_accepts_bundle_decimal_strings_only(self):
        self.assertEqual(frequency('10000000'), 10_000_000)
        self.assertEqual(frequency(10_000_000), 10_000_000)
        for bad in ('10e6', '-1', 0, 1.5, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                frequency(bad)

    def test_cli_help_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'research/clock_models/analyze_bound_run.py'), '--help'],
                                    cwd=directory, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()

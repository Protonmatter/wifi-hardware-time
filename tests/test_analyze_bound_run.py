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


SPACING = 200_000_000  # 20 s between requests: 181 requests span 3,600 s with 3 samples per 60 s span


def write_run(folder: Path, count=181, foreign=0, success=True, condition='idle', duration_s=3600, session=None,
              workload=None, recorded_span=None):
    records, receipts, beacons = [dict(kind='header', clock_type=1, perf_frequency_hz=HZ, events_lost=0, buffers_lost=0)], [], []
    for i in range(count):
        lower = 10_000_000 + i * SPACING
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
        ts = 10_000_000 + j * SPACING + 100_000_000
        records += [dict(kind='report', raw_timestamp=ts, vdev=0, tsf_raw=1), dict(kind='soc_timer', raw_timestamp=ts + 1, soc_timer_raw=1, g_tsf_raw=0),
                    dict(kind='delay', raw_timestamp=ts + 2, vdev=0, tsf_delay_raw=0)]
    (folder / 'raw-timing.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
    (folder / 'requests.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in receipts), encoding='utf-8')
    (folder / 'beacons.jsonl').write_text(''.join(json.dumps(b) + '\n' for b in beacons), encoding='utf-8')
    result = dict(success=success, qpc_frequency_hz=HZ, condition=condition, duration_s=duration_s)
    if recorded_span is not None:
        result.update(collection_start_qpc=recorded_span[0], collection_end_qpc=recorded_span[1])
    (folder / 'run-result.json').write_text(json.dumps(result), encoding='utf-8')
    (folder / 'session.json').write_text(json.dumps(dict(SessionName=session or f'WifiBound-{folder.name}')), encoding='utf-8')
    if condition == 'load':
        load = dict(stop_requested=True, download_stalled=False, downloaded_bytes=10**10, wall_seconds=3605.0,
                    hash_operations=9_000_000)
        load.update(workload or {})
        (folder / 'workload.json').write_text(json.dumps(load), encoding='utf-8')


def pair(a: str, b: str, **load_options):
    write_run(Path(a))
    write_run(Path(b), condition='load', **load_options)
    return analyze_run(Path(a)), analyze_run(Path(b))


class AnalyzeTests(unittest.TestCase):
    def test_clean_run_passes_every_criterion(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            idle, load = pair(a, b, foreign=3)
            self.assertEqual(idle['screen']['accepted_count'], 181)
            self.assertEqual(load['screen']['foreign_groups'], 3)
            verdict = evaluate(idle, load)
            self.assertTrue(verdict['passed'], verdict)

    def test_stopped_run_fails(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            verdict = evaluate(*pair(a, b, success=False))
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['load']['run_completed'])

    def test_verdict_is_always_conditional(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            verdict = evaluate(*pair(a, b))
            self.assertTrue(verdict['passed'])
            self.assertFalse(verdict['physical_bound_proven'])
            self.assertTrue(any(c.startswith('causal capture') for c in verdict['conditional_on']))
            self.assertTrue(any(c.startswith('affine clock') for c in verdict['conditional_on']))

    def test_constant_capture_delay_is_not_detectable(self):
        # Known limitation: every TSF captured 5 ms before its window still passes screening, so a pass is
        # conditional on causal capture rather than proof of it.
        with tempfile.TemporaryDirectory() as a:
            write_run(Path(a))
            path = Path(a) / 'raw-timing.jsonl'
            records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
            for record in records:
                if record['kind'] == 'report':
                    record['tsf_raw'] -= 5_000
                if record['kind'] == 'delay':
                    record['tsf_delay_raw'] = (record['tsf_delay_raw'] - 5_000) & 0xffffffff
            path.write_text(''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
            self.assertEqual(analyze_run(Path(a))['screen']['accepted_count'], 181)

    def test_truncated_trace_labelled_as_an_hour_fails(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write_run(Path(a), count=5, duration_s=3600)  # about 80 s of requests, declared as an hour
            write_run(Path(b), condition='load')
            verdict = evaluate(analyze_run(Path(a)), analyze_run(Path(b)))
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['idle']['collection_span_at_least_3540s'])

    def test_trace_must_cover_the_collection_interval(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write_run(Path(a))
            path = Path(a) / 'raw-timing.jsonl'
            records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
            cut = 10_000_000 + 90 * SPACING
            kept = [r for r in records if r['kind'] == 'header' or r['raw_timestamp'] < cut]
            path.write_text(''.join(json.dumps(r) + '\n' for r in kept), encoding='utf-8')
            write_run(Path(b), condition='load')
            verdict = evaluate(analyze_run(Path(a)), analyze_run(Path(b)))
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['idle']['trace_covers_collection'])

    def test_recorded_collection_interval_must_match_the_receipts(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write_run(Path(a), recorded_span=(0, 10**12))
            write_run(Path(b), condition='load')
            verdict = evaluate(analyze_run(Path(a)), analyze_run(Path(b)))
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['idle']['recorded_interval_consistent'])

    def test_same_run_supplied_twice_fails(self):
        with tempfile.TemporaryDirectory() as a:
            write_run(Path(a))
            run = analyze_run(Path(a))
            verdict = evaluate(run, run)
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['distinct_runs'])

    def test_recorded_condition_must_match_its_role(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            idle, load = pair(a, b)
            verdict = evaluate(load, idle)
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['idle']['condition_recorded'])

    def test_short_run_is_diagnostic_only(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            write_run(Path(a), duration_s=80)
            write_run(Path(b), condition='load')
            verdict = evaluate(analyze_run(Path(a)), analyze_run(Path(b)))
            self.assertFalse(verdict['passed'])
            self.assertFalse(verdict['idle']['duration_at_least_3600s'])

    def test_load_requires_a_completed_progressing_workload(self):
        for workload in (dict(download_stalled=True), dict(downloaded_bytes=0), dict(stop_requested=False),
                         dict(downloaded_bytes=1), dict(hash_operations=0), dict(wall_seconds=1.0)):
            with self.subTest(workload=workload), tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
                verdict = evaluate(*pair(a, b, workload=workload))
                self.assertFalse(verdict['passed'])
                self.assertFalse(verdict['load']['workload_completed'])

    def test_beacon_received_during_the_cache_call_is_not_a_violation(self):
        with tempfile.TemporaryDirectory() as a:
            write_run(Path(a))
            lower = 10_000_000 + 20 * SPACING
            station_at_call_start = 7_000_000_000 + (lower + 100_000_000) // 10
            beacon = dict(qpc_before=lower + 100_000_000, qpc_after=lower + 100_100_000,  # a 10 ms call
                          ap_tsf_us=station_at_call_start + 3_000)  # stamped 3 ms into the call
            (Path(a) / 'beacons.jsonl').write_text(json.dumps(beacon) + '\n', encoding='utf-8')
            check = analyze_run(Path(a))['analysis']['beacon_check']
            self.assertEqual((check['checked'], check['violations']), (1, 0))

    def test_non_qpc_trace_clock_is_rejected(self):
        for clock_type in (2, 3, None):
            with self.subTest(clock_type=clock_type), tempfile.TemporaryDirectory() as a:
                write_run(Path(a))
                path = Path(a) / 'raw-timing.jsonl'
                lines = path.read_text(encoding='utf-8').splitlines()
                header = json.loads(lines[0])
                if clock_type is None:
                    del header['clock_type']
                else:
                    header['clock_type'] = clock_type
                path.write_text('\n'.join([json.dumps(header)] + lines[1:]) + '\n', encoding='utf-8')
                with self.assertRaises(ValueError):
                    analyze_run(Path(a))

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

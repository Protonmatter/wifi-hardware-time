# TSF-to-host bound: implementation plan

This plan turns the [TSF-to-host bound design](2026-10-07-tsf-host-bound-design.md) into tested code, a preview on already saved samples, and a gated live campaign. Offline analysis comes first so the method is checked against existing evidence before any new private request. Live runs happen only after every module passes its tests and the user approves the first run.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** prove, for this laptop and driver build, a worst-case bound below 1,000 us on the station TSF at any QPC instant, using action-4 report windows.

**Architecture:** pure, exact-arithmetic analysis modules under `research/clock_models/` (window polygon bound, sample screening, SoC domain test, beacon check, run analyzer), one read-only public WLAN reader, and one long-run controller under `research/acquisition/` that reuses the existing observer, trace owner and probe admission protocol. Live records are retained unadmitted and classified offline.

**Tech stack:** Python 3.11+ standard library (`fractions`, `ctypes`, `unittest`), existing MSVC-built native helpers (`live_observer.exe`, `decode_tsf_etl.exe`), Windows `logman`.

**Spec:** [docs/overview/2026-10-07-tsf-host-bound-design.md](2026-10-07-tsf-host-bound-design.md)

## Contents

- [Global constraints](#global-constraints)
- [File structure](#file-structure)
- [Task 0: Spec amendments from saved-data checks](#task-0-spec-amendments-from-saved-data-checks)
- [Task 1: Window polygon bound](#task-1-window-polygon-bound)
- [Task 2: Sample screening](#task-2-sample-screening)
- [Task 3: SoC domain test](#task-3-soc-domain-test)
- [Task 4: Beacon consistency check](#task-4-beacon-consistency-check)
- [Task 5: Run analyzer and pass/fail evaluation](#task-5-run-analyzer-and-passfail-evaluation)
- [Task 6: Preview on saved campaign samples](#task-6-preview-on-saved-campaign-samples)
- [Task 7: Public BSS cache reader](#task-7-public-bss-cache-reader)
- [Task 8: Long-run campaign controller](#task-8-long-run-campaign-controller)
- [Task 9: Phase 0 hex-dump caller check](#task-9-phase-0-hex-dump-caller-check)
- [Task 10: Gated live runs](#task-10-gated-live-runs)
- [Task 11: Results and publication](#task-11-results-and-publication)

## Global constraints

- Driver gate: ARM64 `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115` (`QUALIFIED_SHA256`).
- Firmware action: **4 only**. Never 3, 5 or 6 in new live code.
- One request in flight. Report timeout 5 seconds. Request spacing nominal 2 seconds, never below 0.5 seconds.
- Acceptance window: a report counts for a request only if its trace timestamp is within **2,000 us** of `qpc_request_before`.
- Rate prior: TSF-to-QPC rate within **200 ppm** of nominal.
- Freshness band: **100 ppm**, plus 1 us rounding, with no fitted values.
- Sliding analysis spans: **60 s**, step **10 s**, at least **3** samples.
- Pass criteria (both idle and load): maximum proven error below 1,000 us; feasible coverage at least 90%; rejected samples at most 1%; estimated misattributed samples below 0.05; beacon check with at least one check and zero violations.
- Trace: WlanLogger `{bb6f5b93-635c-47be-816f-e895e77064a8}`, keywords `0x2000000000000010`, level `0xff`, QPC clock, one sequential file, run stops at 250 MiB.
- Live runs need Administrator rights and explicit `--execute`; any stop writes `artifacts/bound-campaign-quarantine.json`, which the tool never removes.
- Exact arithmetic (`fractions.Fraction`) for every bound; floats only for display.
- Raw captures stay under `artifacts/` (git-ignored) and the private evidence repository. Never commit captures, BSSIDs or SSIDs.
- No em-dashes in authored files. Commits carry no AI attribution trailer.
- Tests use `unittest`; run with `python -m unittest discover -s tests`.

## File structure

| File | Responsibility |
|---|---|
| `research/clock_models/bracket_bound.py` (new) | Exact feasible (rate, offset) polygon from windows; proven half-width; sliding spans; coverage |
| `research/clock_models/sample_screen.py` (new) | Group trace records; structural attribution; own-loss and foreign counts; freshness filter; misattribution estimate |
| `research/clock_models/soc_domain_test.py` (new) | Fixed-rate containment and rate-interval test for the SoC counter |
| `research/clock_models/beacon_consistency.py` (new) | Coarse "beacon not stamped after its read" check |
| `research/clock_models/analyze_bound_run.py` (new) | CLI: legacy preview, run analysis, idle/load evaluation |
| `research/acquisition/bss_reader.py` (new) | Read-only `WlanGetNetworkBssList` reader for the connected BSS |
| `research/acquisition/run_bound_campaign.py` (new) | Long-run live controller and load workload |
| `tests/test_bracket_bound.py`, `tests/test_sample_screen.py`, `tests/test_soc_domain.py`, `tests/test_beacon_consistency.py`, `tests/test_analyze_bound_run.py`, `tests/test_bss_reader.py`, `tests/test_bound_campaign.py` (new) | Unit tests per module |
| `docs/clock-models/tsf-host-bound-preview.md` (new) | Preview results on saved samples |
| `docs/acquisition/tsf-host-bound-results.md` (new, Task 11) | Live campaign results |

---

### Task 0: Spec amendments from saved-data checks

Saved-data checks on 2026-10-07 changed four design details. Record them before code depends on them.

**Files:**
- Modify: `docs/overview/2026-10-07-tsf-host-bound-design.md`

- [ ] **Step 1: Add the findings section after section 3's SoC paragraph list**

Insert a new subsection at the end of section 3:

```markdown
**Saved-data checks (2026-10-07, read-only, campaign `ecfaed68f20e`):**

- All 18 saved action-4 windows measured 214 to 740 us; the IOCTL itself returned in about 50 us.
- Scan-triggered reports carry vdev 0, the same as ours, so vdev cannot filter them. Every one of our requests logs a `command` record (action 4, vdev 0) before its report group, and the six scan-triggered groups in three scan captures had none. Attribution therefore uses the command record and a 2,000 us acceptance window.
- The SoC counter fails the fixed 10-ticks-per-unit test by 365 to 688 us within about 24 seconds in all six mixed runs, so SoC is unlikely to share the QPC domain.
- Without a limit on the rate, a single window leaves the polygon unbounded. A 200 ppm physical prior on the TSF-to-QPC rate is added; the fitted rates in saved runs lie between about -66 and -23 ppm.
```

- [ ] **Step 2: Update the attribution row's residual-risk formula**

Replace `own-loss count x foreign-report rate x mean window width` with `own-loss count x foreign-report rate x the 2,000 us acceptance window`.

- [ ] **Step 3: Add the quantization rule to section 2**

After the inequality block in section 2, add:

```markdown
TSF is an integer microsecond counter and QPC an integer tick counter, so the implemented constraint widens each window by one TSF microsecond and one QPC tick: `T_i - r * (U_i + 1 tick) <= c <= T_i + 1 - r * L_i`.
```

- [ ] **Step 4: Regenerate the index, test and commit**

```bash
python research/evidence/build_knowledge_index.py --write
python -m unittest discover -s tests
git add docs
git commit -m "Record saved-data checks and quantization in TSF bound design"
```

Expected: tests `OK`.

---

### Task 1: Window polygon bound

**Files:**
- Create: `research/clock_models/bracket_bound.py`
- Test: `tests/test_bracket_bound.py`

**Interfaces:**
- Produces: `Window(tsf_us: int, lower_qpc: int, upper_qpc: int)`; `window_bound(windows: list[Window], qpc_hz: int, rate_prior_ppm: int = 200) -> Bound`; `Bound.feasible: bool`, `Bound.predict(qpc: int) -> tuple[Fraction, Fraction]`, `Bound.half_width_us(qpc: int) -> Fraction`, `Bound.max_half_width_us(start_qpc: int, end_qpc: int) -> Fraction`, `Bound.rate_ppm() -> tuple[Fraction, Fraction]`; `SpanReport(start_qpc, end_qpc, sample_count, feasible, max_half_width_us, bound)`; `sliding_bounds(windows, qpc_hz, span_s=60, step_s=10, min_samples=3, rate_prior_ppm=200) -> list[SpanReport]`; `coverage(reports, start_qpc, end_qpc) -> Fraction`.

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.bracket_bound import Window, window_bound, sliding_bounds, coverage

HZ = 10_000_000
RATE = Fraction(999_960, 10_000_000)  # station TSF 40 ppm slow, in us per QPC tick


def truth(qpc):
    return 5_000_000_000 + qpc * RATE


def windows(count, spacing=20_000_000, jump_after=None, jump_us=0):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        capture = lower + 1_000 + (i * 37) % 1_500
        tsf = int(truth(capture)) + (jump_us if jump_after is not None and i > jump_after else 0)
        out.append(Window(tsf, lower, lower + 5_000))
    return out


class BracketBoundTests(unittest.TestCase):
    def test_truth_lies_inside_every_prediction(self):
        sample = windows(10)
        bound = window_bound(sample, HZ)
        self.assertTrue(bound.feasible)
        for qpc in range(sample[0].lower_qpc, sample[-1].upper_qpc, 7_777_777):
            low, high = bound.predict(qpc)
            self.assertLessEqual(low, truth(qpc))
            self.assertGreaterEqual(high, truth(qpc))

    def test_single_window_half_width_is_exact(self):
        bound = window_bound([Window(5_000_000, 0, 10_000)], HZ)
        expected = (1 + Fraction(100_020, 1_000_000) * 10_001) / 2
        self.assertEqual(bound.half_width_us(5_000), expected)

    def test_inconsistent_windows_are_infeasible(self):
        bound = window_bound([Window(1_000, 0, 100), Window(51_000, 10_000, 10_100)], HZ)
        self.assertFalse(bound.feasible)
        with self.assertRaises(ValueError):
            bound.predict(0)

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(ValueError):
            Window(1, 10, 5)
        with self.assertRaises(ValueError):
            window_bound([], HZ)
        with self.assertRaises(ValueError):
            window_bound([Window(1, 0, 1)], 0)

    def test_rate_interval_contains_truth(self):
        low, high = window_bound(windows(10), HZ).rate_ppm()
        self.assertLessEqual(low, -40)
        self.assertGreaterEqual(high, -40)

    def test_sliding_spans_are_sub_millisecond_and_cover_the_run(self):
        sample = windows(30)
        spans = sliding_bounds(sample, HZ)
        self.assertTrue(spans)
        self.assertTrue(all(s.feasible and s.max_half_width_us < 1000 for s in spans))
        self.assertGreaterEqual(coverage(spans, sample[0].lower_qpc, sample[-1].upper_qpc), Fraction(9, 10))

    def test_tsf_jump_makes_spans_infeasible(self):
        spans = sliding_bounds(windows(30, jump_after=14, jump_us=5_000), HZ)
        self.assertTrue(any(not s.feasible for s in spans))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -p test_bracket_bound.py -v`
Expected: `ModuleNotFoundError: No module named 'research.clock_models.bracket_bound'`.

- [ ] **Step 3: Implement the module**

```python
"""Exact worst-case TSF bounds from host QPC windows. Offline analysis only.

Each Window states that the firmware captured the reported TSF somewhere in
[lower_qpc, upper_qpc]. Sample screening checks that condition separately; this
module only computes what follows if it holds. All arithmetic is exact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations

US_PER_S = 1_000_000
RATE_PRIOR_PPM = 200  # Physical prior on |TSF rate / QPC rate - 1|.


@dataclass(frozen=True)
class Window:
    tsf_us: int
    lower_qpc: int
    upper_qpc: int

    def __post_init__(self) -> None:
        if any(type(v) is not int for v in (self.tsf_us, self.lower_qpc, self.upper_qpc)):
            raise ValueError('Window fields must be integers')
        if not 0 <= self.tsf_us < 1 << 64 or not 0 <= self.lower_qpc <= self.upper_qpc < 1 << 63:
            raise ValueError('Window outside range or reversed')


@dataclass(frozen=True)
class Bound:
    """Feasible (rate, offset) polygon; rate in TSF us per QPC tick from origin_qpc."""
    feasible: bool
    sample_count: int
    qpc_hz: int
    origin_qpc: int
    origin_tsf: int
    vertices: tuple[tuple[Fraction, Fraction], ...]

    def predict(self, qpc: int) -> tuple[Fraction, Fraction]:
        if not self.feasible:
            raise ValueError('No feasible model')
        x = qpc - self.origin_qpc
        values = [rate * x + offset for rate, offset in self.vertices]
        return self.origin_tsf + min(values), self.origin_tsf + max(values)

    def half_width_us(self, qpc: int) -> Fraction:
        low, high = self.predict(qpc)
        return (high - low) / 2

    def max_half_width_us(self, start_qpc: int, end_qpc: int) -> Fraction:
        # The half-width is convex in time, so its maximum on an interval is at an end.
        return max(self.half_width_us(start_qpc), self.half_width_us(end_qpc))

    def rate_ppm(self) -> tuple[Fraction, Fraction]:
        rates = [rate * self.qpc_hz / US_PER_S for rate, _ in self.vertices]
        return (min(rates) - 1) * US_PER_S, (max(rates) - 1) * US_PER_S


def window_bound(windows: list[Window], qpc_hz: int, rate_prior_ppm: int = RATE_PRIOR_PPM) -> Bound:
    if type(qpc_hz) is not int or qpc_hz <= 0:
        raise ValueError('QPC frequency must be a positive integer')
    if type(rate_prior_ppm) is not int or not 0 < rate_prior_ppm < 10_000:
        raise ValueError('Rate prior must be 1 to 9999 ppm')
    if not windows or any(type(w) is not Window for w in windows):
        raise ValueError('Require at least one Window')
    origin_qpc, origin_tsf = windows[0].lower_qpc, windows[0].tsf_us
    # Integer TSF and QPC: widen by one TSF microsecond and one QPC tick.
    rows = [(w.tsf_us - origin_tsf, w.lower_qpc - origin_qpc, w.upper_qpc + 1 - origin_qpc) for w in windows]
    nominal = Fraction(US_PER_S, qpc_hz)
    r_low = nominal * (US_PER_S - rate_prior_ppm) / US_PER_S
    r_high = nominal * (US_PER_S + rate_prior_ppm) / US_PER_S
    # Offset limits per window: y - r*upper <= c <= y + 1 - r*lower.
    lines = [(y, upper) for y, lower, upper in rows] + [(y + 1, lower) for y, lower, upper in rows]

    def inside(rate: Fraction, offset: Fraction) -> bool:
        return r_low <= rate <= r_high and all(
            y - rate * upper <= offset <= y + 1 - rate * lower for y, lower, upper in rows)

    candidates = {(r, y - r * x) for r in (r_low, r_high) for y, x in lines}
    for (y1, x1), (y2, x2) in combinations(lines, 2):
        if x1 != x2:
            rate = Fraction(y1 - y2, x1 - x2)
            candidates.add((rate, y1 - rate * x1))
    vertices = tuple(sorted(v for v in candidates if inside(*v)))
    return Bound(bool(vertices), len(windows), qpc_hz, origin_qpc, origin_tsf, vertices)


@dataclass(frozen=True)
class SpanReport:
    start_qpc: int
    end_qpc: int
    sample_count: int
    feasible: bool
    max_half_width_us: Fraction | None
    bound: Bound = field(repr=False, compare=False)


def sliding_bounds(windows: list[Window], qpc_hz: int, span_s: int = 60, step_s: int = 10,
                   min_samples: int = 3, rate_prior_ppm: int = RATE_PRIOR_PPM) -> list[SpanReport]:
    if type(span_s) is not int or type(step_s) is not int or not 0 < step_s <= span_s:
        raise ValueError('Require integer seconds with 0 < step_s <= span_s')
    if type(min_samples) is not int or min_samples < 1:
        raise ValueError('min_samples must be positive')
    if not windows:
        return []
    if any(b.lower_qpc <= a.lower_qpc for a, b in zip(windows, windows[1:])):
        raise ValueError('Windows must be strictly ordered by lower_qpc')
    span, step = span_s * qpc_hz, step_s * qpc_hz
    reports, seen, start = [], set(), windows[0].lower_qpc
    while start <= windows[-1].lower_qpc:
        members = [w for w in windows if start <= w.lower_qpc and w.upper_qpc <= start + span]
        if len(members) >= min_samples:
            key = (members[0].lower_qpc, members[-1].upper_qpc)
            if key not in seen:
                seen.add(key)
                bound = window_bound(members, qpc_hz, rate_prior_ppm)
                width = bound.max_half_width_us(*key) if bound.feasible else None
                reports.append(SpanReport(key[0], key[1], len(members), bound.feasible, width, bound))
        start += step
    return reports


def coverage(reports: list[SpanReport], start_qpc: int, end_qpc: int) -> Fraction:
    """Share of [start_qpc, end_qpc] covered by feasible spans."""
    if end_qpc <= start_qpc:
        raise ValueError('Empty interval')
    covered, cursor = 0, start_qpc
    for low, high in sorted((r.start_qpc, r.end_qpc) for r in reports if r.feasible):
        low, high = max(low, cursor), min(high, end_qpc)
        if high > low:
            covered += high - low
            cursor = high
    return Fraction(covered, end_qpc - start_qpc)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -p test_bracket_bound.py -v`
Expected: 7 tests `OK`.

- [ ] **Step 5: Commit**

```bash
git add research/clock_models/bracket_bound.py tests/test_bracket_bound.py
git commit -m "Add exact window polygon bound for TSF-to-QPC tracking"
```

---

### Task 2: Sample screening

**Files:**
- Create: `research/clock_models/sample_screen.py`
- Test: `tests/test_sample_screen.py`

**Interfaces:**
- Consumes: decoded trace records as emitted by `decode_tsf_etl.exe` / `live_observer.exe`: `command{raw_timestamp, vdev, action}`, `report{raw_timestamp, vdev, tsf_raw}`, `soc_timer{raw_timestamp, soc_timer_raw, g_tsf_raw}`, `delay{raw_timestamp, vdev, tsf_delay_raw}`; probe receipts from `qualcomm_probe.py` (`qpc_request_before`, `success`, `handle_closed`, `cancel_requested`, `firmware_action`).
- Produces: `TIMING_KINDS`, `MAX_WINDOW_US = 2000`, `LISTEN_TIMEOUT_S = 5`; `Request(sequence: int, lower_qpc: int, succeeded: bool)`; `request_from_receipt(sequence: int, receipt: dict) -> Request`; `Sample(sequence: int, tsf_us: int, soc_raw: int, lower_qpc: int, upper_qpc: int)`; `freshness_filter(samples: list[Sample], qpc_hz: int) -> tuple[list[Sample], list[tuple[int, str]]]`; `Screen(accepted, rejected, foreign_groups, foreign_commands, own_losses, duration_s, expected_misattributed)`; `screen(records: list[dict], requests: list[Request], qpc_hz: int) -> Screen`.

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.sample_screen import Request, Sample, freshness_filter, request_from_receipt, screen

HZ = 10_000_000
SPACING = 20_000_000  # two seconds


def tsf_at(qpc):
    return 7_000_000_000 + qpc // 10


def group(ts, tsf, vdev=0, soc=1_000_000):
    return [dict(kind='report', raw_timestamp=ts, vdev=vdev, tsf_raw=tsf),
            dict(kind='soc_timer', raw_timestamp=ts + 1, soc_timer_raw=soc, g_tsf_raw=0),
            dict(kind='delay', raw_timestamp=ts + 2, vdev=vdev, tsf_delay_raw=(tsf - soc) & 0xffffffff)]


def ours(lower, report_at=3_000, tsf=None, command=True):
    records = [dict(kind='command', raw_timestamp=lower + 500, vdev=0, action=4)] if command else []
    return records + group(lower + report_at, tsf if tsf is not None else tsf_at(lower + report_at))


def requests(count):
    return [Request(i + 1, 10_000_000 + i * SPACING, True) for i in range(count)]


class ScreenTests(unittest.TestCase):
    def test_one_owned_group_per_window_is_accepted(self):
        reqs = requests(3)
        records = [r for q in reqs for r in ours(q.lower_qpc)]
        result = screen(records, reqs, HZ)
        self.assertEqual([s.sequence for s in result.accepted], [1, 2, 3])
        self.assertEqual((result.foreign_groups, result.own_losses), (0, 0))
        self.assertEqual(result.accepted[0].upper_qpc, reqs[0].lower_qpc + 3_000)

    def test_foreign_group_in_gap_is_counted_not_fatal(self):
        reqs = requests(3)
        records = [r for q in reqs for r in ours(q.lower_qpc)]
        records += group(reqs[0].lower_qpc + 10_000_000, tsf_at(reqs[0].lower_qpc + 10_000_000))
        result = screen(records, reqs, HZ)
        self.assertEqual(len(result.accepted), 3)
        self.assertEqual(result.foreign_groups, 1)

    def test_second_report_inside_acceptance_window_rejects_sample(self):
        reqs = requests(2)
        records = [r for q in reqs for r in ours(q.lower_qpc)]
        records += group(reqs[0].lower_qpc + 1_000, tsf_at(reqs[0].lower_qpc + 1_000))
        result = screen(records, reqs, HZ)
        self.assertIn((1, 'multiple_reports_in_window'), result.rejected)

    def test_own_loss_late_report_and_misattribution_estimate(self):
        reqs = requests(3)
        records = ours(reqs[0].lower_qpc) + ours(reqs[1].lower_qpc, report_at=5_000_000)
        records += [dict(kind='command', raw_timestamp=reqs[2].lower_qpc + 500, vdev=0, action=4)]
        records += group(reqs[2].lower_qpc + 60_000_000, tsf_at(reqs[2].lower_qpc + 60_000_000))  # after every listen interval
        result = screen(records, reqs, HZ)
        self.assertIn((2, 'late_report'), result.rejected)
        self.assertIn((3, 'own_loss'), result.rejected)
        self.assertEqual(result.own_losses, 2)
        self.assertEqual(result.foreign_groups, 1)
        expected = 2 * Fraction(1) / result.duration_s * Fraction(2_000, 1_000_000)
        self.assertEqual(result.expected_misattributed, expected)

    def test_missing_command_record_rejects_sample(self):
        reqs = requests(1)
        result = screen(ours(reqs[0].lower_qpc, command=False), reqs, HZ)
        self.assertEqual(result.rejected, ((1, 'command_record_missing_or_extra'),))

    def test_stale_repeat_is_rejected_by_freshness(self):
        reqs = requests(2)
        first = ours(reqs[0].lower_qpc)
        stale = ours(reqs[1].lower_qpc, tsf=first[1]['tsf_raw'])
        result = screen(first + stale, reqs, HZ)
        self.assertEqual([s.sequence for s in result.accepted], [1])
        self.assertIn((2, 'stale_or_inconsistent'), result.rejected)

    def test_vdev_mismatch_and_bad_delay_are_rejected(self):
        reqs = requests(2)
        bad_vdev = [dict(kind='command', raw_timestamp=reqs[0].lower_qpc + 500, vdev=1, action=4)]
        bad_vdev += group(reqs[0].lower_qpc + 3_000, tsf_at(reqs[0].lower_qpc + 3_000))
        bad_delay = ours(reqs[1].lower_qpc)
        bad_delay[3]['tsf_delay_raw'] += 1
        result = screen(bad_vdev + bad_delay, reqs, HZ)
        self.assertIn((1, 'vdev_mismatch'), result.rejected)
        self.assertIn((2, 'delay_arithmetic'), result.rejected)

    def test_malformed_group_raises(self):
        reqs = requests(1)
        records = ours(reqs[0].lower_qpc)
        del records[2]
        with self.assertRaises(ValueError):
            screen(records, reqs, HZ)

    def test_receipt_conversion_admits_only_action_four(self):
        receipt = dict(qpc_request_before=5, success=True, handle_closed=True, cancel_requested=False, firmware_action=4)
        self.assertEqual(request_from_receipt(1, receipt), Request(1, 5, True))
        with self.assertRaises(ValueError):
            request_from_receipt(1, dict(receipt, firmware_action=3))

    def test_freshness_filter_on_samples(self):
        good = [Sample(i, tsf_at(i * SPACING + 3_000), 0, i * SPACING, i * SPACING + 3_000) for i in range(3)]
        accepted, rejected = freshness_filter(good, HZ)
        self.assertEqual(len(accepted), 3)
        self.assertEqual(rejected, [])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -p test_sample_screen.py -v`
Expected: `ModuleNotFoundError: No module named 'research.clock_models.sample_screen'`.

- [ ] **Step 3: Implement the module**

```python
"""Classify TSF trace records into owned action-4 samples. Offline, fail-closed.

Our request logs a command record (action 4) before its report group; scans and
other activity produce report groups without one. Classification is structural
and never proves the firmware identity of a report. A report counts for a
request only inside the acceptance window after the request's host QPC.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from fractions import Fraction

TIMING_KINDS = ('command', 'report', 'soc_timer', 'delay')
MAX_WINDOW_US = 2_000
LISTEN_TIMEOUT_S = 5
FRESHNESS_PPM = 100
US_PER_S = 1_000_000


@dataclass(frozen=True)
class Request:
    sequence: int
    lower_qpc: int
    succeeded: bool


@dataclass(frozen=True)
class Sample:
    sequence: int
    tsf_us: int
    soc_raw: int
    lower_qpc: int
    upper_qpc: int


@dataclass(frozen=True)
class Screen:
    accepted: tuple[Sample, ...]
    rejected: tuple[tuple[int, str], ...]
    foreign_groups: int
    foreign_commands: int
    own_losses: int
    duration_s: Fraction
    expected_misattributed: Fraction


def request_from_receipt(sequence: int, receipt: dict) -> Request:
    lower = receipt.get('qpc_request_before')
    if type(lower) is not int:
        raise ValueError('Receipt lacks integer qpc_request_before')
    if receipt.get('firmware_action') != 4:
        raise ValueError('Only action-4 receipts are admitted')
    succeeded = (receipt.get('success') is True and receipt.get('handle_closed') is True
                 and not receipt.get('cancel_requested'))
    return Request(sequence, lower, succeeded)


def _events(records: list[dict]) -> list[dict]:
    timing = [r for r in records if r.get('kind') in TIMING_KINDS]
    if any(type(r.get('raw_timestamp')) is not int for r in timing):
        raise ValueError('Timing record without integer raw_timestamp')
    timing.sort(key=lambda r: r['raw_timestamp'])  # Stable: ties keep emission order.
    events, index = [], 0
    while index < len(timing):
        record = timing[index]
        if record['kind'] == 'command':
            events.append(dict(type='command', ts=record['raw_timestamp'], vdev=record['vdev'], action=record['action']))
            index += 1
            continue
        if record['kind'] != 'report' or [r['kind'] for r in timing[index + 1:index + 3]] != ['soc_timer', 'delay']:
            raise ValueError('Report group is not report, soc_timer, delay in order')
        report, soc, delay = timing[index:index + 3]
        tsf, soc_raw = report['tsf_raw'], soc['soc_timer_raw']
        delay_ok = ((tsf - soc_raw) & 0xffffffff) == delay['tsf_delay_raw'] and delay['vdev'] == report['vdev']
        events.append(dict(type='report', ts=report['raw_timestamp'], vdev=report['vdev'], tsf=tsf, soc=soc_raw, delay_ok=delay_ok))
        index += 3
    return events


def _fresh(previous: Sample, current: Sample, qpc_hz: int) -> bool:
    shortest = Fraction((current.lower_qpc - previous.upper_qpc) * US_PER_S, qpc_hz)
    longest = Fraction((current.upper_qpc - previous.lower_qpc) * US_PER_S, qpc_hz)
    low = shortest * (US_PER_S - FRESHNESS_PPM) / US_PER_S - 1
    high = longest * (US_PER_S + FRESHNESS_PPM) / US_PER_S + 1
    return low <= current.tsf_us - previous.tsf_us <= high


def freshness_filter(samples: list[Sample], qpc_hz: int) -> tuple[list[Sample], list[tuple[int, str]]]:
    """Reject a sample whose TSF step cannot fit its host interval at 100 ppm."""
    accepted, rejected = [], []
    for sample in samples:
        if accepted and not _fresh(accepted[-1], sample, qpc_hz):
            rejected.append((sample.sequence, 'stale_or_inconsistent'))
            continue
        accepted.append(sample)
    return accepted, rejected


def screen(records: list[dict], requests: list[Request], qpc_hz: int) -> Screen:
    if type(qpc_hz) is not int or qpc_hz <= 0:
        raise ValueError('QPC frequency must be a positive integer')
    if not requests or any(b.lower_qpc <= a.lower_qpc for a, b in zip(requests, requests[1:])):
        raise ValueError('Requests must be non-empty and strictly ordered')
    events = _events(records)
    stamps = [e['ts'] for e in events]
    timeout = LISTEN_TIMEOUT_S * qpc_hz
    accept_ticks = MAX_WINDOW_US * qpc_hz // US_PER_S
    limits = [(r.lower_qpc, min(r.lower_qpc + timeout, n.lower_qpc)) for r, n in zip(requests, requests[1:])]
    limits.append((requests[-1].lower_qpc, requests[-1].lower_qpc + timeout))
    claimed: set[int] = set()
    rejected, candidates = [], []
    own_losses = foreign_groups = foreign_commands = 0
    for request, (begin, end) in zip(requests, limits):
        accept_end = min(begin + accept_ticks, end - 1)
        first, split, last = bisect_left(stamps, begin), bisect_right(stamps, accept_end), bisect_left(stamps, end)
        claimed.update(range(first, last))
        window = events[first:split]
        later = events[split:last]
        commands = [e for e in window if e['type'] == 'command']
        reports = [e for e in window if e['type'] == 'report']
        later_reports = [e for e in later if e['type'] == 'report']
        foreign_commands += sum(e['type'] == 'command' for e in later)
        reason = None
        if not request.succeeded:
            reason = 'request_failed'
        elif len(commands) != 1 or commands[0]['action'] != 4:
            reason = 'command_record_missing_or_extra'
        elif not reports:
            reason = 'late_report' if later_reports else 'own_loss'
            later_reports = later_reports[1:]
        elif len(reports) > 1:
            reason = 'multiple_reports_in_window'
        else:
            command, report = commands[0], reports[0]
            if report['ts'] < command['ts']:
                reason = 'report_before_command'
            elif report['vdev'] != command['vdev']:
                reason = 'vdev_mismatch'
            elif not report['delay_ok']:
                reason = 'delay_arithmetic'
            else:
                candidates.append(Sample(request.sequence, report['tsf'], report['soc'], request.lower_qpc, report['ts']))
        foreign_groups += len(later_reports)
        if reason in ('own_loss', 'late_report'):
            own_losses += 1
        if reason:
            rejected.append((request.sequence, reason))
    accepted, stale = freshness_filter(candidates, qpc_hz)
    rejected.extend(stale)
    unclaimed = [e for i, e in enumerate(events) if i not in claimed]
    foreign_groups += sum(e['type'] == 'report' for e in unclaimed)
    foreign_commands += sum(e['type'] == 'command' for e in unclaimed)
    duration = Fraction(limits[-1][1] - limits[0][0], qpc_hz)
    expected = own_losses * Fraction(foreign_groups) / duration * Fraction(MAX_WINDOW_US, US_PER_S)
    return Screen(tuple(accepted), tuple(sorted(rejected)), foreign_groups, foreign_commands,
                  own_losses, duration, expected)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -p test_sample_screen.py -v`
Expected: 10 tests `OK`.

- [ ] **Step 5: Commit**

```bash
git add research/clock_models/sample_screen.py tests/test_sample_screen.py
git commit -m "Add structural TSF sample screening with foreign-report accounting"
```

---

### Task 3: SoC domain test

**Files:**
- Create: `research/clock_models/soc_domain_test.py`
- Test: `tests/test_soc_domain.py`

**Interfaces:**
- Consumes: `Sample` (Task 2); `assess(points)` from `research/clock_models/analyze_clock_pairing_hypothesis.py`.
- Produces: `soc_domain(samples: list[Sample], ticks_per_unit: int = 10) -> dict` with keys `sample_count, ticks_per_unit, fixed_rate_feasible, fixed_rate_gap_qpc_ticks, rate_interval, rate_interval_contains_nominal, compatible_with_qpc_domain, shared_oscillator_proven`.

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.sample_screen import Sample
from research.clock_models.soc_domain_test import soc_domain


def series(drift_ppm, count=61, spacing=600_000_000):
    out = []
    for i in range(count):
        lower = 1_000 + i * spacing
        capture = lower + 2_000
        soc = int(Fraction(capture, 10) * (1 + Fraction(drift_ppm, 1_000_000)))
        out.append(Sample(i + 1, 0, soc, lower, lower + 5_000))
    return out


class SocDomainTests(unittest.TestCase):
    def test_same_domain_is_compatible(self):
        result = soc_domain(series(0))
        self.assertTrue(result['fixed_rate_feasible'])
        self.assertTrue(result['compatible_with_qpc_domain'])
        self.assertFalse(result['shared_oscillator_proven'])

    def test_one_ppm_separate_clock_is_rejected_over_an_hour(self):
        result = soc_domain(series(1))
        self.assertFalse(result['fixed_rate_feasible'])
        self.assertFalse(result['compatible_with_qpc_domain'])
        self.assertGreater(result['fixed_rate_gap_qpc_ticks'], 0)

    def test_requires_three_samples(self):
        with self.assertRaises(ValueError):
            soc_domain(series(0, count=2))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -p test_soc_domain.py -v`
Expected: `ModuleNotFoundError: No module named 'research.clock_models.soc_domain_test'`.

- [ ] **Step 3: Implement the module**

```python
"""Test whether the TSF report's SoC counter can lie in the QPC time domain.

Compatibility is a falsifiable condition, never proof of a shared oscillator.
"""
from __future__ import annotations

from fractions import Fraction

from research.clock_models.analyze_clock_pairing_hypothesis import assess
from research.clock_models.sample_screen import Sample


def _ratio(value: dict) -> Fraction:
    return Fraction(int(value['numerator']), int(value['denominator']))


def soc_domain(samples: list[Sample], ticks_per_unit: int = 10) -> dict:
    if type(ticks_per_unit) is not int or ticks_per_unit <= 0:
        raise ValueError('ticks_per_unit must be a positive integer')
    points = [(s.soc_raw, s.lower_qpc, s.upper_qpc) for s in samples]
    rate = assess(points)  # Validates count, ordering and ranges.
    low = max(lower - ticks_per_unit * soc for soc, lower, upper in points)
    high = min(upper - ticks_per_unit * soc for soc, lower, upper in points)
    contains = False
    if rate['affine_feasible']:
        interval = rate['slope_interval']
        contains = _ratio(interval['lower']) <= ticks_per_unit <= _ratio(interval['upper'])
    return dict(sample_count=len(points), ticks_per_unit=ticks_per_unit,
                fixed_rate_feasible=low <= high, fixed_rate_gap_qpc_ticks=max(0, low - high),
                rate_interval=rate['slope_interval'], rate_interval_contains_nominal=contains,
                compatible_with_qpc_domain=low <= high and contains, shared_oscillator_proven=False)
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -p test_soc_domain.py -v`
Expected: 3 tests `OK`.

- [ ] **Step 5: Commit**

```bash
git add research/clock_models/soc_domain_test.py tests/test_soc_domain.py
git commit -m "Add SoC-to-QPC domain compatibility test"
```

---

### Task 4: Beacon consistency check

**Files:**
- Create: `research/clock_models/beacon_consistency.py`
- Test: `tests/test_beacon_consistency.py`

**Interfaces:**
- Consumes: `SpanReport` and `Bound.predict` (Task 1).
- Produces: `TOLERANCE_US = 1000`; `Beacon(qpc: int, ap_tsf_us: int)`; `check_beacons(beacons: list[Beacon], spans: list[SpanReport]) -> dict` with keys `checked, unchecked, violations, tolerance_us, worst_excess_us, scope`.

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from research.clock_models.bracket_bound import Window, sliding_bounds
from research.clock_models.beacon_consistency import Beacon, check_beacons

HZ = 10_000_000


def spans():
    windows = [Window(9_000_000 + i * 2_000_000 + 200, 10_000_000 + i * 20_000_000, 10_005_000 + i * 20_000_000)
               for i in range(10)]
    return sliding_bounds(windows, HZ)


class BeaconTests(unittest.TestCase):
    def test_past_beacon_passes(self):
        result = check_beacons([Beacon(50_000_000, 9_000_000 + 4_000_000 - 50_000)], spans())
        self.assertEqual((result['checked'], result['violations']), (1, 0))

    def test_beacon_ahead_of_station_tsf_is_a_violation(self):
        result = check_beacons([Beacon(50_000_000, 9_000_000 + 4_000_000 + 5_000)], spans())
        self.assertEqual(result['violations'], 1)

    def test_beacon_outside_spans_is_unchecked(self):
        result = check_beacons([Beacon(1, 0)], spans())
        self.assertEqual((result['checked'], result['unchecked']), (0, 1))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -p test_beacon_consistency.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement the module**

```python
"""Coarse falsification of the station-TSF/AP-TSF link from public cache reads.

A cached beacon was transmitted before it was read, so its AP timestamp must
not exceed the predicted station TSF at the read. Cache age is unknown, so this
catches only gross disagreement, never sub-millisecond error.
"""
from __future__ import annotations

from dataclasses import dataclass

from research.clock_models.bracket_bound import SpanReport

TOLERANCE_US = 1_000


@dataclass(frozen=True)
class Beacon:
    qpc: int
    ap_tsf_us: int


def check_beacons(beacons: list[Beacon], spans: list[SpanReport]) -> dict:
    checked = unchecked = violations = 0
    worst = None
    for beacon in beacons:
        span = next((s for s in spans if s.feasible and s.start_qpc <= beacon.qpc <= s.end_qpc), None)
        if span is None:
            unchecked += 1
            continue
        checked += 1
        excess = beacon.ap_tsf_us - span.bound.predict(beacon.qpc)[1]
        worst = excess if worst is None else max(worst, excess)
        if excess > TOLERANCE_US:
            violations += 1
    return dict(checked=checked, unchecked=unchecked, violations=violations, tolerance_us=TOLERANCE_US,
                worst_excess_us=None if worst is None else str(worst),
                scope='coarse: AP timestamp must not exceed predicted station TSF; cache age unknown')
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -p test_beacon_consistency.py -v`
Expected: 3 tests `OK`.

- [ ] **Step 5: Commit**

```bash
git add research/clock_models/beacon_consistency.py tests/test_beacon_consistency.py
git commit -m "Add coarse beacon consistency check for the shared-clock link"
```

---

### Task 5: Run analyzer and pass/fail evaluation

**Files:**
- Create: `research/clock_models/analyze_bound_run.py`
- Test: `tests/test_analyze_bound_run.py`

**Interfaces:**
- Consumes: Tasks 1 to 4; `validate_bundle` from `research/evidence/validate_research_bundle.py`.
- Produces: `summarize(samples, qpc_hz, beacons=()) -> dict`; `analyze_legacy(path: Path) -> dict`; `load_run(folder: Path) -> dict`; `analyze_run(folder: Path) -> dict`; `evaluate(idle: dict, load: dict) -> dict`. Run folder format (written by Task 8): `run-result.json` (`success`, `qpc_frequency_hz`), `raw-timing.jsonl` (decoder output, first line `header`), `requests.jsonl` (probe receipts with `sequence`), `beacons.jsonl` (`qpc_before`, `ap_tsf_us`).

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import subprocess
import tempfile
import unittest
from research.clock_models.analyze_bound_run import analyze_run, evaluate

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

    def test_cli_help_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'research/clock_models/analyze_bound_run.py'), '--help'],
                                    cwd=directory, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -p test_analyze_bound_run.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement the module**

```python
"""Analyze a TSF bound run, or preview a legacy evidence bundle. Offline only.

Legacy bundles are previews: the old gate admitted them, but foreign-report
classification and own-loss accounting did not run live. Nothing here enables
a clock provider or claims accuracy against UTC.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from collections import Counter
from fractions import Fraction
import json

from research.clock_models.beacon_consistency import Beacon, check_beacons
from research.clock_models.bracket_bound import Window, coverage, sliding_bounds
from research.clock_models.sample_screen import Sample, freshness_filter, request_from_receipt, screen
from research.clock_models.soc_domain_test import soc_domain
from research.evidence.validate_research_bundle import validate_bundle

MAX_FILE_BYTES = 512 * 1024 * 1024


def _f(value: Fraction) -> float:
    return round(float(value), 3)


def _rank(values: list, share: Fraction):
    ordered = sorted(values)
    return ordered[max(0, -(-share.numerator * len(ordered) // share.denominator) - 1)]


def summarize(samples: list[Sample], qpc_hz: int, beacons: tuple[Beacon, ...] | list[Beacon] = ()) -> dict:
    if not samples:
        return dict(sample_count=0, proven_half_width_us=None, coverage=0.0, coverage_exact='0',
                    infeasible_spans=[], soc_domain=None, beacon_check=check_beacons(list(beacons), []))
    windows = [Window(s.tsf_us, s.lower_qpc, s.upper_qpc) for s in samples]
    spans = sliding_bounds(windows, qpc_hz)
    widths = [s.max_half_width_us for s in spans if s.feasible]
    covered = coverage(spans, windows[0].lower_qpc, windows[-1].upper_qpc) if spans else Fraction(0)
    window_us = [Fraction((w.upper_qpc - w.lower_qpc) * 1_000_000, qpc_hz) for w in windows]
    spacing = [Fraction(b.lower_qpc - a.lower_qpc, qpc_hz) for a, b in zip(windows, windows[1:])]
    try:
        soc = soc_domain(samples)
    except ValueError as error:
        soc = dict(error=str(error))
    return dict(
        sample_count=len(samples), span_count=len(spans),
        infeasible_spans=[dict(start_qpc=s.start_qpc, end_qpc=s.end_qpc, samples=s.sample_count) for s in spans if not s.feasible],
        coverage=_f(covered), coverage_exact=str(covered),
        proven_half_width_us=dict(median=_f(_rank(widths, Fraction(1, 2))), p95=_f(_rank(widths, Fraction(95, 100))),
                                  max=_f(max(widths)), max_exact=str(max(widths))) if widths else None,
        window_width_us=dict(min=_f(min(window_us)), median=_f(_rank(window_us, Fraction(1, 2))), max=_f(max(window_us))),
        request_spacing_s=dict(median=_f(_rank(spacing, Fraction(1, 2))), max=_f(max(spacing))) if spacing else None,
        soc_domain=soc, beacon_check=check_beacons(list(beacons), spans))


def _lines(path: Path) -> list[dict]:
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError(f'{path.name} exceeds size limit')
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def analyze_legacy(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    validate_bundle(data)
    hz = data['manifest']['qpc_frequency_hz']

    def samples(action: int) -> list[Sample]:
        return [Sample(o['sequence'], int(o['tsf_raw']), int(o['soc_raw']), int(o['host_before_qpc']), int(o['report_qpc']))
                for o in data['observations'] if o['action'] == action]
    action4, rejected4 = freshness_filter(samples(4), hz)
    action3 = samples(3)
    _, rejected3 = freshness_filter(action3, hz)
    return dict(schema='wht/tsf-host-bound-legacy-preview-v1', bundle_id=data['manifest']['bundle_id'], preview=True,
                not_screened=['foreign-report classification', 'own-loss accounting'],
                action4=summarize(action4, hz), action4_freshness_rejections=len(rejected4),
                action3_freshness=dict(samples=len(action3), rejected=len(rejected3)))


def load_run(folder: Path) -> dict:
    result = json.loads((folder / 'run-result.json').read_text(encoding='utf-8'))
    hz = result['qpc_frequency_hz']
    if type(hz) is not int or hz <= 0:
        raise ValueError('Run lacks a positive QPC frequency')
    records = _lines(folder / 'raw-timing.jsonl')
    header = next((r for r in records if r.get('kind') == 'header'), None)
    if header is None or header['perf_frequency_hz'] != hz or header['events_lost'] or header['buffers_lost']:
        raise ValueError('Trace header missing, mismatched or lossy')
    receipts = _lines(folder / 'requests.jsonl')
    requests = [request_from_receipt(r['sequence'], r) for r in receipts]
    beacons = [Beacon(b['qpc_before'], b['ap_tsf_us']) for b in _lines(folder / 'beacons.jsonl')]
    return dict(qpc_hz=hz, records=records, requests=requests, beacons=beacons, completed=result.get('success') is True)


def analyze_run(folder: Path) -> dict:
    data = load_run(folder)
    result = screen(data['records'], data['requests'], data['qpc_hz'])
    reasons = Counter(reason for _, reason in result.rejected)
    return dict(schema='wht/tsf-host-bound-run-v1', run_completed=data['completed'],
                screen=dict(request_count=len(data['requests']), accepted_count=len(result.accepted),
                            rejected_count=len(result.rejected), rejected_by_reason=dict(reasons),
                            foreign_groups=result.foreign_groups, foreign_commands=result.foreign_commands,
                            own_losses=result.own_losses, duration_s=_f(result.duration_s),
                            expected_misattributed=_f(result.expected_misattributed),
                            expected_misattributed_exact=str(result.expected_misattributed)),
                analysis=summarize(list(result.accepted), data['qpc_hz'], data['beacons']),
                shared_clock_link='assumed from 802.11 station TSF adoption; coarse beacon check only',
                accuracy_vs_utc=None, clock_provider_enabled=False)


def evaluate(idle: dict, load: dict) -> dict:
    verdict = {}
    for name, run in (('idle', idle), ('load', load)):
        widths, info, analysis = run['analysis']['proven_half_width_us'], run['screen'], run['analysis']
        beacon = analysis['beacon_check']
        criteria = dict(
            run_completed=run['run_completed'],
            max_proven_error_below_1000us=widths is not None and Fraction(widths['max_exact']) < 1000,
            coverage_at_least_90pct=Fraction(analysis['coverage_exact']) >= Fraction(9, 10),
            rejected_at_most_1pct=info['request_count'] > 0 and Fraction(info['rejected_count'], info['request_count']) <= Fraction(1, 100),
            misattribution_below_0_05=Fraction(info['expected_misattributed_exact']) < Fraction(5, 100),
            beacon_checked_without_violation=beacon['checked'] > 0 and beacon['violations'] == 0)
        criteria['stretch_100us'] = widths is not None and Fraction(widths['max_exact']) <= 100
        verdict[name] = criteria
    verdict['passed'] = all(all(v for k, v in verdict[n].items() if k != 'stretch_100us') for n in ('idle', 'load'))
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    legacy = sub.add_parser('legacy', help='Preview saved evidence bundles')
    legacy.add_argument('bundles', type=Path, nargs='+')
    one = sub.add_parser('run', help='Analyze one run folder')
    one.add_argument('folder', type=Path)
    both = sub.add_parser('evaluate', help='Apply the predeclared pass/fail criteria')
    both.add_argument('idle', type=Path)
    both.add_argument('load', type=Path)
    args = parser.parse_args()
    try:
        if args.mode == 'legacy':
            output = [analyze_legacy(path) for path in args.bundles]
        elif args.mode == 'run':
            output = analyze_run(args.folder)
        else:
            idle, load = analyze_run(args.idle), analyze_run(args.load)
            output = dict(idle=idle, load=load, verdict=evaluate(idle, load))
        print(json.dumps(output, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Analysis rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -p test_analyze_bound_run.py -v`
Expected: 3 tests `OK`.

- [ ] **Step 5: Run the full suite and commit**

```bash
python -m unittest discover -s tests
git add research/clock_models/analyze_bound_run.py tests/test_analyze_bound_run.py
git commit -m "Add TSF bound run analyzer and predeclared pass/fail evaluation"
```

---

### Task 6: Preview on saved campaign samples

**Files:**
- Create: `docs/clock-models/tsf-host-bound-preview.md`
- Modify: `docs/clock-models/README.md` (add a link)

- [ ] **Step 1: Run the preview on the six saved mixed runs**

```bash
python research/clock_models/analyze_bound_run.py legacy ../wifi-hardware-time/artifacts/QualcommCampaign-ecfaed68f20e/{idle,workload}-mixed-{1,2,3}/evidence.json > artifacts/bound-preview.json
```

Expected: exit 0. Each bundle reports `action4.proven_half_width_us.max` below 1,000 and `action4.soc_domain.compatible_with_qpc_domain` false. Record `action3_freshness.rejected`, which shows whether action 3 returns cached values.

- [ ] **Step 2: Write the preview document**

Write `docs/clock-models/tsf-host-bound-preview.md` with: an opening synopsis paragraph; scope (six saved bundles, 3 action-4 samples each, preview only, no new acquisition); a table per run of window widths, proven median and maximum half-width, rate interval in ppm and the SoC test result; the action-3 freshness result; the vdev finding; and limits (attribution and own-loss accounting not screened, shared-clock link assumed). Use only numbers printed in Step 1. Do not include raw TSF values, BSSIDs or capture hashes beyond bundle IDs.

- [ ] **Step 3: Link it, regenerate the index, test and commit**

Add a list item titled "TSF-to-host bound preview" that links `tsf-host-bound-preview.md` to the documents list in `docs/clock-models/README.md`.

```bash
python research/evidence/build_knowledge_index.py --write
python -m unittest discover -s tests
git add docs
git commit -m "Preview the TSF-to-host bound on saved action-4 samples"
```

---

### Task 7: Public BSS cache reader

**Files:**
- Create: `research/acquisition/bss_reader.py`
- Test: `tests/test_bss_reader.py`

**Interfaces:**
- Produces: `ENTRY_SIZE = 360`; `parse_bss_list(buffer: bytes, bssid: bytes) -> list[int]`; `BeaconRead(qpc_before: int, qpc_after: int, ap_tsf_us: int, bssid_sha256: str)`; `BssReader(interface_guid: str)` with `.read(qpc: Callable[[], int]) -> BeaconRead` and `.close()`.

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ctypes as ct
import struct
import unittest
from research.acquisition.bss_reader import ENTRY_SIZE, WLAN_BSS_ENTRY, WLAN_CONNECTION_ATTRIBUTES, parse_bss_list


def entry(bssid: bytes, timestamp: int) -> bytes:
    raw = bytearray(ENTRY_SIZE)
    raw[WLAN_BSS_ENTRY.dot11Bssid.offset:WLAN_BSS_ENTRY.dot11Bssid.offset + 6] = bssid
    struct.pack_into('<Q', raw, WLAN_BSS_ENTRY.ullTimestamp.offset, timestamp)
    return bytes(raw)


class BssReaderTests(unittest.TestCase):
    def test_structure_layout_matches_wlanapi(self):
        self.assertEqual(ct.sizeof(WLAN_BSS_ENTRY), 360)
        self.assertEqual(WLAN_BSS_ENTRY.dot11Bssid.offset, 40)
        self.assertEqual(WLAN_BSS_ENTRY.ullTimestamp.offset, 72)
        self.assertEqual(ct.sizeof(WLAN_CONNECTION_ATTRIBUTES), 604)

    def test_parse_selects_connected_bssid(self):
        mine, other = bytes(range(6)), bytes(range(6, 12))
        body = entry(other, 1) + entry(mine, 123456789)
        buffer = struct.pack('<II', 8 + len(body), 2) + body
        self.assertEqual(parse_bss_list(buffer, mine), [123456789])

    def test_parse_rejects_truncated_list(self):
        with self.assertRaises(ValueError):
            parse_bss_list(struct.pack('<II', 8, 3), bytes(6))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -p test_bss_reader.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement the module**

```python
"""Read the connected BSS's cached beacon timestamp through the public WLAN API.

Read-only. WlanGetNetworkBssList returns the WLAN service cache; no scan is
requested and no setting changes. Cache age is unknown, so the value supports
only the coarse shared-clock check. BSSIDs are hashed before leaving this module.
"""
from __future__ import annotations

import ctypes as ct
from dataclasses import dataclass
import hashlib
import struct
from typing import Callable
import uuid

ENTRY_SIZE = 360
HEADER_SIZE = 8
CURRENT_CONNECTION = 7  # wlan_intf_opcode_current_connection
INFRASTRUCTURE = 1  # dot11_BSS_type_infrastructure


class GUID(ct.Structure):
    _fields_ = [('Data1', ct.c_uint32), ('Data2', ct.c_uint16), ('Data3', ct.c_uint16), ('Data4', ct.c_ubyte * 8)]


class DOT11_SSID(ct.Structure):
    _fields_ = [('uSSIDLength', ct.c_uint32), ('ucSSID', ct.c_ubyte * 32)]


class WLAN_RATE_SET(ct.Structure):
    _fields_ = [('uRateSetLength', ct.c_uint32), ('usRateSet', ct.c_uint16 * 126)]


class WLAN_BSS_ENTRY(ct.Structure):
    _fields_ = [('dot11Ssid', DOT11_SSID), ('uPhyId', ct.c_uint32), ('dot11Bssid', ct.c_ubyte * 6),
                ('dot11BssType', ct.c_int), ('dot11BssPhyType', ct.c_int), ('lRssi', ct.c_int32),
                ('uLinkQuality', ct.c_uint32), ('bInRegDomain', ct.c_ubyte), ('usBeaconPeriod', ct.c_uint16),
                ('ullTimestamp', ct.c_uint64), ('ullHostTimestamp', ct.c_uint64),
                ('usCapabilityInformation', ct.c_uint16), ('ulChCenterFrequency', ct.c_uint32),
                ('wlanRateSet', WLAN_RATE_SET), ('ulIeOffset', ct.c_uint32), ('ulIeSize', ct.c_uint32)]


class WLAN_ASSOCIATION_ATTRIBUTES(ct.Structure):
    _fields_ = [('dot11Ssid', DOT11_SSID), ('dot11BssType', ct.c_int), ('dot11Bssid', ct.c_ubyte * 6),
                ('dot11PhyType', ct.c_int), ('uDot11PhyIndex', ct.c_uint32), ('wlanSignalQuality', ct.c_uint32),
                ('ulRxRate', ct.c_uint32), ('ulTxRate', ct.c_uint32)]


class WLAN_SECURITY_ATTRIBUTES(ct.Structure):
    _fields_ = [('bSecurityEnabled', ct.c_int), ('bOneXEnabled', ct.c_int),
                ('dot11AuthAlgorithm', ct.c_int), ('dot11CipherAlgorithm', ct.c_int)]


class WLAN_CONNECTION_ATTRIBUTES(ct.Structure):
    _fields_ = [('isState', ct.c_int), ('wlanConnectionMode', ct.c_int), ('strProfileName', ct.c_wchar * 256),
                ('wlanAssociationAttributes', WLAN_ASSOCIATION_ATTRIBUTES),
                ('wlanSecurityAttributes', WLAN_SECURITY_ATTRIBUTES)]


def parse_bss_list(buffer: bytes, bssid: bytes) -> list[int]:
    """Return ullTimestamp for every entry whose BSSID matches."""
    if len(buffer) < HEADER_SIZE:
        raise ValueError('Short BSS list')
    total, count = struct.unpack_from('<II', buffer)
    if total > len(buffer) or HEADER_SIZE + count * ENTRY_SIZE > len(buffer):
        raise ValueError('BSS list exceeds its buffer')
    stamps = []
    for index in range(count):
        item = WLAN_BSS_ENTRY.from_buffer_copy(buffer, HEADER_SIZE + index * ENTRY_SIZE)
        if bytes(item.dot11Bssid) == bssid:
            stamps.append(item.ullTimestamp)
    return stamps


@dataclass(frozen=True)
class BeaconRead:
    qpc_before: int
    qpc_after: int
    ap_tsf_us: int
    bssid_sha256: str


class BssReader:
    def __init__(self, interface_guid: str):
        self.api = ct.WinDLL('wlanapi.dll')
        self.api.WlanOpenHandle.argtypes = [ct.c_uint32, ct.c_void_p, ct.POINTER(ct.c_uint32), ct.POINTER(ct.c_void_p)]
        self.api.WlanCloseHandle.argtypes = [ct.c_void_p, ct.c_void_p]
        self.api.WlanFreeMemory.argtypes = [ct.c_void_p]
        self.api.WlanQueryInterface.argtypes = [ct.c_void_p, ct.POINTER(GUID), ct.c_int, ct.c_void_p,
                                                ct.POINTER(ct.c_uint32), ct.POINTER(ct.c_void_p), ct.c_void_p]
        self.api.WlanGetNetworkBssList.argtypes = [ct.c_void_p, ct.POINTER(GUID), ct.c_void_p, ct.c_int,
                                                   ct.c_int, ct.c_void_p, ct.POINTER(ct.c_void_p)]
        self.guid = GUID.from_buffer_copy(uuid.UUID(interface_guid).bytes_le)
        version, handle = ct.c_uint32(), ct.c_void_p()
        status = self.api.WlanOpenHandle(2, None, ct.byref(version), ct.byref(handle))
        if status:
            raise OSError(status, 'WlanOpenHandle failed')
        self.handle = handle

    def close(self) -> None:
        if self.handle:
            self.api.WlanCloseHandle(self.handle, None)
            self.handle = None

    def connected_bssid(self) -> bytes:
        size, data = ct.c_uint32(), ct.c_void_p()
        status = self.api.WlanQueryInterface(self.handle, ct.byref(self.guid), CURRENT_CONNECTION, None,
                                             ct.byref(size), ct.byref(data), None)
        if status:
            raise OSError(status, 'WlanQueryInterface failed')
        try:
            if size.value < ct.sizeof(WLAN_CONNECTION_ATTRIBUTES):
                raise ValueError('Short connection attributes')
            attributes = WLAN_CONNECTION_ATTRIBUTES.from_address(data.value)
            return bytes(attributes.wlanAssociationAttributes.dot11Bssid)
        finally:
            self.api.WlanFreeMemory(data)

    def read(self, qpc: Callable[[], int]) -> BeaconRead:
        bssid = self.connected_bssid()
        listing = ct.c_void_p()
        before = qpc()
        status = self.api.WlanGetNetworkBssList(self.handle, ct.byref(self.guid), None, INFRASTRUCTURE, 0, None,
                                                ct.byref(listing))
        after = qpc()
        if status:
            raise OSError(status, 'WlanGetNetworkBssList failed')
        try:
            total = ct.c_uint32.from_address(listing.value).value
            stamps = parse_bss_list(ct.string_at(listing.value, total), bssid)
        finally:
            self.api.WlanFreeMemory(listing)
        if len(stamps) != 1:
            raise RuntimeError('Connected BSS is not uniquely present in the cache')
        if self.connected_bssid() != bssid:
            raise RuntimeError('Association changed during the read')
        return BeaconRead(before, after, stamps[0], hashlib.sha256(bssid).hexdigest())
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -p test_bss_reader.py -v`
Expected: 3 tests `OK`.

- [ ] **Step 5: Live read-only smoke (no elevation, public API only)**

```bash
python -c "import sys;sys.path.insert(0,'.');from research.acquisition.bss_reader import BssReader;from research.acquisition.run_acquisition_campaign import Clock;import subprocess;g=subprocess.run(['powershell','-NoProfile','-Command','(Get-NetAdapter | Where-Object InterfaceDescription -match FastConnect | Where-Object Status -eq Up).InterfaceGuid'],capture_output=True,text=True).stdout.strip();r=BssReader(g);b=r.read(Clock().now);r.close();print(b.qpc_after-b.qpc_before, b.ap_tsf_us>0, b.bssid_sha256[:8])"
```

Expected: a small QPC bracket (well under 100,000 ticks), `True`, and an 8-character hash. Do not record the BSSID itself.

- [ ] **Step 6: Commit**

```bash
git add research/acquisition/bss_reader.py tests/test_bss_reader.py
git commit -m "Add read-only public BSS cache reader for the beacon check"
```

---

### Task 8: Long-run campaign controller

**Files:**
- Create: `research/acquisition/run_bound_campaign.py`
- Test: `tests/test_bound_campaign.py`

**Interfaces:**
- Consumes: from `research/acquisition/run_acquisition_campaign.py`: `PROVIDER`, `ROOT`, `Clock`, `Observer`, `TraceOwner`, `identity`, `run`, `same_identity`, `save`, `utc`; `ReportGate` from `campaign_gate.py`; `Admission`, `transition` from `campaign_admission.py`; `QUALIFIED_SHA256` from `research/tsf/qualcomm_protocol.py`; `BssReader` (Task 7); `TIMING_KINDS`, `LISTEN_TIMEOUT_S` (Task 2).
- Produces: `BoundGate(ReportGate)` with `.timing: list[dict]` and `.report_after(qpc: int) -> bool`; `remaining_sleep(spacing_s: float, elapsed_s: float) -> float`; `loss_budget_exceeded(losses: int, requests: int) -> bool`; `parse(argv) -> argparse.Namespace`; run folder files consumed by Task 5.

- [ ] **Step 1: Write the failing tests**

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import subprocess
import tempfile
import unittest
from research.acquisition.run_bound_campaign import BoundGate, loss_budget_exceeded, parse, remaining_sleep

ROOT = Path(__file__).resolve().parents[1]
GUID = '01234567-89ab-cdef-0123-456789abcdef'


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

    def test_argument_limits(self):
        base = ['--if-index', '5', '--interface-guid', GUID, '--condition', 'idle']
        self.assertEqual(parse(base).duration_s, 3600)
        for extra in (['--duration-s', '30'], ['--spacing-s', '0.1'], ['--interface-guid', 'nope']):
            with self.subTest(extra=extra), self.assertRaises(SystemExit):
                parse(base + extra)

    def test_cli_help_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(ROOT / 'research/acquisition/run_bound_campaign.py'), '--help'],
                                    cwd=directory, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('usage:', result.stdout.lower())


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `python -m unittest discover -s tests -p test_bound_campaign.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement the controller**

```python
"""Long-run action-4 TSF bound campaign. Windows/admin, explicit --execute.

One action-4 request in flight. Timing records are retained for offline
screening, not admitted live. The run stops on trace loss, lifecycle or
association change, driver change, request failure, own-loss budget or trace
cap; any stop writes a quarantine marker that this tool never clears.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import ctypes as ct
import hashlib
import json
import subprocess
import threading
import time
import urllib.request
import uuid

from research.acquisition.campaign_admission import Admission, transition
from research.acquisition.campaign_gate import ReportGate
from research.acquisition.run_acquisition_campaign import (PROVIDER, ROOT, Clock, Observer, TraceOwner, identity, run,
                                                           same_identity, save, utc)
from research.clock_models.sample_screen import LISTEN_TIMEOUT_S, TIMING_KINDS
from research.tsf.qualcomm_protocol import QUALIFIED_SHA256

MARKER = ROOT / 'artifacts' / 'bound-campaign-quarantine.json'
TRACE_CAP_BYTES = 250 * 1024 * 1024
DOWNLOAD_URL = 'https://speed.cloudflare.com/__down?bytes=100000000'
IDENTITY_EVERY = 10
BEACON_EVERY_S = 10
OWN_LOSS_LIMIT = 0.01
MIN_REQUESTS_FOR_LOSS_LIMIT = 100


class BoundGate(ReportGate):
    """Keeps the live health, lifecycle and association failures; retains timing records."""

    def __init__(self) -> None:
        super().__init__()
        self.timing: list[dict] = []

    def consume(self, event: dict) -> None:
        if event.get('kind') in TIMING_KINDS:
            if self.reason:
                self._fail(self.reason)
            if type(event.get('raw_timestamp')) is not int:
                self._fail('malformed_timing_record')
            self.timing.append(event)
            return
        super().consume(event)

    def report_after(self, qpc: int) -> bool:
        return any(e['kind'] == 'report' and e['raw_timestamp'] >= qpc for e in self.timing[-16:])


def remaining_sleep(spacing_s: float, elapsed_s: float) -> float:
    return max(0.0, spacing_s - elapsed_s)


def loss_budget_exceeded(losses: int, requests: int) -> bool:
    return requests >= MIN_REQUESTS_FOR_LOSS_LIMIT and losses > OWN_LOSS_LIMIT * requests


def bound_workload(stop_path: Path, output: Path, max_seconds: int) -> int:
    """SHA-256 10 ms on / 10 ms off, plus a looped HTTPS download."""
    start, cycles, payload = time.monotonic(), 0, bytes(65536)
    totals = dict(downloaded=0, errors=0)
    stop = threading.Event()

    def download() -> None:
        while not stop.is_set():
            try:
                with urllib.request.urlopen(DOWNLOAD_URL, timeout=30) as response:
                    while not stop.is_set():
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        totals['downloaded'] += len(chunk)
            except OSError:
                totals['errors'] += 1
                time.sleep(1)

    thread = threading.Thread(target=download, daemon=True)
    thread.start()
    while not stop_path.exists() and time.monotonic() - start < max_seconds:
        end = time.monotonic() + 0.010
        while time.monotonic() < end:
            hashlib.sha256(payload).digest()
            cycles += 1
        time.sleep(0.010)
    stop.set()
    thread.join(timeout=35)
    wall = time.monotonic() - start
    save(output, dict(workload='sha256-10ms-on-10ms-off plus looped HTTPS download', url=DOWNLOAD_URL,
                      wall_seconds=wall, hash_operations=cycles, downloaded_bytes=totals['downloaded'],
                      download_errors=totals['errors'],
                      mean_download_mbit_s=totals['downloaded'] * 8 / wall / 1e6 if wall else 0.0,
                      stop_requested=stop_path.exists()))
    return 0 if stop_path.exists() else 1


def submit(folder: Path, number: int, index: int, clock: Clock, observer: Observer, gate: BoundGate) -> dict:
    """Send one action-4 request through the existing admission protocol."""
    request_path = folder / f'request-{number:05}.json'
    control = folder / f'submission-{number:05}.json'
    save(control, dict(state='prepared', pid=None, abort_requested=False))
    admission = Admission(control, 'Local\\WifiAdmission-' + uuid.uuid4().hex, create=True)
    try:
        permitted = False
        with (folder / f'probe-{number:05}.stdout').open('w') as out, (folder / f'probe-{number:05}.stderr').open('w') as err:
            process = subprocess.Popen([sys.executable, str(ROOT / 'research/tsf/qualcomm_probe.py'), '--if-index', str(index),
                                        '--command', 'tsf_read_value', '--tsf-action', '4', '--execute',
                                        '--output', str(request_path), '--campaign-control', str(control),
                                        '--campaign-mutex', admission.name], stdout=out, stderr=err)
            with admission.locked():
                tracking = json.loads(control.read_text())
                tracking['pid'] = process.pid
                save(control, tracking)
            deadline = time.monotonic() + 15
            while process.poll() is None:
                observer.pump(gate)
                if not permitted:
                    with admission.locked():
                        if json.loads(control.read_text())['state'] == 'ready':
                            transition(control, 'permit')
                            permitted = True
                if time.monotonic() > deadline:
                    # Never kill a process whose overlapped IOCTL may still own buffers.
                    save(folder / 'pending-probe.json', dict(pid=process.pid, still_running=True))
                    raise RuntimeError('Probe deadline; pending probe retained')
                time.sleep(0.005)
        if process.returncode:
            raise RuntimeError('Private probe failed')
        receipt = json.loads(request_path.read_text(encoding='utf-8'))
        if receipt['driver_sha256'] != QUALIFIED_SHA256 or receipt['qpc_frequency_hz'] != clock.frequency:
            raise RuntimeError('Request build or clock mismatch')
        return receipt
    except BaseException:
        try:
            with admission.locked():
                transition(control, 'abort')
        except BaseException:
            pass
        raise
    finally:
        admission.close()


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--if-index', type=int)
    parser.add_argument('--interface-guid')
    parser.add_argument('--condition', choices=('idle', 'load'))
    parser.add_argument('--duration-s', type=int, default=3600)
    parser.add_argument('--spacing-s', type=float, default=2.0)
    parser.add_argument('--execute', action='store_true', help='Send private requests; default is preview only')
    parser.add_argument('--workload', nargs=3, metavar=('STOP', 'OUTPUT', 'SECONDS'), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.workload is None:
        if args.if_index is None or args.interface_guid is None or args.condition is None:
            parser.error('--if-index, --interface-guid and --condition are required')
        if not 60 <= args.duration_s <= 3600:
            parser.error('--duration-s must be 60 to 3600')
        if not 0.5 <= args.spacing_s <= 60:
            parser.error('--spacing-s must be 0.5 to 60')
        try:
            uuid.UUID(args.interface_guid)
        except ValueError:
            parser.error('--interface-guid must be a GUID')
    return args


def campaign(args: argparse.Namespace) -> int:
    from research.acquisition.bss_reader import BssReader
    if MARKER.exists():
        print(f'Quarantine marker present: {MARKER}. Review it before any new run.', file=sys.stderr)
        return 1
    if not ct.windll.shell32.IsUserAnAdmin():
        print('Administrator rights required.', file=sys.stderr)
        return 1
    clock = Clock()
    baseline = identity(args.if_index)
    guid = run(['powershell.exe', '-NoProfile', '-Command',
                f'(Get-NetAdapter -InterfaceIndex {args.if_index}).InterfaceGuid']).stdout.strip().strip('{}').lower()
    if guid != args.interface_guid.strip('{}').lower():
        print('Interface GUID does not match the interface index.', file=sys.stderr)
        return 1
    plan = dict(condition=args.condition, duration_s=args.duration_s, spacing_s=args.spacing_s, action=4,
                provider=PROVIDER, trace_cap_bytes=TRACE_CAP_BYTES, identity_every=IDENTITY_EVERY,
                beacon_every_s=BEACON_EVERY_S, own_loss_limit=OWN_LOSS_LIMIT, marker=str(MARKER))
    if not args.execute:
        print(json.dumps(dict(preview=True, plan=plan, adapter_status=baseline['Status']), indent=2))
        return 0
    folder = ROOT / 'artifacts' / f'BoundCampaign-{uuid.uuid4().hex[:12]}' / args.condition
    folder.mkdir(parents=True)
    session = 'WifiBound-' + uuid.uuid4().hex[:12]
    gate, trace = BoundGate(), TraceOwner(session, folder)
    observer = worker = reader = None
    failure, receipts, beacon_count, losses = None, [], 0, 0
    save(folder / 'session.json', dict(SessionName=session, StartedUtc=utc(), Plan=plan))
    try:
        save(folder / 'adapter-before.json', baseline)
        trace.start(['-p', PROVIDER, '0x2000000000000010', '0xff', '-o', str(folder / 'tsf.etl'), '-f', 'bin',
                     '-max', '256', '-rt', '-ct', 'perf', '-ft', '00:00:01', '-ets'])
        observer = Observer(session, args.if_index, folder, clock)
        observer.wait(2.5, gate)
        if not observer.ready or observer.association is None:
            raise RuntimeError('Observer readiness or association not established')
        reader = BssReader(args.interface_guid)
        if args.condition == 'load':
            worker = subprocess.Popen([sys.executable, __file__, '--workload', str(folder / 'workload-stop'),
                                       str(folder / 'workload.json'), str(args.duration_s + 120)],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            observer.wait(2, gate)
        end, next_beacon, number = time.monotonic() + args.duration_s, 0.0, 0
        with (folder / 'requests.jsonl').open('w', encoding='utf-8') as requests_file, \
             (folder / 'beacons.jsonl').open('w', encoding='utf-8') as beacon_file:
            while time.monotonic() < end:
                cycle = time.monotonic()
                if number % IDENTITY_EVERY == 0:
                    same_identity(identity(args.if_index), baseline)
                if worker is not None and worker.poll() is not None:
                    raise RuntimeError('Workload exited prematurely')
                if (folder / 'tsf.etl').stat().st_size > TRACE_CAP_BYTES:
                    raise RuntimeError('Trace cap reached')
                if time.monotonic() >= next_beacon:
                    beacon = reader.read(clock.now)
                    beacon_file.write(json.dumps(dict(qpc_before=beacon.qpc_before, qpc_after=beacon.qpc_after,
                                                      ap_tsf_us=beacon.ap_tsf_us, bssid_sha256=beacon.bssid_sha256)) + '\n')
                    beacon_file.flush()
                    beacon_count += 1
                    next_beacon = time.monotonic() + BEACON_EVERY_S
                number += 1
                receipt = submit(folder, number, args.if_index, clock, observer, gate)
                receipt['sequence'] = number
                requests_file.write(json.dumps(receipt) + '\n')
                requests_file.flush()
                receipts.append(receipt)
                listen_end = time.monotonic() + LISTEN_TIMEOUT_S
                while not gate.report_after(receipt['qpc_request_before']) and time.monotonic() < listen_end:
                    observer.pump(gate)
                    time.sleep(0.005)
                if not gate.report_after(receipt['qpc_request_before']):
                    losses += 1
                if loss_budget_exceeded(losses, number):
                    raise RuntimeError('Own-loss budget exceeded')
                observer.wait(remaining_sleep(args.spacing_s, time.monotonic() - cycle), gate)
        observer.wait(2.0, gate)
    except BaseException as error:
        gate.quarantine(str(error))
        failure = str(error)
    finally:
        if reader is not None:
            reader.close()
        if worker is not None:
            (folder / 'workload-stop').touch()
            try:
                worker.wait(timeout=40)
                if worker.returncode:
                    raise RuntimeError('Workload ended without controlled stop')
            except BaseException as error:
                failure = failure or str(error)
                if worker.poll() is None:
                    worker.kill()
                    worker.wait(timeout=5)
        try:
            trace.stop()
        except BaseException as error:
            failure = failure or f'Trace cleanup: {error}'
        if observer is not None:
            try:
                observer.close(gate)
            except BaseException as error:
                failure = failure or f'Observer cleanup: {error}'
        try:
            after = identity(args.if_index)
            save(folder / 'adapter-after.json', after)
            same_identity(after, baseline)
        except BaseException as error:
            failure = failure or f'Final identity: {error}'
    if failure is None:
        decoded = run([str(ROOT / 'artifacts/decode_tsf_etl.exe'), str(folder / 'tsf.etl')], timeout=600)
        (folder / 'raw-timing.jsonl').write_text(decoded.stdout, encoding='utf-8')
        offline = [json.loads(line) for line in decoded.stdout.splitlines()]
        live = [{k: v for k, v in e.items() if k != 'received_qpc'} for e in gate.timing]
        if live != [e for e in offline if e['kind'] in TIMING_KINDS]:
            failure = 'Live and offline timing records disagree'
        elif offline[0]['events_lost'] or offline[0]['buffers_lost']:
            failure = 'Trace reported lost events or buffers'
    save(folder / 'run-result.json', dict(success=failure is None, error=failure, condition=args.condition,
                                          duration_s=args.duration_s, request_count=len(receipts),
                                          own_losses_live=losses, beacon_reads=beacon_count,
                                          qpc_frequency_hz=clock.frequency, firmware_sampling_validated=False))
    if failure:
        save(MARKER, dict(created_utc=utc(), run=str(folder), reason=failure))
        print(f'Run stopped: {failure}. Quarantine marker written: {MARKER}', file=sys.stderr)
        return 1
    print(json.dumps(dict(run=str(folder), requests=len(receipts), own_losses_live=losses)))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse(argv)
    if args.workload is not None:
        stop, output, seconds = args.workload
        return bound_workload(Path(stop), Path(output), int(seconds))
    return campaign(args)


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `python -m unittest discover -s tests -p test_bound_campaign.py -v`
Expected: 5 tests `OK`.

- [ ] **Step 5: Build the native helpers into this worktree's `artifacts/`**

Locate the MSVC environment and build (Windows, from the repository root):

```powershell
$vs = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -property installationPath
New-Item -ItemType Directory -Force artifacts | Out-Null
cmd /c "`"$vs\VC\Auxiliary\Build\vcvarsall.bat`" arm64 && cl /nologo /W4 /WX /O2 research/acquisition/live_observer.c /Foartifacts/live_observer.obj /Feartifacts/live_observer.exe /link advapi32.lib wlanapi.lib iphlpapi.lib kernel32.lib && cl /nologo /W4 /WX research/tsf/decode_tsf_etl.c /Foartifacts/decode_tsf_etl.obj /Feartifacts/decode_tsf_etl.exe /link advapi32.lib kernel32.lib"
```

Expected: both executables exist; no warnings.

- [ ] **Step 6: Preview mode on the real adapter (no private request)**

From an elevated prompt:

```powershell
$a = Get-NetAdapter | Where-Object { $_.InterfaceDescription -match 'FastConnect' -and $_.Status -eq 'Up' }
python research/acquisition/run_bound_campaign.py --if-index $a.ifIndex --condition idle --duration-s 300
```

Expected: JSON with `"preview": true`, the plan, and `"adapter_status": "Up"`. No trace session, probe or file under `artifacts/BoundCampaign-*`.

- [ ] **Step 7: Full suite and commit**

```bash
python -m unittest discover -s tests
git add research/acquisition/run_bound_campaign.py tests/test_bound_campaign.py
git commit -m "Add long-run action-4 bound campaign controller"
```

---

**Execution note (2026-10-07):** the implemented controller takes the interface GUID from `identity()` (its `InterfaceGuid` field) instead of a separate `--interface-guid` argument, and preview mode no longer requires Administrator rights; `--execute` still does. Task 10 commands omit `--interface-guid`.

### Task 9: Phase 0 hex-dump caller check

Time-boxed to two hours. Read-only static analysis of the pinned driver.

**Files:**
- Modify: `docs/overview/2026-10-07-tsf-host-bound-design.md` (record the result in section 4)

- [ ] **Step 1: Locate the format strings and their references**

Use the existing Ghidra workspace procedure in `docs/adapters/ghidra-workspace.md` on the pinned driver. Find the RVAs of the two 16-byte hex-dump format strings and of `receive WMI_VDEV_TSF_REPORT_EVENTID on %d, tsf: %lu %lu`, and list every code reference to each.

- [ ] **Step 2: Decide reachability**

For each hex-dump caller, record whether it lies on the WMI event receive or TSF report path, and which debug level or component bits gate it. Record the actual received TSF event length if the receive path exposes it.

- [ ] **Step 3: Record and commit**

Add a dated "Result" paragraph to section 4 with the RVAs, callers and decision (reachable or not reachable). If the two-hour limit is reached first, record "not resolved within the time box" and the remaining unknown. Commit:

```bash
git add docs/overview/2026-10-07-tsf-host-bound-design.md
git commit -m "Record Phase 0 hex-dump caller result"
```

---

### Task 10: Gated live runs

**Stop and ask the user before Step 1.** State the run sequence, duration, the 120-second-limit extension, the UAC prompts and the quarantine behavior. Proceed only on explicit approval.

- [ ] **Step 1: Five-minute idle smoke run**

```powershell
$a = Get-NetAdapter | Where-Object { $_.InterfaceDescription -match 'FastConnect' -and $_.Status -eq 'Up' }
python research/acquisition/run_bound_campaign.py --if-index $a.ifIndex --condition idle --duration-s 300 --execute
python research/clock_models/analyze_bound_run.py run artifacts/BoundCampaign-<id>/idle
```

Expected: exit 0, about 100 to 150 requests, and an analyzer report. The smoke run is not used for pass/fail. If it stops, report the stop reason and the marker; do not continue.

- [ ] **Step 2: Sixty-minute idle run**

Same command with `--duration-s 3600`.

- [ ] **Step 3: Sixty-minute load run**

Same command with `--condition load --duration-s 3600`.

- [ ] **Step 4: Evaluate**

```bash
python research/clock_models/analyze_bound_run.py evaluate artifacts/BoundCampaign-<idle-id>/idle artifacts/BoundCampaign-<load-id>/load > artifacts/bound-verdict.json
```

Expected: a verdict object. Report `passed` exactly as computed.

---

### Task 11: Results and publication

**Files:**
- Create: `docs/acquisition/tsf-host-bound-results.md`
- Modify: `docs/acquisition/README.md`, `docs/knowledge/current-findings.md`

- [ ] **Step 1: Write the results document**

Opening synopsis with the verdict; scope (driver hash, dates, durations, conditions); a table per run of requests, accepted, rejected by reason, foreign groups, own losses, misattribution estimate, coverage, proven median, p95 and maximum, SoC result and beacon check; the verdict table; and limits (shared-clock link assumed, no UTC claim, exact-build scope). Numbers only from the analyzer output.

- [ ] **Step 2: Update current findings**

Add one dated paragraph to `docs/knowledge/current-findings.md` stating the verdict and linking the results document.

- [ ] **Step 3: Preserve private evidence**

Copy the run folders to the private evidence repository using its `tools/snapshot.py` workflow. Do not commit them to this repository.

- [ ] **Step 4: Index, test, commit, and ask before pushing**

```bash
python research/evidence/build_knowledge_index.py --write
python -m unittest discover -s tests
git add docs
git commit -m "Report TSF-to-host bound campaign results"
```

Ask the user before pushing the branch and opening a pull request.

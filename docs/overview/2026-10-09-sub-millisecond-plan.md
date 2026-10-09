# Sub-millisecond TSF timing: implementation plan

This plan turns the 2026-10-09 review of the TSF clock into tested code, then into one gated live qualification. It makes the live (causal) estimate stay below one millisecond essentially all of the time, tightens settled timestamps from about 280 us to about 200 us median under the guaranteed model, and adds a labeled learned-rate estimate near 150 us. It does not reach microsecond accuracy: the current capture window (about 250 us wide) sets a floor that only a different capture mechanism can remove, described at the end as a separate research track.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reliable sub-millisecond live TSF estimates and tighter settled timestamps, with every new assumption declared, versioned and tested.

**Architecture:** Four offline model changes (phase-jump allowance, settlement against every nearby sample, a learned-rate companion provider, new replay modes) leave every historical default unchanged and add versioned v3 policies. One acquisition change forces ETW delivery after each request so samples arrive in milliseconds instead of about 1.5 seconds. An acceptance evaluator turns "reliable sub-millisecond" into explicit pass/fail checks, applied to a live run only after the user authorizes it.

**Tech Stack:** Python 3.11+ standard library (`fractions`, `ctypes`, `unittest`), Windows ETW `ControlTraceW`, existing repository tooling.

**Spec:** the Background section below (review of `e6cd83a`) and the existing [causal provider design contract](2026-10-08-causal-provider-design.md). Read the [TSF mathematics reference](../clock-models/tsf-mathematics.md) before Task 1.

## Global Constraints

- Python 3.11 is the CI floor; use only the standard library and existing requirements.
- Model arithmetic stays exact (`fractions.Fraction`, integer QPC and TSF); floats appear only in rounded presentation fields.
- Every changed public function keeps its historical default behavior: called without the new arguments it must return exactly what it returned at `e6cd83a`. Existing tests must pass unmodified.
- New behavior is versioned: `wht/causal-provider-v2`, `wht/settlement-v3`, `wht/wander-model-v1`, `wht/sub-ms-acceptance-v1`.
- No task before Task 9 sends a request to a wireless adapter, starts a trace session or uses `--execute`. Tests use injected fakes only.
- Task 9 requires explicit user authorization for each live run, as [OPERATIONS.md](OPERATIONS.md) requires. Never clear a quarantine marker or unfinished-run record to make a run possible.
- Run one test file with `python -m unittest discover -s tests -p <file>.py`; run everything with `python -m unittest discover -s tests`. (`tests` is not a package; `python -m unittest tests.x` fails.)
- After changing anything under `research/`, `tests/` or `docs/`, run `python research/evidence/build_knowledge_index.py --write` and commit `docs/knowledge/research-index.json` and `docs/knowledge/reference-index.md` with the change; `--check` must then print `Unchanged`.
- No em-dashes in any file or commit message. No `Co-Authored-By` or other AI attribution trailers in commits.
- Windows: clone to a short path (for example `C:\src\wht`). From a deep path, five `test_relative_file_links_resolve` subtests fail on the 260-character path limit; that is an environment artifact, not a regression.

---

## Background: where the uncertainty comes from

Each sample's TSF was read somewhere inside a host window `[L, U]`: `L` is the QPC read just before the action-4 `DeviceIoControl`, `U` is the ETW timestamp of the driver's report. The model allows the TSF rate to differ from QPC by up to 200 ppm. Retained smoke results (2026-10-08) and the review's simulations give:

| Quantity | Value | Consequence |
|---|---|---|
| Capture window width | median 254.5 us, min 198.8 us | Floor: no model can beat about half the window (about 127 us) without knowing where in the window the read happened |
| Report delivery to the reader | median 1.49 s, max 2.17 s | Live samples arrive late; the 1 s requested spacing became 2.0 s because the controller waits for each report |
| Rate-only growth between samples | 200 us of half-width per second | With 2 s gaps the live estimate is stale 7 to 21 percent of the time |
| Constant-rate (affine) median | 124 us | Confirms the window floor; the read point is consistent, so more samples alone cannot shrink it |

The trace session already uses the minimum one-second flush timer (`-ft 00:00:01` in `run_bound_campaign.py`), so the only way to deliver faster is an explicit `ControlTraceW(EVENT_TRACE_CONTROL_FLUSH)` after each completion.

Two model gaps are fixed on the way. First, in an 802.11 infrastructure network the station rewrites its TSF to the access point's value on beacons. These jumps are a few microseconds and conflict with the declared "no unmodelled phase steps" condition; they are negligible at 280 us but matter as widths shrink. Second, settlement used only the nearest sample on each side, although a farther sample with a narrower window can be tighter.

## Targets

Simulated with the prototype of Tasks 1 to 7 on a synthetic recording (smoke-like windows, AP rate +37 ppm with slow wander, beacon sawtooth, 900 s). The true TSF stayed inside every reported interval in every scenario.

| Metric | Today (2 s gaps, 1.5 s delivery) | Flush, 1.0 s spacing | Flush, 0.5 s spacing | Acceptance limit |
|---|---:|---:|---:|---:|
| Live guaranteed coverage below 1 ms | 0.94 | 1.000 | 1.000 | at least 0.995 |
| Live guaranteed median half-width | not measured | 274 us | 215 us | report only |
| Live learned-rate median half-width | n/a | 148 us | 140 us | at most 180 us |
| Settled median half-width, v3 (includes 25 us jump allowance) | 282 us | 199 us | 170 us | at most 250 us |
| Settled share below 1 ms | 1.0 | 1.0 | 1.0 | 1.0 |
| Learned-rate holdout violations | 0 | 0 | 0 | 0 |
| Delivery p99 | about 2 s | under 0.02 s | under 0.02 s | at most 0.1 s |

These are expectations, not results. Only Task 9 produces evidence, and passing it remains conditional research evidence, not AP or UTC calibration.

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `research/clock_models/rate_bound.py` | Modify | `beacon_jump_allowance_us`, `DEFAULT_JUMP_US`, `check_jump`, jump-aware `envelope` |
| `research/clock_models/causal_provider.py` | Modify | `jump_us` parameter, `conditions()`, `PROVIDER_POLICY_VERSION` |
| `research/clock_models/bracket_bound.py` | Modify | `jump_us` in the affine polygon |
| `research/clock_models/settle.py` | Modify | v3 settlement: jump allowance and intersection of every available nearby sample |
| `research/clock_models/wander_provider.py` | Create | Exact constant-rate interval and the learned-rate companion provider |
| `research/clock_models/replay_wander.py` | Create | Grid replay of guaranteed and learned-rate layers with out-of-sample holdout |
| `research/clock_models/replay_causal_provider.py` | Modify | `settle-v3`, `causal-v3`, `wander` and `v3` modes |
| `research/acquisition/etw_flush.py` | Create | `ControlTraceW` flush binding with injectable API |
| `research/acquisition/report_wait.py` | Create | Bounded report wait that issues flushes |
| `research/acquisition/run_bound_campaign.py` | Modify | `--etw-flush` flag, `sampler_plan`, report wait through `wait_for_report` |
| `research/clock_models/sub_ms_acceptance.py` | Create | Run timing statistics and pass/fail evaluation |
| `tests/test_phase_jump.py`, `tests/test_settle_v3.py`, `tests/test_wander_provider.py`, `tests/test_replay_v3.py`, `tests/test_etw_flush.py`, `tests/test_report_wait.py`, `tests/test_campaign_flush.py`, `tests/test_sub_ms_acceptance.py` | Create | One test file per task |
| `docs/clock-models/tsf-mathematics.md`, `docs/acquisition/persistent-tsf-sampler.md`, `research/clock_models/README.md`, `docs/overview/README.md` | Modify | Document the v3 policies, the flag and this plan |

Diffs below are against `e6cd83a`. Apply each with `git apply` from the repository root (save the block to a file first) or edit by hand; the result must match exactly.

---

### Task 1: Declare and apply a phase-jump allowance

**Files:**
- Modify: `research/clock_models/rate_bound.py`
- Modify: `research/clock_models/causal_provider.py`
- Modify: `research/clock_models/bracket_bound.py`
- Test: `tests/test_phase_jump.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `rate_bound.check_jump(jump_us) -> None` (raises `ValueError` unless a non-negative `int` or `Fraction`); `rate_bound.beacon_jump_allowance_us(beacon_interval_tu=100, beacon_intervals=6, relative_ppm=40) -> int`; `rate_bound.DEFAULT_JUMP_US == 25`; `rate_bound.envelope(tsf_us, lower_qpc, upper_qpc, query_qpc, limits, jump_us=0) -> (low, high)`; `causal_provider.conditions(jump_us=0) -> tuple[str, ...]`; `causal_provider.PROVIDER_POLICY_VERSION == 'wht/causal-provider-v2'`; `CausalProvider(qpc_hz, rate_prior_ppm=200, threshold_us=1000, jump_us=0)` with attributes `jump_us` and `conditions`; `bracket_bound.window_bound(windows, qpc_hz, rate_prior_ppm=200, jump_us=0)`.

The allowance is pairwise: for any two instants, the TSF advance lies within the rate prior times the elapsed QPC time, widened by `jump_us` on each side. The default of 25 us is six 102.4 ms beacon periods at 40 ppm relative drift (two 20 ppm oscillators), rounded up. It is a declared prior, not a measurement.

- [ ] **Step 1: Write the failing test**

Create `tests/test_phase_jump.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.bracket_bound import Window, window_bound
from research.clock_models.causal_provider import CONDITIONS, AvailableSample, CausalProvider, conditions
from research.clock_models.rate_bound import DEFAULT_JUMP_US, beacon_jump_allowance_us, envelope, rate_limits

HZ = 10_000_000
LIMITS = rate_limits(HZ)
BEACON = 1_024_000  # 102.4 ms in QPC ticks


def sawtooth(qpc):
    """Nominal-rate AP trajectory; the station runs 40 ppm fast and re-adopts the AP value every beacon."""
    return Fraction(9_000_000_000) + Fraction(qpc, 10) + Fraction(40, 1_000_000) * Fraction(qpc % BEACON, 10)


class PhaseJumpTests(unittest.TestCase):
    def test_declared_allowance_is_six_beacon_periods_at_forty_ppm_rounded_up(self):
        self.assertEqual(beacon_jump_allowance_us(), 25)  # 6 * 102.4 ms * 40 ppm = 24.576 us
        self.assertEqual(DEFAULT_JUMP_US, 25)
        self.assertEqual(beacon_jump_allowance_us(100, 1, 40), 5)
        for bad in ((0, 6, 40), (100, -1, 40), (100, 6, 4.0)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                beacon_jump_allowance_us(*bad)

    def test_envelope_widens_each_side_by_the_allowance_only(self):
        base = envelope(1_000, 100, 200, 10_000, LIMITS)
        widened = envelope(1_000, 100, 200, 10_000, LIMITS, 25)
        self.assertEqual((widened[0], widened[1]), (base[0] - 25, base[1] + 25))
        with self.assertRaises(ValueError):
            envelope(1_000, 100, 200, 10_000, LIMITS, -1)

    def test_beacon_adoption_breaks_the_jump_free_envelope_but_not_the_widened_one(self):
        # Capture just before an adoption; query just after it. The station value
        # drops by about 4 us while the rate-only slack is far below 1 us.
        lower = 10 * BEACON - 120
        sample_tsf = int(sawtooth(lower))
        query = 10 * BEACON + 50
        low0, high0 = envelope(sample_tsf, lower, lower, query, LIMITS)
        low1, high1 = envelope(sample_tsf, lower, lower, query, LIMITS, 5)
        self.assertFalse(low0 <= sawtooth(query) <= high0)
        self.assertTrue(low1 <= sawtooth(query) <= high1)

    def test_provider_with_allowance_contains_the_sawtooth_and_states_it(self):
        provider = CausalProvider(HZ, jump_us=5)
        self.assertEqual(provider.conditions, conditions(5))
        self.assertNotEqual(conditions(5)[1], CONDITIONS[1])
        self.assertEqual(conditions(0), CONDITIONS)
        for i in range(30):
            lower = 5_000_000 + i * 7_777_777
            provider.ingest(AvailableSample(i, int(sawtooth(lower + 300)), lower, lower + 2_000, lower + 2_001))
            for query in (lower + 2_001, lower + 2_001 + BEACON // 3, lower + 7_000_000):
                estimate = provider.estimate(query)
                self.assertNotEqual(estimate.state, 'invalid')
                self.assertLessEqual(estimate.low_us, sawtooth(query))
                self.assertGreaterEqual(estimate.high_us, sawtooth(query))
                self.assertEqual(estimate.conditions, conditions(5))

    def test_affine_polygon_accepts_the_allowance(self):
        windows = [Window(int(sawtooth(q + 300)), q, q + 2_000) for q in range(1_000_000, 300_000_000, 9_999_991)]
        bound = window_bound(windows, HZ, jump_us=5)
        self.assertTrue(bound.feasible)
        for q in (50_000_000, 150_000_000):
            low, high = bound.predict(q)
            self.assertLessEqual(low, sawtooth(q))
            self.assertGreaterEqual(high, sawtooth(q))
        self.assertLessEqual(window_bound(windows, HZ).sample_count, bound.sample_count)
        with self.assertRaises(ValueError):
            window_bound(windows, HZ, jump_us=-1)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest discover -s tests -p test_phase_jump.py -v`
Expected: ERROR, `ImportError: cannot import name 'DEFAULT_JUMP_US'`.

- [ ] **Step 3: Implement**

Apply to `research/clock_models/rate_bound.py`:

```diff
diff --git a/research/clock_models/rate_bound.py b/research/clock_models/rate_bound.py
index a621ec2..847d887 100644
--- a/research/clock_models/rate_bound.py
+++ b/research/clock_models/rate_bound.py
@@ -9,6 +9,27 @@ from __future__ import annotations
 from fractions import Fraction
 
 US_PER_S = 1_000_000
+TU_US = 1_024  # 802.11 time unit
+
+
+def beacon_jump_allowance_us(beacon_interval_tu: int = 100, beacon_intervals: int = 6,
+                             relative_ppm: int = 40) -> int:
+    """Declared pairwise phase-jump allowance from station adoption of AP beacon timestamps.
+
+    Between adoptions the station TSF free-runs; its drift from the AP trajectory over
+    beacon_intervals beacon periods at relative_ppm is the largest correction one
+    adoption can apply. Defaults: 100 TU beacons, six periods without an adopted beacon
+    (power-save/DTIM listening), and two 20-ppm OFDM oscillators. A declared prior,
+    not a measurement; the result is rounded up to whole microseconds.
+    """
+    values = (beacon_interval_tu, beacon_intervals, relative_ppm)
+    if any(type(v) is not int or v <= 0 for v in values):
+        raise ValueError('Beacon jump parameters must be positive integers')
+    drift = Fraction(beacon_interval_tu * TU_US * beacon_intervals * relative_ppm, US_PER_S)
+    return -(-drift.numerator // drift.denominator)
+
+
+DEFAULT_JUMP_US = beacon_jump_allowance_us()
 
 
 def rate_limits(qpc_hz: int, rate_prior_ppm: int = 200) -> tuple[Fraction, Fraction]:
@@ -21,13 +42,24 @@ def rate_limits(qpc_hz: int, rate_prior_ppm: int = 200) -> tuple[Fraction, Fract
     return (nominal * (US_PER_S - rate_prior_ppm) / US_PER_S, nominal * (US_PER_S + rate_prior_ppm) / US_PER_S)
 
 
-def envelope(tsf_us: int, lower_qpc: int, upper_qpc: int, query_qpc, limits: tuple[Fraction, Fraction]):
-    """TSF interval at query_qpc implied by one sample alone (capture anywhere in its widened window)."""
+def check_jump(jump_us) -> None:
+    if type(jump_us) not in (int, Fraction) or jump_us < 0:
+        raise ValueError('Phase-jump allowance must be a non-negative int or Fraction')
+
+
+def envelope(tsf_us: int, lower_qpc: int, upper_qpc: int, query_qpc, limits: tuple[Fraction, Fraction],
+             jump_us=0):
+    """TSF interval at query_qpc implied by one sample alone (capture anywhere in its widened window).
+
+    jump_us widens both sides for a bounded pairwise phase jump, such as station TSF
+    adoption of the access point's beacon timestamp; 0 keeps the historical envelope.
+    """
+    check_jump(jump_us)
     a, b = limits
     toward_low = query_qpc - (upper_qpc + 1)  # latest possible capture gives the lowest value later
     toward_high = query_qpc - lower_qpc       # earliest possible capture gives the highest value later
-    low = tsf_us + (a if toward_low >= 0 else b) * toward_low
-    high = tsf_us + 1 + (b if toward_high >= 0 else a) * toward_high
+    low = tsf_us - jump_us + (a if toward_low >= 0 else b) * toward_low
+    high = tsf_us + 1 + jump_us + (b if toward_high >= 0 else a) * toward_high
     return low, high
 
 
```

Apply to `research/clock_models/causal_provider.py`:

```diff
diff --git a/research/clock_models/causal_provider.py b/research/clock_models/causal_provider.py
index 4437af6..2724fc1 100644
--- a/research/clock_models/causal_provider.py
+++ b/research/clock_models/causal_provider.py
@@ -10,7 +10,7 @@ from dataclasses import dataclass
 from fractions import Fraction
 import math
 
-from research.clock_models.rate_bound import rate_limits
+from research.clock_models.rate_bound import check_jump, rate_limits
 
 THRESHOLD_US = 1_000
 ROUNDING_ALLOWANCE_US = Fraction(1, 2)
@@ -20,6 +20,18 @@ CONDITIONS = (
     'continuity: one continuous TSF within the epoch',
     'station TSF equals access point TSF (802.11 synchronization; not checked here)',
 )
+PROVIDER_POLICY_VERSION = 'wht/causal-provider-v2'
+
+
+def conditions(jump_us=0) -> tuple[str, ...]:
+    """Declared conditions; a nonzero jump allowance replaces the no-phase-step condition."""
+    check_jump(jump_us)
+    if jump_us == 0:
+        return CONDITIONS
+    return (CONDITIONS[0],
+            f'bounded rate with phase jumps: over any interval the TSF advance lies within the rate prior '
+            f'times the elapsed QPC time, widened by {jump_us} us on each side',
+            *CONDITIONS[2:])
 
 
 @dataclass(frozen=True)
@@ -71,10 +83,13 @@ class CausalProvider:
     high(Q) = c_high + b*Q with c_high = min(T_k + 1 - b*L_k), over the epoch's samples k.
     Availability at least one tick after each window end makes every allowed query satisfy that."""
 
-    def __init__(self, qpc_hz: int, rate_prior_ppm: int = 200, threshold_us: int = THRESHOLD_US):
+    def __init__(self, qpc_hz: int, rate_prior_ppm: int = 200, threshold_us: int = THRESHOLD_US,
+                 jump_us=0):
         self.qpc_hz = qpc_hz
         self.rate_prior_ppm = rate_prior_ppm
         self.threshold_us = threshold_us
+        self.jump_us = jump_us
+        self.conditions = conditions(jump_us)
         self.a, self.b = rate_limits(qpc_hz, rate_prior_ppm)
         self.epoch = -1
         self.last_available: int | None = None
@@ -125,8 +140,8 @@ class CausalProvider:
             if self.invalid_reason is None:
                 self.invalid_reason = f'sample {sample.sequence}: {result.reason}'
             return result
-        low = sample.tsf_us - self.a * (sample.upper_qpc + 1)
-        high = sample.tsf_us + 1 - self.b * sample.lower_qpc
+        low = sample.tsf_us - self.jump_us - self.a * (sample.upper_qpc + 1)
+        high = sample.tsf_us + 1 + self.jump_us - self.b * sample.lower_qpc
         self.c_low = low if self.c_low is None else max(self.c_low, low)
         self.c_high = high if self.c_high is None else min(self.c_high, high)
         self.count += 1
@@ -146,10 +161,10 @@ class CausalProvider:
             raise ValueError('Query precedes the latest available sample; that would use future information')
         if self.invalid_reason is not None:
             return Estimate(query_qpc, 'invalid', self.epoch, None, None, None, None, None, None,
-                            self.last_available, self.invalid_reason)
+                            self.last_available, self.invalid_reason, self.conditions)
         if self.count == 0:
             return Estimate(query_qpc, 'acquiring', self.epoch, None, None, None, None, None, None,
-                            self.last_available, 'no usable sample in the current epoch')
+                            self.last_available, 'no usable sample in the current epoch', self.conditions)
         low = self.c_low + self.a * query_qpc
         high = self.c_high + self.b * query_qpc
         midpoint, half_width = (low + high) / 2, (high - low) / 2
@@ -161,4 +176,4 @@ class CausalProvider:
         state = 'tracking' if uncertainty < self.threshold_us else 'stale'
         reason = 'uncertainty below threshold' if state == 'tracking' else 'uncertainty at or above threshold'
         return Estimate(query_qpc, state, self.epoch, low, high, midpoint, half_width, rounded, uncertainty,
-                        self.last_available, reason)
+                        self.last_available, reason, self.conditions)
```

Apply to `research/clock_models/bracket_bound.py`:

```diff
diff --git a/research/clock_models/bracket_bound.py b/research/clock_models/bracket_bound.py
index 256a6e2..5b6440b 100644
--- a/research/clock_models/bracket_bound.py
+++ b/research/clock_models/bracket_bound.py
@@ -10,6 +10,8 @@ from dataclasses import dataclass, field
 from fractions import Fraction
 from itertools import combinations
 
+from research.clock_models.rate_bound import check_jump
+
 US_PER_S = 1_000_000
 RATE_PRIOR_PPM = 200  # Physical prior on |TSF rate / QPC rate - 1|.
 
@@ -57,7 +59,8 @@ class Bound:
         return (min(rates) - 1) * US_PER_S, (max(rates) - 1) * US_PER_S
 
 
-def window_bound(windows: list[Window], qpc_hz: int, rate_prior_ppm: int = RATE_PRIOR_PPM) -> Bound:
+def window_bound(windows: list[Window], qpc_hz: int, rate_prior_ppm: int = RATE_PRIOR_PPM, jump_us=0) -> Bound:
+    check_jump(jump_us)
     if type(qpc_hz) is not int or qpc_hz <= 0:
         raise ValueError('QPC frequency must be a positive integer')
     if type(rate_prior_ppm) is not int or not 0 < rate_prior_ppm < 10_000:
@@ -70,12 +73,13 @@ def window_bound(windows: list[Window], qpc_hz: int, rate_prior_ppm: int = RATE_
     nominal = Fraction(US_PER_S, qpc_hz)
     r_low = nominal * (US_PER_S - rate_prior_ppm) / US_PER_S
     r_high = nominal * (US_PER_S + rate_prior_ppm) / US_PER_S
-    # Offset limits per window: y - r*upper <= c <= y + 1 - r*lower.
-    lines = [(y, upper) for y, lower, upper in rows] + [(y + 1, lower) for y, lower, upper in rows]
+    # Offset limits per window: y - J - r*upper <= c <= y + 1 + J - r*lower (J: phase-jump allowance).
+    lines = ([(y - jump_us, upper) for y, lower, upper in rows]
+             + [(y + 1 + jump_us, lower) for y, lower, upper in rows])
 
     def inside(rate: Fraction, offset: Fraction) -> bool:
         return r_low <= rate <= r_high and all(
-            y - rate * upper <= offset <= y + 1 - rate * lower for y, lower, upper in rows)
+            y - jump_us - rate * upper <= offset <= y + 1 + jump_us - rate * lower for y, lower, upper in rows)
 
     candidates = {(r, y - r * x) for r in (r_low, r_high) for y, x in lines}
     for (y1, x1), (y2, x2) in combinations(lines, 2):
```

- [ ] **Step 4: Run the new and existing model tests**

Run each: `python -m unittest discover -s tests -p test_phase_jump.py`, then `-p test_rate_bound.py`, `-p test_causal_provider.py`, `-p test_bracket_bound.py`, `-p test_settle.py`, `-p test_replay_causal_provider.py`.
Expected: all `OK`. The existing files must pass without edits; that proves the defaults are unchanged.

- [ ] **Step 5: Refresh the index and commit**

```bash
python research/evidence/build_knowledge_index.py --write
git add research/clock_models/rate_bound.py research/clock_models/causal_provider.py research/clock_models/bracket_bound.py tests/test_phase_jump.py docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Declare a beacon phase-jump allowance in TSF envelopes"
```

---

### Task 2: Settlement v3

**Files:**
- Modify: `research/clock_models/settle.py`
- Test: `tests/test_settle_v3.py`

**Interfaces:**
- Consumes: `envelope(..., jump_us)`, `conditions(jump_us)` and `window_bound(..., jump_us)` from Task 1.
- Produces: `settle.SETTLEMENT_POLICY_VERSION_V3 == 'wht/settlement-v3'`; `settle.INTERSECT_SPAN_S == 10`; `settle.policy_version(jump_us=0, intersect_span_s=0) -> str`; `settle(event_qpc, samples, now_qpc, qpc_hz, rate_prior_ppm=200, affine=True, jump_us=0, intersect_span_s=0) -> Settled`; `Settled.jump_us`; `settle_replay(samples, qpc_hz, step_qpc, affine=True, rate_prior_ppm=200, jump_us=0, intersect_span_s=0) -> dict` with new keys `jump_us` (string) and `intersect_span_s`.

The bracket rule is unchanged: the nearest true-before and true-after samples decide when an event settles. v3 then also intersects the envelope of every other sample that was available by that reported cutoff and lies within `INTERSECT_SPAN_S` of the event. Each envelope is individually valid, so the intersection stays sound; the span only bounds the work, because a sample more than about two seconds farther than the nearest one cannot be tighter (window difference at most about 800 us, divided by the 400 ppm envelope spread).

- [ ] **Step 1: Write the failing test**

Create `tests/test_settle_v3.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.causal_provider import AvailableSample, conditions
from research.clock_models.settle import (INTERSECT_SPAN_S, SETTLEMENT_POLICY_VERSION, SETTLEMENT_POLICY_VERSION_V3,
                                          policy_version, settle, settle_replay)

HZ = 10_000_000


def at(qpc):
    return Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000)


def sample(sequence, lower, width_ticks, delay=1):
    upper = lower + width_ticks
    return AvailableSample(sequence, int(at(lower + width_ticks // 3)), lower, upper, upper + delay)


class SettleV3Tests(unittest.TestCase):
    def test_policy_version_tracks_the_parameters(self):
        self.assertEqual(policy_version(), SETTLEMENT_POLICY_VERSION)
        self.assertEqual(policy_version(25, 0), SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual(policy_version(0, 10), SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual(INTERSECT_SPAN_S, 10)

    def test_defaults_reproduce_v2_exactly(self):
        samples = [sample(i, 1_000_000 + i * 20_000_000, 2_540) for i in range(8)]
        for event in range(30_000_000, 130_000_000, 3_333_333):
            v2 = settle(event, samples, samples[-1].available_qpc, HZ, affine=False)
            same = settle(event, samples, samples[-1].available_qpc, HZ, affine=False, jump_us=0, intersect_span_s=0)
            self.assertEqual(v2, same)
            self.assertEqual(v2.settlement_policy_version, SETTLEMENT_POLICY_VERSION)

    def test_far_narrow_window_tightens_a_near_wide_bracket(self):
        # Narrow 20-us windows 1 s out; the nearest neighbours have 1-ms windows.
        samples = [sample(1, 0, 200), sample(2, 9_000_000, 10_000), sample(3, 11_000_000, 10_000),
                   sample(4, 20_000_000, 200)]
        event = 10_000_000
        v2 = settle(event, samples, samples[-1].available_qpc, HZ, affine=False)
        v3 = settle(event, samples, samples[-1].available_qpc, HZ, affine=False, intersect_span_s=INTERSECT_SPAN_S)
        self.assertEqual((v2.earlier_sequence, v2.later_sequence), (2, 3))
        self.assertLess(v3.half_width_us, v2.half_width_us)
        # Sample 4 arrives after the bracket's cutoff, so it cannot narrow this result.
        self.assertEqual(v3.rate_bound_sequences, (1, 2, 3))
        self.assertLessEqual(v3.low_us, at(event))
        self.assertGreaterEqual(v3.high_us, at(event))
        self.assertEqual(v3.settlement_policy_version, SETTLEMENT_POLICY_VERSION_V3)

    def test_unavailable_or_out_of_span_samples_are_ignored(self):
        samples = [sample(1, 0, 200), sample(2, 9_000_000, 10_000), sample(3, 11_000_000, 10_000),
                   sample(4, 20_000_000, 200, delay=900_000_000)]
        event = 10_000_000
        cutoff = samples[2].available_qpc
        v3 = settle(event, samples, cutoff, HZ, affine=False, intersect_span_s=INTERSECT_SPAN_S)
        self.assertNotIn(4, v3.rate_bound_sequences)
        narrow = settle(event, samples, cutoff, HZ, affine=False, intersect_span_s=0)
        far = settle(event, samples[1:3], cutoff, HZ, affine=False, intersect_span_s=INTERSECT_SPAN_S)
        self.assertEqual(far.half_width_us, narrow.half_width_us)

    def test_jump_allowance_widens_and_is_recorded(self):
        samples = [sample(i, 1_000_000 + i * 20_000_000, 2_540) for i in range(6)]
        event = 50_000_000
        plain = settle(event, samples, samples[-1].available_qpc, HZ, affine=False)
        jumped = settle(event, samples, samples[-1].available_qpc, HZ, affine=False, jump_us=25)
        self.assertEqual(jumped.half_width_us, plain.half_width_us + 25)
        self.assertEqual(jumped.jump_us, 25)
        self.assertEqual(jumped.conditions[:4], conditions(25))

    def test_replay_reports_v3_parameters(self):
        samples = [sample(i, 1_000_000 + i * 20_000_000, 2_540) for i in range(8)]
        result = settle_replay(samples, HZ, HZ, affine=False, jump_us=25, intersect_span_s=INTERSECT_SPAN_S)
        self.assertEqual(result['settlement_policy_version'], SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual((result['jump_us'], result['intersect_span_s']), ('25', 10))
        self.assertEqual(result['states'], dict(settled=result['events']))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest discover -s tests -p test_settle_v3.py -v`
Expected: ERROR, `ImportError: cannot import name 'INTERSECT_SPAN_S'`.

- [ ] **Step 3: Implement**

Apply to `research/clock_models/settle.py`:

```diff
diff --git a/research/clock_models/settle.py b/research/clock_models/settle.py
index 696c755..616c057 100644
--- a/research/clock_models/settle.py
+++ b/research/clock_models/settle.py
@@ -14,12 +14,19 @@ from dataclasses import dataclass
 from fractions import Fraction
 
 from research.clock_models.bracket_bound import Window, window_bound
-from research.clock_models.causal_provider import CONDITIONS, AvailableSample
+from research.clock_models.causal_provider import AvailableSample, conditions
 from research.clock_models.rate_bound import envelope, rate_limits
 
 AFFINE_HALF_SPAN_S = 30
 AFFINE_CONDITION = 'best estimate only: assumes one constant rate within the surrounding 60-second span'
 SETTLEMENT_POLICY_VERSION = 'wht/settlement-v2'
+SETTLEMENT_POLICY_VERSION_V3 = 'wht/settlement-v3'
+INTERSECT_SPAN_S = 10
+
+
+def policy_version(jump_us=0, intersect_span_s: int = 0) -> str:
+    """v2: nearest bracket pair only, no jump allowance. v3: any other setting."""
+    return SETTLEMENT_POLICY_VERSION if jump_us == 0 and intersect_span_s == 0 else SETTLEMENT_POLICY_VERSION_V3
 
 
 @dataclass(frozen=True)
@@ -36,16 +43,24 @@ class Settled:
     settled_at_qpc: int | None = None
     earlier_sequence: int | None = None
     later_sequence: int | None = None
-    conditions: tuple[str, ...] = CONDITIONS
+    conditions: tuple[str, ...] = conditions()
     settlement_policy_version: str = SETTLEMENT_POLICY_VERSION
     rate_bound_sequences: tuple[int, ...] = ()
+    jump_us: int | Fraction = 0
 
 
 def settle(event_qpc: int, samples: list[AvailableSample], now_qpc: int, qpc_hz: int,
-           rate_prior_ppm: int = 200, affine: bool = True) -> Settled:
-    """Settle one event using only samples available at now_qpc. Samples are one epoch, in capture order."""
+           rate_prior_ppm: int = 200, affine: bool = True, jump_us=0, intersect_span_s: int = 0) -> Settled:
+    """Settle one event using only samples available at now_qpc. Samples are one epoch, in capture order.
+
+    intersect_span_s > 0 also intersects the envelope of every sample available by the
+    reported cutoff whose window lies within that many seconds of the event (v3).
+    """
     if type(event_qpc) is not int or type(now_qpc) is not int:
         raise ValueError('Event and settle times must be integer QPC values')
+    if type(intersect_span_s) is not int or intersect_span_s < 0:
+        raise ValueError('Intersection span must be a non-negative integer number of seconds')
+    version, stated = policy_version(jump_us, intersect_span_s), conditions(jump_us)
     if any(b.lower_qpc <= a.upper_qpc for a, b in zip(samples, samples[1:])):
         raise ValueError('Samples must be in capture order with non-overlapping windows')
     # The quantized window includes its extra QPC tick; a window straddling
@@ -53,14 +68,16 @@ def settle(event_qpc: int, samples: list[AvailableSample], now_qpc: int, qpc_hz:
     available = [s for s in samples if s.available_qpc <= now_qpc]
     before = [s for s in available if s.upper_qpc + 1 <= event_qpc]
     if not before:
-        return Settled(event_qpc, 'unbracketed')
+        return Settled(event_qpc, 'unbracketed', conditions=stated, settlement_policy_version=version,
+                       jump_us=jump_us)
     earlier = before[-1]
     later = next((s for s in available if s.lower_qpc > event_qpc), None)
     if later is None:
-        return Settled(event_qpc, 'pending', earlier_sequence=earlier.sequence)
+        return Settled(event_qpc, 'pending', earlier_sequence=earlier.sequence, conditions=stated,
+                       settlement_policy_version=version, jump_us=jump_us)
     limits = rate_limits(qpc_hz, rate_prior_ppm)
-    lo1, hi1 = envelope(earlier.tsf_us, earlier.lower_qpc, earlier.upper_qpc, event_qpc, limits)
-    lo2, hi2 = envelope(later.tsf_us, later.lower_qpc, later.upper_qpc, event_qpc, limits)
+    lo1, hi1 = envelope(earlier.tsf_us, earlier.lower_qpc, earlier.upper_qpc, event_qpc, limits, jump_us)
+    lo2, hi2 = envelope(later.tsf_us, later.lower_qpc, later.upper_qpc, event_qpc, limits, jump_us)
     low, high = max(lo1, lo2), min(hi1, hi2)
     settled_at = max(later.available_qpc, earlier.available_qpc)
     # An overlapping capture cannot establish a bracket side. Once a bracket
@@ -68,28 +85,40 @@ def settle(event_qpc: int, samples: list[AvailableSample], now_qpc: int, qpc_hz:
     # the reported cutoff (which may be earlier than this call's now_qpc).
     overlaps = [s for s in available if s.lower_qpc <= event_qpc < s.upper_qpc + 1
                 and s.available_qpc <= settled_at]
-    for sample in overlaps:
-        lo, hi = envelope(sample.tsf_us, sample.lower_qpc, sample.upper_qpc, event_qpc, limits)
+    span = intersect_span_s * qpc_hz
+    # v3: every other sample available by the cutoff is valid evidence too; a far
+    # narrow window can beat a near wide one. The span only bounds the work.
+    extra = [s for s in available if span and s.available_qpc <= settled_at
+             and s not in (earlier, later) and s not in overlaps
+             and event_qpc - span <= s.upper_qpc and s.lower_qpc <= event_qpc + span]
+    for sample in (*overlaps, *extra):
+        lo, hi = envelope(sample.tsf_us, sample.lower_qpc, sample.upper_qpc, event_qpc, limits, jump_us)
         low, high = max(low, lo), min(high, hi)
-    sequences = tuple(s.sequence for s in [earlier, *overlaps, later])
+    # Capture order: identical to v2 when there are no extra samples.
+    sequences = tuple(s.sequence for s in sorted([earlier, *overlaps, *extra, later], key=lambda s: s.lower_qpc))
     if low > high:
         return Settled(event_qpc, 'inconsistent', earlier_sequence=earlier.sequence, later_sequence=later.sequence,
-                       rate_bound_sequences=sequences)
-    estimate = _affine(event_qpc, samples, settled_at, qpc_hz, rate_prior_ppm) if affine else (None, None, None)
+                       rate_bound_sequences=sequences, conditions=stated, settlement_policy_version=version,
+                       jump_us=jump_us)
+    estimate = (_affine(event_qpc, samples, settled_at, qpc_hz, rate_prior_ppm, jump_us) if affine
+                else (None, None, None))
     return Settled(event_qpc, 'settled', low, high, (low + high) / 2, (high - low) / 2, *estimate,
                    settled_at_qpc=settled_at,
                    earlier_sequence=earlier.sequence, later_sequence=later.sequence,
                    rate_bound_sequences=sequences,
-                   conditions=CONDITIONS + (AFFINE_CONDITION,))
+                   conditions=stated + (AFFINE_CONDITION,), settlement_policy_version=version,
+                   jump_us=jump_us)
 
 
-def _affine(event_qpc: int, samples: list[AvailableSample], now_qpc: int, qpc_hz: int, rate_prior_ppm: int):
+def _affine(event_qpc: int, samples: list[AvailableSample], now_qpc: int, qpc_hz: int, rate_prior_ppm: int,
+            jump_us=0):
     span = AFFINE_HALF_SPAN_S * qpc_hz
     members = [s for s in samples if s.available_qpc <= now_qpc
                and event_qpc - span <= s.lower_qpc and s.upper_qpc <= event_qpc + span]
     if len(members) < 3 or not any(s.upper_qpc < event_qpc for s in members) or not any(s.lower_qpc > event_qpc for s in members):
         return None, None, None
-    bound = window_bound([Window(s.tsf_us, s.lower_qpc, s.upper_qpc) for s in members], qpc_hz, rate_prior_ppm)
+    bound = window_bound([Window(s.tsf_us, s.lower_qpc, s.upper_qpc) for s in members], qpc_hz, rate_prior_ppm,
+                         jump_us)
     if not bound.feasible:
         return None, None, None
     low, high = bound.predict(event_qpc)
@@ -105,7 +134,7 @@ def _quantiles(values: list, shares=(Fraction(1, 2), Fraction(9, 10), Fraction(9
 
 
 def settle_replay(samples: list[AvailableSample], qpc_hz: int, step_qpc: int, affine: bool = True,
-                  rate_prior_ppm: int = 200) -> dict:
+                  rate_prior_ppm: int = 200, jump_us=0, intersect_span_s: int = 0) -> dict:
     """Settle events on a regular grid between the first and last capture, each at its earliest settle time."""
     if type(step_qpc) is not int or step_qpc <= 0:
         raise ValueError('Replay step must be a positive integer')
@@ -119,7 +148,7 @@ def settle_replay(samples: list[AvailableSample], qpc_hz: int, step_qpc: int, af
         earlier_at = min(s.available_qpc for s in samples if s.upper_qpc + 1 <= event)
         later_at = min(s.available_qpc for s in samples if s.lower_qpc > event)
         now = max(earlier_at, later_at)
-        result = settle(event, samples, now, qpc_hz, rate_prior_ppm, affine)
+        result = settle(event, samples, now, qpc_hz, rate_prior_ppm, affine, jump_us, intersect_span_s)
         states[result.state] += 1
         if result.state == 'settled':
             waits.append(Fraction(result.settled_at_qpc - event, qpc_hz))
@@ -129,7 +158,8 @@ def settle_replay(samples: list[AvailableSample], qpc_hz: int, step_qpc: int, af
         event += step_qpc
     count = sum(states.values())
     return dict(events=count, step_s=round(step_qpc / qpc_hz, 6), states=dict(states),
-                settlement_policy_version=SETTLEMENT_POLICY_VERSION,
+                settlement_policy_version=policy_version(jump_us, intersect_span_s),
+                jump_us=str(jump_us), intersect_span_s=intersect_span_s,
                 actual_settled_grid_max_half_width_us=round(float(max(widths)), 3) if widths else None,
                 actual_settled_grid_max_half_width_exact=str(max(widths)) if widths else None,
                 wait_s=_quantiles(waits) if waits else None,
@@ -138,4 +168,4 @@ def settle_replay(samples: list[AvailableSample], qpc_hz: int, step_qpc: int, af
                 affine_estimate_count=len(affine_widths),
                 affine_estimate_share=round(len(affine_widths) / count, 6) if count else None,
                 sub_millisecond_share=round(sum(1 for w in widths if w < 1_000) / count, 6) if count else None,
-                rate_prior_ppm=rate_prior_ppm, conditions=list(CONDITIONS) + [AFFINE_CONDITION])
+                rate_prior_ppm=rate_prior_ppm, conditions=list(conditions(jump_us)) + [AFFINE_CONDITION])
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest discover -s tests -p test_settle_v3.py`, then `-p test_settle.py` and `-p test_replay_causal_provider.py`.
Expected: all `OK`.

- [ ] **Step 5: Refresh the index and commit**

```bash
python research/evidence/build_knowledge_index.py --write
git add research/clock_models/settle.py tests/test_settle_v3.py docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Add v3 settlement with jump allowance and nearby-sample intersection"
```

---

### Task 3: Learned-rate companion provider

**Files:**
- Create: `research/clock_models/wander_provider.py`
- Test: `tests/test_wander_provider.py`

**Interfaces:**
- Consumes: `CausalProvider(..., jump_us)`, `AvailableSample`, `Consistency`, `Estimate`, `ROUNDING_ALLOWANCE_US` from `causal_provider`; `US_PER_S`, `check_jump` from `rate_bound`.
- Produces: `constant_rate_interval(samples, limits, jump_us=0) -> tuple[Fraction, Fraction] | None`; `WanderProvider(qpc_hz, *, wander_ppm, span_s=60, min_samples=5, rate_prior_ppm=200, threshold_us=1000, jump_us=0)` with `ingest(sample) -> Consistency`, `check_model(sample) -> bool | None`, `estimate(query_qpc) -> WanderEstimate`, `stale_from_qpc()`, attributes `guaranteed` and `conditions`; `WanderEstimate` fields `guaranteed, state, low_us, high_us, half_width_us, estimate_us, uncertainty_us, rate_ppm, reason, policy_version`; `WANDER_POLICY_VERSION == 'wht/wander-model-v1'`.

Why it helps: the guaranteed provider must assume the rate can swing across the full 200 ppm at any instant, so its interval grows 200 us per second. Over 60 seconds of samples a constant rate is pinned to a few ppm. The learned-rate model assumes the rate stays inside that pinned interval widened by `wander_ppm`, so holdover growth drops to a few microseconds per second and the width approaches the window floor. It is a stronger, labeled assumption. It never replaces the guarantee (its interval is intersected with it), and `check_model` tests each new sample against the model before ingest, so a wrong assumption shows up as holdout violations.

`constant_rate_interval` is exact and O(n^2): a common offset exists for rate `r` if and only if every ordered pair of samples satisfies `r * (L_j - U_i - 1) <= T_j - T_i + 1 + 2J`. The test `test_matches_the_affine_polygon_rate_projection` checks this against the existing polygon code.

- [ ] **Step 1: Write the failing test**

Create `tests/test_wander_provider.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import unittest
from research.clock_models.causal_provider import AvailableSample
from research.clock_models.rate_bound import rate_limits
from research.clock_models.wander_provider import WANDER_POLICY_VERSION, WanderProvider, constant_rate_interval

HZ = 10_000_000
RATE = Fraction(1_000_037, 10_000_000)  # +37 ppm TSF us per QPC tick


def at(qpc, rate=RATE):
    return Fraction(9_000_000_000) + rate * qpc


def samples(count, spacing=10_000_000, width=2_540, delay=40_000, clock=at):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        out.append(AvailableSample(i, int(clock(lower + width // 3)), lower, lower + width, lower + width + delay))
    return out


class ConstantRateIntervalTests(unittest.TestCase):
    def test_interval_contains_the_true_rate_and_narrows_with_span(self):
        limits = rate_limits(HZ)
        short = constant_rate_interval(samples(5), limits)
        long = constant_rate_interval(samples(60), limits)
        for interval in (short, long):
            self.assertLessEqual(interval[0], RATE)
            self.assertGreaterEqual(interval[1], RATE)
        self.assertLess(long[1] - long[0], short[1] - short[0])

    def test_rate_change_inside_the_span_is_infeasible(self):
        def kink(qpc):
            return at(qpc) if qpc < 300_000_000 else at(300_000_000) + Fraction(1_000_150, 10_000_000) * (qpc - 300_000_000)
        self.assertIsNone(constant_rate_interval(samples(60, clock=kink), rate_limits(HZ)))

    def test_matches_the_affine_polygon_rate_projection(self):
        from research.clock_models.bracket_bound import Window, window_bound
        group = samples(8, spacing=7_000_003)
        bound = window_bound([Window(s.tsf_us, s.lower_qpc, s.upper_qpc) for s in group], HZ)
        rates = [rate for rate, _ in bound.vertices]
        self.assertEqual(constant_rate_interval(group, rate_limits(HZ)), (min(rates), max(rates)))


class WanderProviderTests(unittest.TestCase):
    def test_model_is_narrower_contains_truth_and_never_widens_the_guarantee(self):
        provider = WanderProvider(HZ, wander_ppm=2)
        for item in samples(40):
            self.assertIn(provider.check_model(item), (None, True))
            provider.ingest(item)
        query = samples(40)[-1].available_qpc + 15_000_000  # 1.5 s holdover
        result = provider.estimate(query)
        self.assertEqual(result.state, 'tracking')
        self.assertLess(result.half_width_us, result.guaranteed.half_width_us)
        self.assertGreaterEqual(result.low_us, result.guaranteed.low_us)
        self.assertLessEqual(result.high_us, result.guaranteed.high_us)
        self.assertLessEqual(result.low_us, at(query))
        self.assertGreaterEqual(result.high_us, at(query))
        self.assertEqual(result.policy_version, WANDER_POLICY_VERSION)
        self.assertIn('learned rate', provider.conditions[-1])

    def test_unavailable_until_min_samples(self):
        provider = WanderProvider(HZ, wander_ppm=2, min_samples=5)
        for item in samples(4):
            provider.ingest(item)
        result = provider.estimate(samples(4)[-1].available_qpc)
        self.assertEqual(result.state, 'unavailable')
        self.assertEqual(result.guaranteed.state, 'tracking')

    def test_holdout_flags_a_rate_step_that_the_guarantee_still_accepts(self):
        provider = WanderProvider(HZ, wander_ppm=1)
        fast = Fraction(1_000_187, 10_000_000)  # +187 ppm: inside the 200-ppm prior
        def step(qpc):
            return at(qpc) if qpc < 400_000_000 else at(400_000_000) + fast * (qpc - 400_000_000)
        verdicts = []
        for item in samples(60, clock=step):
            verdicts.append(provider.check_model(item))
            self.assertTrue(provider.ingest(item).compatible)
        self.assertIn(False, verdicts)

    def test_parameter_validation(self):
        for kwargs in (dict(wander_ppm=-1), dict(wander_ppm=201), dict(wander_ppm=2, span_s=0),
                       dict(wander_ppm=2, min_samples=1), dict(wander_ppm=1.5)):
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                WanderProvider(HZ, **kwargs)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest discover -s tests -p test_wander_provider.py -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'research.clock_models.wander_provider'`.

- [ ] **Step 3: Implement**

Create `research/clock_models/wander_provider.py`:

```python
"""Stronger-assumption companion to CausalProvider: a learned rate with bounded wander.

The guaranteed result stays CausalProvider's rate-only interval. This module adds a
narrower model interval under an explicitly declared extra assumption: across the
trailing span and the holdover to the query, the TSF rate stays within the exact
constant-rate interval of the trailing samples widened by +/- wander_ppm. The model is
labeled, never replaces the guarantee, and is validated out of sample by check_model().
Offline research code; contract in docs/overview/2026-10-09-sub-millisecond-plan.md.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from fractions import Fraction
import math

from research.clock_models.causal_provider import ROUNDING_ALLOWANCE_US, AvailableSample, CausalProvider, Consistency, Estimate
from research.clock_models.rate_bound import US_PER_S, check_jump

WANDER_POLICY_VERSION = 'wht/wander-model-v1'
SPAN_S = 60
MIN_SAMPLES = 5


def constant_rate_interval(samples, limits: tuple[Fraction, Fraction], jump_us=0) -> tuple[Fraction, Fraction] | None:
    """Exact constant-rate interval (TSF us per QPC tick) consistent with every sample, or None.

    Under TSF(q) = c + r*q with pairwise phase jumps of at most jump_us, sample i limits
    c to [T_i - J - r*(U_i + 1), T_i + 1 + J - r*L_i]. A common c exists for rate r
    iff every pair satisfies r*(L_j - U_i - 1) <= T_j - T_i + 1 + 2J, so the feasible
    rates are an intersection of half-lines: O(n^2), exact.
    """
    check_jump(jump_us)
    low, high = limits
    for i in samples:
        for j in samples:
            span = j.lower_qpc - (i.upper_qpc + 1)
            slack = j.tsf_us - i.tsf_us + 1 + 2 * jump_us
            if span > 0:
                high = min(high, Fraction(slack) / span)
            elif span < 0:
                low = max(low, Fraction(slack) / span)
            elif slack < 0:
                return None
    return (low, high) if low <= high else None


@dataclass(frozen=True)
class WanderEstimate:
    guaranteed: Estimate
    state: str  # tracking | stale | unavailable | rejected | invalid
    low_us: Fraction | None
    high_us: Fraction | None
    half_width_us: Fraction | None
    estimate_us: int | None
    uncertainty_us: Fraction | None
    rate_ppm: tuple[Fraction, Fraction] | None
    reason: str
    policy_version: str = WANDER_POLICY_VERSION


class WanderProvider:
    def __init__(self, qpc_hz: int, *, wander_ppm: int, span_s: int = SPAN_S, min_samples: int = MIN_SAMPLES,
                 rate_prior_ppm: int = 200, threshold_us: int = 1_000, jump_us=0):
        if type(wander_ppm) is not int or not 0 <= wander_ppm <= rate_prior_ppm:
            raise ValueError('wander_ppm must be an integer within the rate prior')
        if type(span_s) is not int or span_s <= 0 or type(min_samples) is not int or min_samples < 2:
            raise ValueError('Require a positive span and at least two samples')
        self.guaranteed = CausalProvider(qpc_hz, rate_prior_ppm, threshold_us, jump_us)
        self.qpc_hz, self.wander_ppm, self.span_s, self.min_samples = qpc_hz, wander_ppm, span_s, min_samples
        self.threshold_us, self.jump_us = threshold_us, jump_us
        self.trailing: deque[AvailableSample] = deque()
        self.fit: tuple[Fraction, Fraction, Fraction, Fraction] | None = None  # a', b', c_low, c_high
        self.fit_reason = 'too few samples'

    @property
    def conditions(self) -> tuple[str, ...]:
        return self.guaranteed.conditions + (
            f'learned rate: over the trailing {self.span_s} s and the holdover to the query, the TSF rate stays '
            f'within the trailing constant-rate interval widened by {self.wander_ppm} ppm',)

    def _refit(self) -> None:
        self.fit = None
        if len(self.trailing) < self.min_samples:
            self.fit_reason = 'too few samples'
            return
        prior = (self.guaranteed.a, self.guaranteed.b)
        interval = constant_rate_interval(self.trailing, prior, self.jump_us)
        if interval is None:
            self.fit_reason = 'trailing samples admit no constant rate'
            return
        wander = Fraction(US_PER_S, self.qpc_hz) * self.wander_ppm / US_PER_S
        a, b = max(prior[0], interval[0] - wander), min(prior[1], interval[1] + wander)
        c_low = max(s.tsf_us - self.jump_us - a * (s.upper_qpc + 1) for s in self.trailing)
        c_high = min(s.tsf_us + 1 + self.jump_us - b * s.lower_qpc for s in self.trailing)
        self.fit, self.fit_reason = (a, b, c_low, c_high), 'fitted'

    def check_model(self, sample: AvailableSample) -> bool | None:
        """Out-of-sample test before ingest: is the new sample feasible under the model? None: no model."""
        if self.fit is None or self.guaranteed.invalid_reason is not None:
            return None
        a, b, c_low, c_high = self.fit
        latest = min(Fraction(sample.upper_qpc + 1), (sample.tsf_us + 1 - c_low) / a)
        earliest = max(Fraction(sample.lower_qpc), (sample.tsf_us - c_high) / b)
        return earliest <= latest

    def ingest(self, sample: AvailableSample) -> Consistency:
        result = self.guaranteed.ingest(sample)
        if result.compatible:
            self.trailing.append(sample)
            horizon = sample.lower_qpc - self.span_s * self.qpc_hz
            while self.trailing and self.trailing[0].lower_qpc < horizon:
                self.trailing.popleft()
        self._refit()
        return result

    def stale_from_qpc(self) -> Fraction | None:
        """First QPC at which the model uncertainty reaches the threshold (ignores the guarantee's narrowing)."""
        if self.fit is None or self.guaranteed.invalid_reason is not None:
            return None
        a, b, c_low, c_high = self.fit
        return (2 * (self.threshold_us - ROUNDING_ALLOWANCE_US) - c_high + c_low) / (b - a)

    def estimate(self, query_qpc: int) -> WanderEstimate:
        guaranteed = self.guaranteed.estimate(query_qpc)
        if guaranteed.state in ('invalid', 'acquiring'):
            return WanderEstimate(guaranteed, guaranteed.state, None, None, None, None, None, None, guaranteed.reason)
        if self.fit is None:
            return WanderEstimate(guaranteed, 'unavailable', None, None, None, None, None, None, self.fit_reason)
        a, b, c_low, c_high = self.fit
        low = max(guaranteed.low_us, c_low + a * query_qpc)
        high = min(guaranteed.high_us, c_high + b * query_qpc)
        if low > high:
            return WanderEstimate(guaranteed, 'rejected', None, None, None, None, None, None,
                                  'model interval excludes the guaranteed interval; learned-rate assumption failed')
        midpoint, half_width = (low + high) / 2, (high - low) / 2
        uncertainty = half_width + ROUNDING_ALLOWANCE_US
        state = 'tracking' if uncertainty < self.threshold_us else 'stale'
        scale = Fraction(self.qpc_hz, US_PER_S)
        rate_ppm = ((a * scale - 1) * US_PER_S, (b * scale - 1) * US_PER_S)
        return WanderEstimate(guaranteed, state, low, high, half_width, math.floor(midpoint + Fraction(1, 2)),
                              uncertainty, rate_ppm, self.fit_reason)
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest discover -s tests -p test_wander_provider.py -v`
Expected: 7 tests, `OK`.

- [ ] **Step 5: Refresh the index and commit**

```bash
python research/evidence/build_knowledge_index.py --write
git add research/clock_models/wander_provider.py tests/test_wander_provider.py docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Add learned-rate companion provider with out-of-sample checks"
```

---

### Task 4: v3 replay modes

**Files:**
- Create: `research/clock_models/replay_wander.py`
- Modify: `research/clock_models/replay_causal_provider.py`
- Test: `tests/test_replay_v3.py`

**Interfaces:**
- Consumes: Tasks 1 to 3.
- Produces: `replay_wander(items, qpc_hz, start, end, *, wander_ppm, jump_us=0, rate_prior_ppm=200, threshold_us=1000) -> dict` with keys `guaranteed_tracking_share`, `model_tracking_share`, `guaranteed_half_width_us`, `model_half_width_us` (each `{median, p90, p99, max}`), `holdout_checked`, `holdout_violations`, `holdout_violation_sequences`, `queries`, `guaranteed_states`, `model_states`, `policy_version`, `conditions`; in `replay_causal_provider`: `V3_MODES == ('settle-v3', 'causal-v3', 'wander')`, `WANDER_PPM == 2`, `replay(..., jump_us=0)` adding output keys `provider_policy_version` and `jump_us`; `replay_run(folder, mode)` accepting the three new modes; CLI `--mode v3`.

Mode semantics: `causal-v3` is `causal-arrival` with `DEFAULT_JUMP_US`. `settle-v3` is `settle` with `DEFAULT_JUMP_US` and `INTERSECT_SPAN_S`, returned under the `settle` key. `wander` runs `replay_wander` over the same declared interval as `causal-arrival` (first request QPC to last request QPC plus the five-second listen interval) on a 100 ms grid, returned under the `wander` key. The `all` mode keeps its historical four modes so published outputs stay reproducible.

- [ ] **Step 1: Write the failing test**

Create `tests/test_replay_v3.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fractions import Fraction
import tempfile
import unittest
from unittest.mock import patch
from research.clock_models.causal_provider import PROVIDER_POLICY_VERSION, AvailableSample
from research.clock_models.rate_bound import DEFAULT_JUMP_US
from research.clock_models.replay_causal_provider import V3_MODES, replay_run
from research.clock_models.replay_wander import replay_wander
from research.clock_models.sample_screen import Request, Sample, Screen
from research.clock_models.settle import SETTLEMENT_POLICY_VERSION_V3
from research.clock_models.wander_provider import WANDER_POLICY_VERSION

HZ = 10_000_000


def tsf(qpc):
    return int(Fraction(9_000_000_000) + Fraction(qpc, 10) * Fraction(1_000_037, 1_000_000))


def available(count=30, spacing=10_000_000, width=2_540, delay=40_000):
    out = []
    for i in range(count):
        lower = 1_000_000 + i * spacing
        out.append(AvailableSample(i, tsf(lower + width // 3), lower, lower + width, lower + width + delay))
    return out


def recorded(count=40, spacing=10_000_000, delivery=50_000):
    accepted, live, receipts, requests = [], [], [], []
    for i in range(1, count + 1):
        lower = i * spacing
        upper = lower + 2_540
        accepted.append(Sample(i, tsf(lower + 800), 0, lower, upper))
        live.extend([dict(kind='report', raw_timestamp=upper), dict(kind='delay', received_qpc=upper + delivery)])
        receipts.append(dict(sequence=i, qpc_request_completed=upper + 10))
        requests.append(Request(i, lower, True))
    return accepted, live, receipts, requests


def run_mode(mode, **kwargs):
    accepted, live, receipts, requests = recorded(**kwargs)
    data = dict(qpc_hz=HZ, records=[], requests=requests, identity=dict(folder='synthetic', session='synthetic'))
    screened = Screen(tuple(accepted), (), 0, 0, 0, Fraction(len(accepted)), Fraction(0), ())
    with tempfile.TemporaryDirectory() as directory, \
            patch('research.clock_models.replay_causal_provider.load_run', return_value=data), \
            patch('research.clock_models.replay_causal_provider.screen', return_value=screened), \
            patch('research.clock_models.replay_causal_provider._revision', return_value={}), \
            patch('research.clock_models.replay_causal_provider._lines',
                  side_effect=lambda p: live if p.name == 'live-observer.jsonl' else receipts):
        return replay_run(Path(directory), mode)


class ReplayV3Tests(unittest.TestCase):
    def test_v3_mode_names(self):
        self.assertEqual(V3_MODES, ('settle-v3', 'causal-v3', 'wander'))

    def test_causal_v3_uses_arrival_availability_and_the_jump_allowance(self):
        v3, v2 = run_mode('causal-v3'), run_mode('causal-arrival')
        self.assertEqual(v3['jump_us'], str(DEFAULT_JUMP_US))
        self.assertEqual(v2['jump_us'], '0')
        self.assertEqual(v3['provider_policy_version'], PROVIDER_POLICY_VERSION)
        self.assertEqual(v3['availability_rule'], v2['availability_rule'])
        self.assertEqual(Fraction(v3['max_half_width_before_next_sample_exact']),
                         Fraction(v2['max_half_width_before_next_sample_exact']) + DEFAULT_JUMP_US)
        self.assertEqual(v3['incompatible'], [])

    def test_settle_v3_reports_its_policy(self):
        result = run_mode('settle-v3')
        self.assertEqual(result['settle']['settlement_policy_version'], SETTLEMENT_POLICY_VERSION_V3)
        self.assertEqual(result['settle']['states'], dict(settled=result['settle']['events']))

    def test_wander_mode_reports_holdout(self):
        result = run_mode('wander')['wander']
        self.assertEqual(result['policy_version'], WANDER_POLICY_VERSION)
        self.assertEqual(result['holdout_violations'], 0)
        self.assertLess(result['model_half_width_us']['median'], result['guaranteed_half_width_us']['median'])


class ReplayWanderTests(unittest.TestCase):
    def test_grid_replay_reports_both_layers_and_holdout(self):
        items = available(30)
        result = replay_wander(items, HZ, items[0].lower_qpc, items[-1].available_qpc, wander_ppm=2, jump_us=0)
        self.assertEqual(result['holdout_violations'], 0)
        self.assertGreater(result['holdout_checked'], 20)
        self.assertGreater(result['guaranteed_tracking_share'], 0.9)
        self.assertLess(result['model_half_width_us']['median'], result['guaranteed_half_width_us']['median'])
        self.assertEqual(result['queries'], sum(result['guaranteed_states'].values()))
        with self.assertRaises(ValueError):
            replay_wander(items, HZ, 5, 5, wander_ppm=2)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest discover -s tests -p test_replay_v3.py -v`
Expected: ERROR, `ImportError: cannot import name 'PROVIDER_POLICY_VERSION'` if Task 1 is missing, otherwise `cannot import name 'V3_MODES'`.

- [ ] **Step 3: Implement**

Create `research/clock_models/replay_wander.py`:

```python
"""Grid replay of the guaranteed provider beside the learned-rate model. Offline only.

Queries run on a fixed QPC grid; samples are ingested in availability order before
any query at or after their availability. Each model check happens before ingest
(out of sample), so holdout violations measure the declared learned-rate assumption.
"""
from __future__ import annotations

from fractions import Fraction

from research.clock_models.causal_provider import AvailableSample
from research.clock_models.wander_provider import WANDER_POLICY_VERSION, WanderProvider

GRID_STEP_S = Fraction(1, 10)


def _quantiles(values: list[Fraction]) -> dict | None:
    if not values:
        return None
    ordered = sorted(values)
    pick = lambda share: ordered[max(0, -(-share.numerator * len(ordered) // share.denominator) - 1)]
    return dict(median=round(float(pick(Fraction(1, 2))), 3), p90=round(float(pick(Fraction(9, 10))), 3),
                p99=round(float(pick(Fraction(99, 100))), 3), max=round(float(ordered[-1]), 3))


def replay_wander(items: list[AvailableSample], qpc_hz: int, start: int, end: int, *, wander_ppm: int,
                  jump_us=0, rate_prior_ppm: int = 200, threshold_us: int = 1_000) -> dict:
    if not start < end:
        raise ValueError('Empty replay interval')
    provider = WanderProvider(qpc_hz, wander_ppm=wander_ppm, rate_prior_ppm=rate_prior_ppm,
                              threshold_us=threshold_us, jump_us=jump_us)
    order = sorted(items, key=lambda s: (s.available_qpc, s.lower_qpc, s.sequence))
    step = int(GRID_STEP_S * qpc_hz)
    states_g: dict[str, int] = {}
    states_m: dict[str, int] = {}
    widths_g, widths_m, holdout, index = [], [], [], 0
    for query in range(start, end, step):
        while index < len(order) and order[index].available_qpc <= query:
            item = order[index]
            verdict = provider.check_model(item)
            if verdict is not None:
                holdout.append(dict(sequence=item.sequence, compatible=verdict))
            provider.ingest(item)
            index += 1
        result = provider.estimate(query)
        states_g[result.guaranteed.state] = states_g.get(result.guaranteed.state, 0) + 1
        states_m[result.state] = states_m.get(result.state, 0) + 1
        if result.guaranteed.half_width_us is not None:
            widths_g.append(result.guaranteed.half_width_us)
        if result.half_width_us is not None:
            widths_m.append(result.half_width_us)
    total = sum(states_g.values())
    violations = [h['sequence'] for h in holdout if not h['compatible']]
    return dict(label='grid replay: guaranteed rate-only provider and labeled learned-rate model',
                policy_version=WANDER_POLICY_VERSION, wander_ppm=wander_ppm, jump_us=str(jump_us),
                grid_step_s=float(GRID_STEP_S), queries=total,
                guaranteed_states=states_g, model_states=states_m,
                guaranteed_tracking_share=round(states_g.get('tracking', 0) / total, 6),
                model_tracking_share=round(states_m.get('tracking', 0) / total, 6),
                guaranteed_half_width_us=_quantiles(widths_g), model_half_width_us=_quantiles(widths_m),
                holdout_checked=len(holdout), holdout_violations=len(violations),
                holdout_violation_sequences=violations[:50], conditions=list(provider.conditions))
```

Apply to `research/clock_models/replay_causal_provider.py`:

```diff
diff --git a/research/clock_models/replay_causal_provider.py b/research/clock_models/replay_causal_provider.py
index f92f85a..37ac6c5 100644
--- a/research/clock_models/replay_causal_provider.py
+++ b/research/clock_models/replay_causal_provider.py
@@ -21,13 +21,17 @@ import json
 import subprocess
 
 from research.clock_models.analyze_bound_run import _lines, load_run
-from research.clock_models.causal_provider import CONDITIONS, ROUNDING_ALLOWANCE_US, AvailableSample, CausalProvider
-from research.clock_models.rate_bound import retrospective_max_half_width
+from research.clock_models.causal_provider import (CONDITIONS, PROVIDER_POLICY_VERSION, ROUNDING_ALLOWANCE_US,
+                                                   AvailableSample, CausalProvider)
+from research.clock_models.rate_bound import DEFAULT_JUMP_US, retrospective_max_half_width
 from research.clock_models.sample_screen import LISTEN_TIMEOUT_S, screen
-from research.clock_models.settle import settle_replay
+from research.clock_models.settle import INTERSECT_SPAN_S, settle_replay
+from research.clock_models.replay_wander import replay_wander
 
 ROOT = Path(__file__).resolve().parents[2]
 SETTLE_STEP_S = 1
+WANDER_PPM = 2
+V3_MODES = ('settle-v3', 'causal-v3', 'wander')
 SCREENING_LABEL = 'causal clock-model replay conditioned on offline sample screening'
 ARRIVAL_ORDER_POLICY_VERSION = 'wht/arrival-order-v2'
 AVAILABILITY_RULES = {
@@ -60,13 +64,13 @@ def availability(sample, mode: str, delay_seen: dict[int, int], completed: dict[
 
 
 def replay(events: list, qpc_hz: int, start: int, end: int, review_interval: tuple[int, int] | None = None,
-           rate_prior_ppm: int = 200, threshold_us: int = 1_000) -> dict:
+           rate_prior_ppm: int = 200, threshold_us: int = 1_000, jump_us=0) -> dict:
     """Feed accepted/rejected samples and continuity diagnostics by their availability.
 
     Simultaneously available samples use capture order as a tie-break only. Skips
     preserve original availability, elapsed denominators and already-issued history.
     """
-    provider = CausalProvider(qpc_hz, rate_prior_ppm, threshold_us)
+    provider = CausalProvider(qpc_hz, rate_prior_ppm, threshold_us, jump_us)
     segments, t = [], start
     incompatible, rejected_checked, ingested = [], [], 0
     late_history_skipped = []
@@ -166,7 +170,8 @@ def replay(events: list, qpc_hz: int, start: int, end: int, review_interval: tup
                                                         str(worst_uncertainty_before_next)),
                stale_interval_count=len(stale_runs),
                longest_stale_s=round(float(max(stale_runs) / qpc_hz), 6) if stale_runs else 0.0,
-               conditions=list(CONDITIONS))
+               provider_policy_version=PROVIDER_POLICY_VERSION, jump_us=str(jump_us),
+               conditions=list(provider.conditions))
     if review_interval is not None:
         lo, hi = review_interval
         window = durations(lo, hi)
@@ -224,6 +229,20 @@ def replay_run(folder: Path, mode: str) -> dict:
                     conditions=list(CONDITIONS))
         return meta
     completed = {r['sequence']: r['qpc_request_completed'] for r in _lines(folder / 'requests.jsonl')}
+    if mode in ('settle-v3', 'wander'):
+        delay_seen = arrival_map(_lines(folder / 'live-observer.jsonl'))
+        items = [AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
+                                 availability(s, 'causal-arrival', delay_seen, completed)) for s in accepted]
+        meta['availability_rule'] = AVAILABILITY_RULES['causal-arrival']
+        if mode == 'settle-v3':
+            meta.update(label='two-phase settled timestamps (v3) conditioned on offline sample screening',
+                        settle=settle_replay(items, hz, step_qpc=SETTLE_STEP_S * hz, jump_us=DEFAULT_JUMP_US,
+                                             intersect_span_s=INTERSECT_SPAN_S))
+            return meta
+        start = data['requests'][0].lower_qpc
+        end = data['requests'][-1].lower_qpc + LISTEN_TIMEOUT_S * hz
+        meta.update(wander=replay_wander(items, hz, start, end, wander_ppm=WANDER_PPM, jump_us=DEFAULT_JUMP_US))
+        return meta
     if mode == 'settle':
         delay_seen = arrival_map(_lines(folder / 'live-observer.jsonl'))
         items = [AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
@@ -247,6 +266,8 @@ def replay_run(folder: Path, mode: str) -> dict:
                         'overlapping capture windows or out-of-order arrival; legacy field aliases the '
                         'retrospective consecutive-pair maximum, not the actual settled grid maximum'))
         return meta
+    jump_us = DEFAULT_JUMP_US if mode == 'causal-v3' else 0
+    mode = 'causal-arrival' if mode == 'causal-v3' else mode
     delay_seen = arrival_map(_lines(folder / 'live-observer.jsonl')) if mode == 'causal-arrival' else {}
     events = [('accepted', None, AvailableSample(s.sequence, s.tsf_us, s.lower_qpc, s.upper_qpc,
                                                   availability(s, mode, delay_seen, completed))) for s in accepted]
@@ -283,17 +304,19 @@ def replay_run(folder: Path, mode: str) -> dict:
     meta['availability_rule'] = AVAILABILITY_RULES[mode]
     meta['rejected_uncheckable'] = rejected_uncheckable
     review_interval = (available[0], available[-1]) if len(available) >= 2 and available[0] < available[-1] else None
-    meta.update(replay(events, hz, start, end, review_interval))
+    meta.update(replay(events, hz, start, end, review_interval, jump_us=jump_us))
     return meta
 
 
 def main() -> int:
     parser = argparse.ArgumentParser(description=__doc__)
     parser.add_argument('folder', type=Path)
-    parser.add_argument('--mode', choices=('retrospective', 'settle', 'causal-etw', 'causal-arrival', 'all'), default='all')
+    parser.add_argument('--mode', choices=('retrospective', 'settle', 'causal-etw', 'causal-arrival', 'all',
+                                           *V3_MODES, 'v3'), default='all')
     args = parser.parse_args()
     try:
-        modes = ('retrospective', 'settle', 'causal-etw', 'causal-arrival') if args.mode == 'all' else (args.mode,)
+        modes = {'all': ('retrospective', 'settle', 'causal-etw', 'causal-arrival'), 'v3': V3_MODES}.get(
+            args.mode, (args.mode,))
         print(json.dumps({mode: replay_run(args.folder, mode) for mode in modes}, indent=2))
         return 0
     except (OSError, ValueError, KeyError, TypeError) as error:
```

- [ ] **Step 4: Run the tests and the CLI**

Run: `python -m unittest discover -s tests -p test_replay_v3.py`, then `-p test_replay_causal_provider.py` and `-p test_tsf_headlines.py`.
Then: `python research/clock_models/replay_causal_provider.py --help`
Expected: tests `OK`; help lists `settle-v3,causal-v3,wander,v3`; `python research/evidence/sync_tsf_headlines.py --check` exits 0.

- [ ] **Step 5: Refresh the index and commit**

```bash
python research/evidence/build_knowledge_index.py --write
git add research/clock_models/replay_wander.py research/clock_models/replay_causal_provider.py tests/test_replay_v3.py docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Replay recorded runs under the v3 settlement, provider and learned-rate policies"
```

---

### Task 5: ETW flush binding

**Files:**
- Create: `research/acquisition/etw_flush.py`
- Test: `tests/test_etw_flush.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `EVENT_TRACE_CONTROL_FLUSH == 3`; ctypes structures `WnodeHeader`, `EventTraceProperties` (120 bytes on 64-bit), `PropertiesBuffer`; `TraceFlusher(session, now, *, live=False, api=None)` with `flush() -> dict(started_qpc, finished_qpc, status, events_lost, realtime_buffers_lost)`.

Field types are fixed-width (`c_uint32`, not `c_ulong`) so the layout is the same on the Linux CI runner and Windows. A nonzero status is returned, never raised: the session's one-second timer still delivers, so a failed flush only costs latency, and the status is kept as evidence. The binding was checked on Windows: a missing session returns 4201 and a protected session returns 5 (access denied) when not elevated; each call takes about 50 us.

- [ ] **Step 1: Write the failing test**

Create `tests/test_etw_flush.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ctypes as ct
import unittest
from research.acquisition.etw_flush import (EVENT_TRACE_CONTROL_FLUSH, EventTraceProperties, PropertiesBuffer,
                                            TraceFlusher)


class FakeAdvapi:
    def __init__(self, status):
        self.status, self.calls = status, []

    def ControlTraceW(self, handle, name, properties, code):
        buffer = ct.cast(properties, ct.POINTER(PropertiesBuffer)).contents
        self.calls.append((handle, name, code, buffer.p.Wnode.BufferSize, buffer.p.LoggerNameOffset))
        buffer.p.EventsLost = 0
        return self.status


class TraceFlusherTests(unittest.TestCase):
    def test_properties_layout_matches_evntrace_h_on_64_bit(self):
        if ct.sizeof(ct.c_void_p) != 8:
            self.skipTest('64-bit layout')
        self.assertEqual(ct.sizeof(EventTraceProperties), 120)
        self.assertEqual(EventTraceProperties.LoggerThreadId.offset, 104)
        self.assertEqual(PropertiesBuffer.name.offset, 120)

    def test_flush_calls_control_trace_with_named_session_and_records_qpc(self):
        api, ticks = FakeAdvapi(0), iter((10, 25))
        receipt = TraceFlusher('WifiBound-abc', lambda: next(ticks), api=api).flush()
        self.assertEqual(api.calls, [(0, 'WifiBound-abc', EVENT_TRACE_CONTROL_FLUSH, ct.sizeof(PropertiesBuffer), 120)])
        self.assertEqual(receipt, dict(started_qpc=10, finished_qpc=25, status=0, events_lost=0,
                                       realtime_buffers_lost=0))

    def test_failed_flush_is_returned_not_raised(self):
        receipt = TraceFlusher('WifiBound-abc', lambda: 1, api=FakeAdvapi(4201)).flush()
        self.assertEqual(receipt['status'], 4201)

    def test_live_selection_is_explicit(self):
        with self.assertRaises(ValueError):
            TraceFlusher('WifiBound-abc', lambda: 1)
        with self.assertRaises(ValueError):
            TraceFlusher('', lambda: 1, api=FakeAdvapi(0))


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest discover -s tests -p test_etw_flush.py -v`
Expected: ERROR, `ModuleNotFoundError: No module named 'research.acquisition.etw_flush'`.

- [ ] **Step 3: Implement**

Create `research/acquisition/etw_flush.py`:

```python
"""Explicit flush of the campaign's real-time ETW session; no session control on import.

Real-time consumers receive events only when a buffer is flushed, and the minimum
flush timer is one second, so a report group can wait one to two seconds for delivery.
ControlTraceW(EVENT_TRACE_CONTROL_FLUSH) delivers non-empty buffers now. A failed flush
is evidence, not a run failure: the session's one-second timer still delivers.
"""
from __future__ import annotations

import ctypes as ct
import os

EVENT_TRACE_CONTROL_FLUSH = 3
NAME_CHARS = 1024


class WnodeHeader(ct.Structure):
    _fields_ = [('BufferSize', ct.c_uint32), ('ProviderId', ct.c_uint32), ('HistoricalContext', ct.c_uint64),
                ('TimeStamp', ct.c_int64), ('Guid', ct.c_ubyte * 16), ('ClientContext', ct.c_uint32),
                ('Flags', ct.c_uint32)]


class EventTraceProperties(ct.Structure):
    _fields_ = [('Wnode', WnodeHeader), ('BufferSize', ct.c_uint32), ('MinimumBuffers', ct.c_uint32),
                ('MaximumBuffers', ct.c_uint32), ('MaximumFileSize', ct.c_uint32), ('LogFileMode', ct.c_uint32),
                ('FlushTimer', ct.c_uint32), ('EnableFlags', ct.c_uint32), ('AgeLimit', ct.c_int32),
                ('NumberOfBuffers', ct.c_uint32), ('FreeBuffers', ct.c_uint32), ('EventsLost', ct.c_uint32),
                ('BuffersWritten', ct.c_uint32), ('LogBuffersLost', ct.c_uint32),
                ('RealTimeBuffersLost', ct.c_uint32), ('LoggerThreadId', ct.c_void_p),
                ('LogFileNameOffset', ct.c_uint32), ('LoggerNameOffset', ct.c_uint32)]


class PropertiesBuffer(ct.Structure):
    # UTF-16 name storage sized in bytes so the layout is identical on every host.
    _fields_ = [('p', EventTraceProperties), ('name', ct.c_uint16 * NAME_CHARS), ('file', ct.c_uint16 * NAME_CHARS)]


class TraceFlusher:
    def __init__(self, session: str, now, *, live: bool = False, api=None):
        if not session or len(session) >= NAME_CHARS:
            raise ValueError('Session name required and shorter than 1024 characters')
        if api is None:
            if not live or os.name != 'nt':
                raise ValueError('Explicit Windows live selection required')
            api = ct.WinDLL('advapi32')
            api.ControlTraceW.argtypes = [ct.c_uint64, ct.c_wchar_p, ct.POINTER(EventTraceProperties), ct.c_uint32]
            api.ControlTraceW.restype = ct.c_uint32
        self.session, self.now, self.api = session, now, api

    def flush(self) -> dict:
        buffer = PropertiesBuffer()
        buffer.p.Wnode.BufferSize = ct.sizeof(PropertiesBuffer)
        buffer.p.LoggerNameOffset = PropertiesBuffer.name.offset
        buffer.p.LogFileNameOffset = PropertiesBuffer.file.offset
        started = self.now()
        status = int(self.api.ControlTraceW(0, self.session, ct.cast(ct.pointer(buffer), ct.POINTER(EventTraceProperties)),
                                            EVENT_TRACE_CONTROL_FLUSH))
        finished = self.now()
        return dict(started_qpc=started, finished_qpc=finished, status=status,
                    events_lost=buffer.p.EventsLost, realtime_buffers_lost=buffer.p.RealTimeBuffersLost)
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest discover -s tests -p test_etw_flush.py -v`
Expected: 4 tests, `OK`.

- [ ] **Step 5: Refresh the index and commit**

```bash
python research/evidence/build_knowledge_index.py --write
git add research/acquisition/etw_flush.py tests/test_etw_flush.py docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Add an explicit ETW session flush binding"
```

---

### Task 6: Flush during the campaign's report wait

**Files:**
- Create: `research/acquisition/report_wait.py`
- Modify: `research/acquisition/run_bound_campaign.py`
- Test: `tests/test_report_wait.py`, `tests/test_campaign_flush.py`

**Interfaces:**
- Consumes: `TraceFlusher` from Task 5.
- Produces: `wait_for_report(arrived, *, pump, monotonic, sleep, flush=None, listen_s=5.0, retry_s=0.05, max_flushes=3) -> list[dict]`; `run_bound_campaign.sampler_plan(args) -> dict` (adds `etw_flush_after_completion`); CLI flag `--etw-flush` (persistent sampler only); each `sampler-schedule.jsonl` row gains `etw_flushes`.

The helper replaces the inline listen loop with identical behavior when `flush` is `None`: pump, poll every 5 ms, stop at report or after `LISTEN_TIMEOUT_S`. With a flusher it flushes at once (the caller enters after terminal completion, which the driver logs after the report), then retries every 50 ms up to three times. The flag is opt-in and recorded in the plan before any request, so earlier run profiles stay reproducible and every run says which delivery mode it used.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_report_wait.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from research.acquisition.report_wait import wait_for_report


class FakeTime:
    def __init__(self):
        self.t = 100.0

    def monotonic(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds


class ReportWaitTests(unittest.TestCase):
    def test_flushes_immediately_then_stops_when_report_arrives(self):
        clock, calls = FakeTime(), []
        arrived = lambda: len(calls) >= 1 and clock.t >= 100.01
        flushes = wait_for_report(arrived, pump=lambda: None, monotonic=clock.monotonic, sleep=clock.sleep,
                                  flush=lambda: calls.append(clock.t) or dict(status=0))
        self.assertEqual(calls, [100.0])
        self.assertEqual(flushes, [dict(status=0)])
        self.assertLess(clock.t, 100.05)

    def test_retries_at_most_max_flushes_then_listens_until_timeout(self):
        clock, calls = FakeTime(), []
        flushes = wait_for_report(lambda: False, pump=lambda: None, monotonic=clock.monotonic, sleep=clock.sleep,
                                  flush=lambda: calls.append(clock.t) or dict(status=0), listen_s=1.0)
        self.assertEqual(len(flushes), 3)
        self.assertGreaterEqual(calls[1] - calls[0], 0.05)
        self.assertGreaterEqual(clock.t, 101.0)

    def test_without_flush_behaves_like_the_retained_wait(self):
        clock, pumps = FakeTime(), []
        arrived = lambda: clock.t >= 100.5
        flushes = wait_for_report(arrived, pump=lambda: pumps.append(clock.t), monotonic=clock.monotonic,
                                  sleep=clock.sleep)
        self.assertEqual(flushes, [])
        self.assertTrue(pumps)
        self.assertGreaterEqual(clock.t, 100.5)

    def test_rejects_invalid_bounds(self):
        for kwargs in (dict(listen_s=0), dict(retry_s=0), dict(max_flushes=-1)):
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                wait_for_report(lambda: True, pump=lambda: None, monotonic=lambda: 0.0, sleep=lambda s: None, **kwargs)


if __name__ == '__main__':
    unittest.main()
```

Create `tests/test_campaign_flush.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contextlib
import io
import unittest
from research.acquisition.run_bound_campaign import parse, sampler_plan

BASE = ['--if-index', '5', '--condition', 'idle']


class CampaignFlushTests(unittest.TestCase):
    def test_flush_is_opt_in_and_recorded_in_the_plan(self):
        self.assertEqual(sampler_plan(parse(BASE)), {})
        plain = sampler_plan(parse(BASE + ['--sampler', 'persistent']))
        flushed = sampler_plan(parse(BASE + ['--sampler', 'persistent', '--etw-flush']))
        self.assertIs(plain['etw_flush_after_completion'], False)
        self.assertIs(flushed['etw_flush_after_completion'], True)
        self.assertEqual({k: v for k, v in flushed.items() if k != 'etw_flush_after_completion'},
                         {k: v for k, v in plain.items() if k != 'etw_flush_after_completion'})

    def test_flush_requires_the_persistent_sampler(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parse(BASE + ['--etw-flush'])


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m unittest discover -s tests -p test_report_wait.py -v` and `-p test_campaign_flush.py -v`
Expected: ERROR, `No module named 'research.acquisition.report_wait'`; then `cannot import name 'sampler_plan'`.

- [ ] **Step 3: Implement**

Create `research/acquisition/report_wait.py`:

```python
"""Bounded wait for a request's report group, optionally forcing ETW delivery. No device access."""
from __future__ import annotations

from typing import Callable

LISTEN_S = 5.0
POLL_S = 0.005
FLUSH_RETRY_S = 0.05
MAX_FLUSHES = 3


def wait_for_report(arrived: Callable[[], bool], *, pump: Callable[[], None], monotonic: Callable[[], float],
                    sleep: Callable[[float], None], flush: Callable[[], dict] | None = None,
                    listen_s: float = LISTEN_S, retry_s: float = FLUSH_RETRY_S, max_flushes: int = MAX_FLUSHES) -> list[dict]:
    """Pump until the report arrives or listen_s passes; flush first, then every retry_s up to max_flushes.

    The first flush is issued immediately because the caller enters after terminal I/O
    completion, which the driver logs after the report. Returns the flush receipts.
    """
    if listen_s <= 0 or retry_s <= 0 or type(max_flushes) is not int or max_flushes < 0:
        raise ValueError('Invalid report-wait bounds')
    flushes: list[dict] = []
    start = monotonic()
    next_flush = start
    while not arrived() and monotonic() - start < listen_s:
        if flush is not None and len(flushes) < max_flushes and monotonic() >= next_flush:
            flushes.append(flush())
            next_flush = monotonic() + retry_s
        pump()
        if arrived():
            break
        sleep(POLL_S)
    return flushes
```

Apply to `research/acquisition/run_bound_campaign.py`:

```diff
diff --git a/research/acquisition/run_bound_campaign.py b/research/acquisition/run_bound_campaign.py
index 6a2e6cf..2319534 100644
--- a/research/acquisition/run_bound_campaign.py
+++ b/research/acquisition/run_bound_campaign.py
@@ -28,6 +28,7 @@ import uuid
 from research.acquisition.campaign_admission import Admission, transition
 from research.acquisition.campaign_gate import ReportGate
 from research.acquisition.persistent_sampler import record_quarantine
+from research.acquisition.report_wait import wait_for_report
 from research.clock_models.sample_screen import LISTEN_TIMEOUT_S, MAX_WINDOW_US, TIMING_KINDS
 
 MARKER_NAME = 'bound-campaign-quarantine.json'
@@ -349,6 +350,8 @@ def parse(argv: list[str] | None = None) -> argparse.Namespace:
     parser.add_argument('--duration-s', type=int, default=3600)
     parser.add_argument('--sampler', choices=('per-request', 'persistent'), default='per-request')
     parser.add_argument('--spacing-s', type=float, default=None)
+    parser.add_argument('--etw-flush', action='store_true',
+                        help='Persistent only: flush the trace session after each completion to deliver reports')
     parser.add_argument('--execute', action='store_true', help='Send private requests; default is preview only')
     parser.add_argument('--workload', nargs=3, metavar=('STOP', 'OUTPUT', 'SECONDS'), help=argparse.SUPPRESS)
     args = parser.parse_args(argv)
@@ -361,9 +364,19 @@ def parse(argv: list[str] | None = None) -> argparse.Namespace:
             parser.error('--duration-s must be 60 to 3600')
         if not 0.5 <= args.spacing_s <= 60:
             parser.error('--spacing-s must be 0.5 to 60')
+        if args.etw_flush and args.sampler != 'persistent':
+            parser.error('--etw-flush requires --sampler persistent')
     return args
 
 
+def sampler_plan(args: argparse.Namespace) -> dict:
+    """Plan fields that change acquisition behavior; recorded before any request."""
+    if args.sampler != 'persistent':
+        return {}
+    return dict(sampler='persistent', identity_every=None, identity_every_s=30, report_wait_retained=True,
+                etw_flush_after_completion=args.etw_flush)
+
+
 def campaign(args: argparse.Namespace) -> int:
     from research.acquisition.bss_reader import BssReader, CacheEntryUnavailable
     from research.acquisition.run_acquisition_campaign import (PROVIDER, ROOT, Clock, Observer, TraceOwner,
@@ -377,8 +390,7 @@ def campaign(args: argparse.Namespace) -> int:
     plan = dict(condition=args.condition, duration_s=args.duration_s, spacing_s=args.spacing_s, action=4,
                 provider=PROVIDER, trace_cap_bytes=TRACE_CAP_BYTES, identity_every=IDENTITY_EVERY,
                 beacon_every_s=BEACON_EVERY_S, own_loss_limit=OWN_LOSS_LIMIT, marker=str(marker))
-    if args.sampler == 'persistent':
-        plan.update(sampler='persistent', identity_every=None, identity_every_s=30, report_wait_retained=True)
+    plan.update(sampler_plan(args))
     if not args.execute:
         print(json.dumps(dict(preview=True, plan=plan, adapter_status=baseline['Status'],
                               driver_version=baseline['DriverVersion']), indent=2))
@@ -436,6 +448,10 @@ def _execute(args: argparse.Namespace, clock, baseline: dict, plan: dict, marker
                                        in_progress_path(ROOT / 'artifacts', baseline['InterfaceGuid']),
                                        clock, observer, gate)
             sampler.start()
+        flusher = None
+        if persistent and args.etw_flush:
+            from research.acquisition.etw_flush import TraceFlusher
+            flusher = TraceFlusher(session, clock.now, live=True)
         reader = BssReader(baseline['InterfaceGuid'])
         if args.condition == 'load':
             worker = subprocess.Popen([sys.executable, __file__, '--workload', str(folder / 'workload-stop'),
@@ -496,13 +512,16 @@ def _execute(args: argparse.Namespace, clock, baseline: dict, plan: dict, marker
                 requests_file.write(json.dumps(receipt) + '\n')
                 requests_file.flush()
                 receipts.append(receipt)
-                listen_end = time.monotonic() + LISTEN_TIMEOUT_S
                 listen_started_qpc = clock.now() if persistent else None
-                while not gate.report_after(receipt['qpc_request_before']) and time.monotonic() < listen_end:
+
+                def pump() -> None:
                     if persistent:
                         sampler.pulse()
                     observer.pump(gate)
-                    time.sleep(0.005)
+                flushes = wait_for_report(lambda: gate.report_after(receipt['qpc_request_before']), pump=pump,
+                                          monotonic=time.monotonic, sleep=time.sleep,
+                                          flush=flusher.flush if flusher is not None else None,
+                                          listen_s=LISTEN_TIMEOUT_S)
                 if not gate.report_in_window(receipt['qpc_request_before'], clock.frequency):
                     losses += 1
                 if loss_budget_exceeded(losses, number):
@@ -518,7 +537,7 @@ def _execute(args: argparse.Namespace, clock, baseline: dict, plan: dict, marker
                         report_wait_started_qpc=listen_started_qpc, report_wait_finished_qpc=clock.now(),
                         identity_checked=checked_identity, identity_started_qpc=identity_started,
                         identity_finished_qpc=identity_finished, slot_identity_checks=slot_identity_checks,
-                        processing_finished_qpc=clock.now(),
+                        processing_finished_qpc=clock.now(), etw_flushes=flushes,
                         actual_spacing_s=((receipt['qpc_request_before'] - previous_submission) / clock.frequency
                                           if previous_submission is not None else None))) + '\n')
                     schedule_file.flush()
```

- [ ] **Step 4: Run the tests and the preview path**

Run: `python -m unittest discover -s tests -p test_report_wait.py`, `-p test_campaign_flush.py`, `-p test_bound_campaign.py`, `-p test_persistent_controller.py`, `-p test_acquisition_corrections.py`.
Then: `python research/acquisition/run_bound_campaign.py --help`
Expected: all `OK`; help shows `--etw-flush`. Do not run the campaign itself.

- [ ] **Step 5: Refresh the index and commit**

```bash
python research/evidence/build_knowledge_index.py --write
git add research/acquisition/report_wait.py research/acquisition/run_bound_campaign.py tests/test_report_wait.py tests/test_campaign_flush.py docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Flush the trace session during the persistent report wait when requested"
```

---

### Task 7: Sub-millisecond acceptance evaluator

**Files:**
- Create: `research/clock_models/sub_ms_acceptance.py`
- Test: `tests/test_sub_ms_acceptance.py`

**Interfaces:**
- Consumes: `replay_run`, `V3_MODES`, `arrival_map` (Task 4); `load_run`, `_lines`; `screen`.
- Produces: `CRITERIA` (dict of eight limits, names ending `_min` or `_max`); `ACCEPTANCE_VERSION == 'wht/sub-ms-acceptance-v1'`; `run_timing(folder) -> dict(spacing_s, accepted, delivery_missing, delivery_s{median,p99,max}, accepted_gap_s{median,max})`; `evaluate(replays, timing, criteria=CRITERIA) -> dict(schema, passed, checks[{name, value, limit, passed}], scope)`; CLI exiting 0 on pass, 2 on fail, 1 on rejected input.

The criteria are the Targets table's acceptance limits. One test feeds today's smoke numbers and expects exactly four failures (coverage, settled width, delivery and cadence), which documents why the current setup does not pass.

- [ ] **Step 1: Write the failing test**

Create `tests/test_sub_ms_acceptance.py`:

```python
import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import unittest
from research.clock_models.sub_ms_acceptance import CRITERIA, evaluate

PASSING = {
    'causal-v3': dict(coverage_declared=0.9991, incompatible=[]),
    'settle-v3': dict(settle=dict(sub_millisecond_share=1.0, half_width_us=dict(median=199.1))),
    'wander': dict(wander=dict(model_half_width_us=dict(median=148.3), holdout_violations=0)),
}
TIMING = dict(spacing_s=1.0, delivery_s=dict(median=0.006, p99=0.012, max=0.05),
              accepted_gap_s=dict(median=1.004, max=3.1))


class AcceptanceTests(unittest.TestCase):
    def test_passing_run(self):
        result = evaluate(PASSING, TIMING)
        self.assertTrue(result['passed'])
        self.assertEqual([c['name'] for c in result['checks']], list(CRITERIA))

    def test_each_criterion_can_fail_alone(self):
        breaks = {
            'guaranteed_live_coverage_min': lambda r, t: r['causal-v3'].update(coverage_declared=0.93),
            'incompatible_max': lambda r, t: r['causal-v3'].update(incompatible=[dict(sequence=4)]),
            'settled_sub_ms_share_min': lambda r, t: r['settle-v3']['settle'].update(sub_millisecond_share=0.99),
            'settled_median_max_us': lambda r, t: r['settle-v3']['settle']['half_width_us'].update(median=281.0),
            'model_median_max_us': lambda r, t: r['wander']['wander']['model_half_width_us'].update(median=200.0),
            'model_holdout_violations_max': lambda r, t: r['wander']['wander'].update(holdout_violations=1),
            'delivery_p99_max_s': lambda r, t: t['delivery_s'].update(p99=1.9),
            'median_gap_ratio_max': lambda r, t: t['accepted_gap_s'].update(median=2.005),
        }
        self.assertEqual(set(breaks), set(CRITERIA))
        for name, mutate in breaks.items():
            replays, timing = copy.deepcopy(PASSING), copy.deepcopy(TIMING)
            mutate(replays, timing)
            result = evaluate(replays, timing)
            with self.subTest(criterion=name):
                self.assertFalse(result['passed'])
                self.assertEqual([c['name'] for c in result['checks'] if not c['passed']], [name])

    def test_todays_smoke_numbers_fail_on_delivery_cadence_and_width(self):
        today = copy.deepcopy(PASSING)
        today['causal-v3']['coverage_declared'] = 0.92884
        today['settle-v3']['settle']['half_width_us']['median'] = 280.429
        timing = dict(spacing_s=1.0, delivery_s=dict(median=1.486, p99=1.999, max=2.167),
                      accepted_gap_s=dict(median=2.005, max=4.009))
        failed = {c['name'] for c in evaluate(today, timing)['checks'] if not c['passed']}
        self.assertEqual(failed, {'guaranteed_live_coverage_min', 'settled_median_max_us', 'delivery_p99_max_s',
                                  'median_gap_ratio_max'})


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m unittest discover -s tests -p test_sub_ms_acceptance.py -v`
Expected: ERROR, `No module named 'research.clock_models.sub_ms_acceptance'`.

- [ ] **Step 3: Implement**

Create `research/clock_models/sub_ms_acceptance.py`:

```python
"""Sub-millisecond acceptance for one recorded run under the v3 policies. Offline only.

Passing is conditional research evidence for the declared assumptions; it is not
calibrated AP/UTC accuracy and does not prove where inside its window a TSF was read.
"""
from __future__ import annotations

import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
from fractions import Fraction
import json
import statistics

from research.clock_models.analyze_bound_run import _lines, load_run
from research.clock_models.replay_causal_provider import V3_MODES, arrival_map, replay_run
from research.clock_models.sample_screen import screen

ACCEPTANCE_VERSION = 'wht/sub-ms-acceptance-v1'
CRITERIA = dict(
    guaranteed_live_coverage_min=0.995,   # causal-v3 coverage_declared
    incompatible_max=0,                   # causal-v3 incompatible samples
    settled_sub_ms_share_min=1.0,         # settle-v3 sub_millisecond_share
    settled_median_max_us=250,            # settle-v3 rate-only median half-width
    model_median_max_us=180,              # learned-rate model median half-width
    model_holdout_violations_max=0,       # out-of-sample learned-rate failures
    delivery_p99_max_s=0.1,               # report delay-record receipt after report timestamp
    median_gap_ratio_max=1.1,             # median accepted gap / requested spacing
)


def _p(values: list[float], share: Fraction) -> float:
    ordered = sorted(values)
    return ordered[max(0, -(-share.numerator * len(ordered) // share.denominator) - 1)]


def run_timing(folder: Path) -> dict:
    data = load_run(folder)
    hz = data['qpc_hz']
    accepted = list(screen(data['records'], data['requests'], hz).accepted)
    seen = arrival_map(_lines(folder / 'live-observer.jsonl'))
    delivery = [(seen[s.upper_qpc] - s.upper_qpc) / hz for s in accepted if s.upper_qpc in seen]
    gaps = [(b.lower_qpc - a.lower_qpc) / hz for a, b in zip(accepted, accepted[1:])]
    spacing = json.loads((folder / 'session.json').read_text(encoding='utf-8'))['Plan']['spacing_s']
    if not delivery or not gaps:
        raise ValueError('Run lacks delivery receipts or accepted gaps')
    return dict(spacing_s=spacing, accepted=len(accepted), delivery_missing=len(accepted) - len(delivery),
                delivery_s=dict(median=statistics.median(delivery), p99=_p(delivery, Fraction(99, 100)),
                                max=max(delivery)),
                accepted_gap_s=dict(median=statistics.median(gaps), max=max(gaps)))


def evaluate(replays: dict, timing: dict, criteria: dict = CRITERIA) -> dict:
    causal, settle, model = replays['causal-v3'], replays['settle-v3']['settle'], replays['wander']['wander']
    observed = dict(
        guaranteed_live_coverage_min=causal['coverage_declared'],
        incompatible_max=len(causal['incompatible']),
        settled_sub_ms_share_min=settle['sub_millisecond_share'],
        settled_median_max_us=settle['half_width_us']['median'],
        model_median_max_us=model['model_half_width_us']['median'],
        model_holdout_violations_max=model['holdout_violations'],
        delivery_p99_max_s=timing['delivery_s']['p99'],
        median_gap_ratio_max=timing['accepted_gap_s']['median'] / timing['spacing_s'],
    )
    checks = []
    for name, limit in criteria.items():
        value = observed[name]
        passed = value >= limit if name.endswith('_min') else value <= limit
        checks.append(dict(name=name, value=value, limit=limit, passed=passed))
    return dict(schema=ACCEPTANCE_VERSION, passed=all(c['passed'] for c in checks), checks=checks,
                scope='conditional research evidence under the declared v3 assumptions; not AP/UTC calibration')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    try:
        replays = {mode: replay_run(args.folder, mode) for mode in V3_MODES}
        result = evaluate(replays, run_timing(args.folder))
        print(json.dumps(dict(result, replays=replays), indent=2))
        return 0 if result['passed'] else 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'Acceptance rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and the full suite**

Run: `python -m unittest discover -s tests -p test_sub_ms_acceptance.py -v`, then `python research/clock_models/sub_ms_acceptance.py --help`, then the full CI sequence:

```bash
python -m compileall -q research tests
python -m unittest discover -s tests
python research/evidence/build_knowledge_index.py --write
python research/evidence/build_knowledge_index.py --check
python research/evidence/sync_workflow_diagrams.py --check
python research/evidence/publish_archify_previews.py --check
python research/evidence/sync_tsf_headlines.py --check
```

Expected: all pass. The suite grows by 36 tests (589 to 625 at `e6cd83a`).

- [ ] **Step 5: Commit**

```bash
git add research/clock_models/sub_ms_acceptance.py tests/test_sub_ms_acceptance.py docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Evaluate recorded runs against explicit sub-millisecond criteria"
```

---

### Task 8: Documentation

**Files:**
- Modify: `docs/clock-models/tsf-mathematics.md`
- Modify: `docs/acquisition/persistent-tsf-sampler.md`
- Modify: `research/clock_models/README.md`
- Modify: `docs/overview/README.md`

**Interfaces:**
- Consumes: names and versions from Tasks 1 to 7.
- Produces: documentation only.

- [ ] **Step 1: Add the v3 section to the mathematics reference**

In `docs/clock-models/tsf-mathematics.md`, insert immediately before the line `## What the current results mean`:

```markdown
## Version 3 policies

These policies are opt-in. Every historical default and published result is unchanged.

**Phase-jump allowance (`wht/causal-provider-v2`, `wht/settlement-v3`).** In an infrastructure network the station rewrites its TSF to the access point's beacon value, so the TSF is not a smooth rate-bounded trajectory at microsecond scale. The v3 envelope assumes only that over any interval the TSF advance lies within the rate prior times the elapsed QPC time, widened by `J` microseconds on each side:

    lower_i(Q) = T_i     - J + (a or b) * (Q - (U_i + 1))
    upper_i(Q) = T_i + 1 + J + (b or a) * (Q - L_i)

The default `J = 25` us is six 102.4 ms beacon periods at 40 ppm relative drift, rounded up. It is a declared prior, not a measurement, and adds `J` to every half-width.

**Nearby-sample settlement (`wht/settlement-v3`).** The bracket rule and settle time are unchanged. The result additionally intersects the envelope of every sample available by the reported cutoff whose window lies within 10 seconds of the event. A farther sample with a narrow window can be tighter than the nearest one with a wide window.

**Learned-rate model (`wht/wander-model-v1`).** A stronger, labeled assumption: across the trailing 60 seconds and the holdover to the query, the TSF rate stays within the exact constant-rate interval of the trailing samples widened by `wander_ppm` (default 2). A common offset exists for rate `r` exactly when every ordered sample pair satisfies `r * (L_j - U_i - 1) <= T_j - T_i + 1 + 2J`. The model interval is intersected with the guaranteed interval and never replaces it. Each new sample is first checked against the model (out of sample); any holdout violation is evidence that the assumption failed.

**Explicit ETW flush.** Real-time trace delivery waits for the one-second flush timer. With `--etw-flush` the persistent campaign calls `ControlTraceW(EVENT_TRACE_CONTROL_FLUSH)` after each completion, so a sample becomes available in milliseconds. Availability semantics (`A_i = max(D_i, C_i, U_i + 1)`) are unchanged; only `D_i` arrives sooner.

None of this narrows the capture window, which sets a floor of about half its width (about 127 us at the median smoke width). Locating the read point inside the window needs an independent reference or a different capture path.
```

- [ ] **Step 2: Document the flag in the sampler contract**

In `docs/acquisition/persistent-tsf-sampler.md`, insert after the paragraph that begins `Campaign exit 0 requires successful persisted outcome`:

```markdown
`--etw-flush` (persistent sampler only) flushes the trace session after each completed request so the report group reaches the observer in milliseconds instead of waiting for the one-second flush timer. The plan records `etw_flush_after_completion`, and each `sampler-schedule.jsonl` row records the flush receipts in `etw_flushes`. A failed flush is recorded, not fatal; delivery then falls back to the timer. The flag does not authorize a run.
```

- [ ] **Step 3: List the new tools**

In `research/clock_models/README.md`, add three rows to the Files table after the `settle.py` row. Run this from the repository root (each row links the file name to the file, matching the existing rows; the script assembles the links so that this plan does not itself contain links to files that do not exist yet):

```python
from pathlib import Path

rows = {
    'wander_provider.py': 'Exact constant-rate interval and the labeled learned-rate companion to the causal provider; '
                          'never replaces the guaranteed interval.',
    'replay_wander.py': 'Grid replay of guaranteed and learned-rate layers with out-of-sample holdout checks.',
    'sub_ms_acceptance.py': 'Pass/fail evaluation of one recorded run against the sub-millisecond criteria under the '
                            'v3 policies.',
}
path = Path('research/clock_models/README.md')
text = path.read_text(encoding='utf-8')
end = text.index('\n', text.index('| [settle.py]'))
added = ''.join('\n| [' + name + ']' + '(' + name + ') | ' + role + ' |' for name, role in rows.items())
path.write_text(text[:end] + added + text[end:], encoding='utf-8', newline='\n')
```

In `docs/overview/README.md`, add as the first item under `## Documents`:

```markdown
- [Sub-millisecond TSF timing: implementation plan](2026-10-09-sub-millisecond-plan.md).
```

(If this plan file is already listed there, skip that line.)

- [ ] **Step 4: Verify the documentation checks**

Run: `python -m unittest discover -s tests -p test_documentation_navigation.py`, then `python research/evidence/build_knowledge_index.py --write` and `--check`.
Expected: `OK` and `Unchanged`.

- [ ] **Step 5: Commit**

```bash
git add docs/clock-models/tsf-mathematics.md docs/acquisition/persistent-tsf-sampler.md research/clock_models/README.md docs/overview/README.md docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Document the v3 timing policies and the trace flush option"
```

---

### Task 9: Live qualification (gated; requires user authorization for each run)

**Files:**
- Create (after the runs): `docs/acquisition/sub-millisecond-qualification-<YYYY-MM-DD>.md` and a matching `.json` summary.

**Interfaces:**
- Consumes: everything above, the native observer and decoder artifacts described in [OPERATIONS.md](OPERATIONS.md), an elevated Windows session on the exact qualified adapter and driver.
- Produces: evidence only.

Stop and ask the user before every `--execute`. Confirm there is no quarantine marker and no unfinished-run record first; never remove one to proceed.

- [ ] **Step 1: Preview without requests**

```powershell
python research/acquisition/run_bound_campaign.py --sampler persistent --etw-flush --spacing-s 1.0 --if-index <INDEX> --condition idle --duration-s 300
```

Expected: a preview JSON whose `plan` contains `"etw_flush_after_completion": true`. No request is sent.

- [ ] **Step 2: Five-minute idle smoke (authorized run 1)**

Re-run Step 1's command with `--execute` only after the user approves. Then:

```powershell
python research/clock_models/sub_ms_acceptance.py artifacts/BoundCampaign-<ID>/idle
```

Expected: exit 0. If it fails, record which checks failed and stop; do not tune limits to pass. Check that every `etw_flushes` status is 0, and that `delivery_s.p99` fell from about 2 s to under 0.1 s.

- [ ] **Step 3: Hour-long idle and load runs (authorized runs 2 and 3)**

```powershell
python research/acquisition/run_bound_campaign.py --sampler persistent --etw-flush --spacing-s 1.0 --if-index <INDEX> --condition idle --duration-s 3600 --execute
python research/acquisition/run_bound_campaign.py --sampler persistent --etw-flush --spacing-s 1.0 --if-index <INDEX> --condition load --duration-s 3600 --execute
```

Run the acceptance evaluator on each folder. Also run `python research/clock_models/replay_causal_provider.py <folder> --mode all` so the v2 numbers stay comparable with the 2026-10-08 baseline.

- [ ] **Step 4: Publish the evidence**

Write the dated qualification page with: commands, plan JSON, source commit, input hashes (from the replay `inputs` field), every acceptance check value, v2 and v3 numbers side by side, flush status counts, and the unchanged limits (no AP/UTC calibration, read point inside the window unknown, jump allowance declared not measured). Add a line to [publication status](../research-history/publication-status.md). Updating the README headline (`sync_tsf_headlines.py`) is a separate reviewed change.

- [ ] **Step 5: Commit**

```bash
python research/evidence/build_knowledge_index.py --write
git add docs/acquisition/sub-millisecond-qualification-*.md docs/acquisition/sub-millisecond-qualification-*.json docs/research-history/publication-status.md docs/knowledge/research-index.json docs/knowledge/reference-index.md
git commit -m "Publish sub-millisecond qualification runs"
```

---

## Out of scope: toward microsecond accuracy

Every result above has a floor of about half the capture window. Getting below it needs one of these, each a research question before any implementation plan:

1. **Locate the read point.** Compare against an independent reference that timestamps the same physical event, for example a second, monitor-mode adapter timestamping the AP's beacons in its own TSF and QPC. A stable offset found that way would let the window collapse to a calibrated point plus a measured spread.
2. **A latched pair.** Find a firmware or driver path that reports a TSF together with a host-domain timestamp taken at the same instant (RX descriptor timestamps, a PTM-style cross-timestamp). The 2026-10-08 SoC-counter test found no fixed-rate relation to QPC, so that counter is not one.
3. **Measure the jump allowance.** With a narrower window, the beacon-adoption jumps become observable and `J` can be measured instead of declared.
4. **Trim host overhead in `L`.** `qpc_request_before` is read in Python before the ctypes call. Worth measuring once the window is narrow; negligible at 250 us.

# TSF-to-host bound: complete methodology and work record

This is the full record of how the sub-millisecond TSF bound was designed, built, tested and measured on 2026-10-07 and 2026-10-08. It lists every analysis, every live attempt with its measurements, every defect found and how each was diagnosed and fixed. The [results document](tsf-host-bound-results.md) gives the verdict; this page explains how it was reached so that another engineer can audit or repeat it.

## Contents

- [1. Objective and constraints](#1-objective-and-constraints)
- [2. Sequence of work](#2-sequence-of-work)
- [3. Checks on saved evidence before any new collection](#3-checks-on-saved-evidence-before-any-new-collection)
- [4. Measurement method](#4-measurement-method)
- [5. Software built and how it was verified](#5-software-built-and-how-it-was-verified)
- [6. Live procedure](#6-live-procedure)
- [7. Measurements from every attempt](#7-measurements-from-every-attempt)
- [8. Investigations and fixes](#8-investigations-and-fixes)
- [9. Work not done and stated limitations](#9-work-not-done-and-stated-limitations)
- [10. Environment, records and reproduction](#10-environment-records-and-reproduction)

**Terms:** **TSF** is the 802.11 microsecond timer a station keeps aligned to its access point. **QPC** is Windows `QueryPerformanceCounter` (10 MHz here). A **window** is the QPC interval in which one firmware TSF capture must have happened. The **proven half-width** is the worst-case TSF error at any instant of an analyzed span. **ETW** is Event Tracing for Windows. See the [glossary](../glossary.md).

## 1. Objective and constraints

- **Goal (user-selected):** the current Qualcomm FastConnect 7800 laptop tracks its associated access point's TSF with error below 1,000 us at a stated QPC instant.
- **Equipment (user decision):** the laptop and its existing consumer router only. No second node, GPS/PPS, wired reference, or shell access to the router.
- **Consequence:** the laptop-TSF to router-TSF step cannot be measured independently. The claim was split into a proven link (QPC to station TSF) and an assumed link (station TSF to access point TSF, by 802.11 station synchronization, with a coarse check).
- **Safety rules carried forward:** firmware action 4 only (never 3, 5 or 6); one request in flight; pinned driver hash; any stop writes a quarantine marker the tool never clears; elevation only by the user approving Windows UAC. The quarantined 2026-10-03 private campaign was not reopened or relabelled.

## 2. Sequence of work

1. **Review of prior work.** Read the Codex session records and the repository's current findings. The existing action-4 private request, live observer and trace decoder were identified as reusable. The public BSS-cache approach had already failed with 32 to 52 ms held-out disagreement.
2. **Design** ([design](../overview/2026-10-07-tsf-host-bound-design.md)): window-bound proof, attribution, freshness and shared-clock conditions, SoC domain test, predeclared pass/fail criteria. Revised after review of a separate gap register (foreign-report classification instead of stopping on any unsolicited report).
3. **Saved-evidence checks** (section 3), which changed four design details before any code depended on them.
4. **Implementation plan** ([plan](../overview/2026-10-07-tsf-host-bound-plan.md)): eleven tasks with code and tests.
5. **Implementation, test-first**, one commit per task (section 5).
6. **Preview on saved samples** ([preview](../clock-models/tsf-host-bound-preview.md)).
7. **Live campaign:** a 5-minute idle smoke run, then hour-long idle and load runs, with each stop investigated before any rerun (sections 6 to 8).
8. **Evaluation and results** ([results](tsf-host-bound-results.md)).

## 3. Checks on saved evidence before any new collection

All checks below used the six saved mixed runs of campaign `ecfaed68f20e` (2026-10-02), read-only.

| Check | How | Result | Effect on the design |
|---|---|---|---|
| Window widths | `report_qpc - host_before_qpc` for each saved action-4 sample | 214 to 740 us for all 18 samples; IOCTL return about 50 us | A single sample is already below 1 ms |
| SoC fixed-rate test | Largest `L - 10 * SoC` versus smallest `U - 10 * SoC` per run | No common offset; gap 365 to 688 us within about 24 s | SoC shortcut unlikely; window method is primary |
| Report vdev | Report records in three saved scan captures versus campaign runs | Scan-triggered reports also carry vdev 0 | Attribution uses the driver's `command` record instead |
| Command record | Record sequence per request in campaign and scan captures | Every request logs `command` (action 4) before `report`, `soc_timer`, `delay`; the six scan-triggered groups had no `command` | Structural attribution rule |
| Unbounded polygon | Single-window feasible set with only `r > 0` | Unbounded | Added a 200 ppm rate prior |
| Preview bound | New analyzer on the six runs | Worst case 143 to 296 us per run | Method viable before new collection |
| Action-3 freshness | Same freshness band on 48 action-3 samples | 0 rejected | Recorded; campaign still uses action 4 only |
| Router TSF phase | Cached beacon TSF modulo 102.4 ms | All 0 to 5 ms after a beacon boundary | Confirms cached values are genuine beacons |

## 4. Measurement method

**Model.** Within one epoch, `TSF = r * Q + c`, with `Q` in QPC ticks and `r` in TSF microseconds per tick.

**Constraint per sample.** With reported TSF `T`, lower bound `L` (QPC immediately before the request) and upper bound `U` (driver's ETW timestamp for the report), and widening by one TSF microsecond and one QPC tick for integer counters:

`T - r * (U + 1) <= c <= T + 1 - r * L`

**Rate prior.** `r` within 200 ppm of nominal (10^6 / QPC frequency).

**Feasible set and bound.** The constraints define a convex polygon in `(r, c)`, found exactly by enumerating line intersections with Python `fractions.Fraction`. The proven half-width at time `Q` is half the spread of `r * Q + c` over the polygon's vertices. Because the half-width is convex in `Q`, its maximum over a span is at the span's first or last instant, so the reported per-span maximum is exact.

**Spans.** 60-second spans stepped by 10 seconds, at least 3 samples each. A span with no feasible model is counted as infeasible and never dropped. Coverage is the union of feasible spans over the run.

**Screening** ([`sample_screen.py`](../../research/clock_models/sample_screen.py)):

- Records are grouped as `command` events and `report` + `soc_timer` + `delay` groups. A malformed group stops analysis.
- Each request has a 2,000 us acceptance window after `L` and a listening interval up to the next request (at most 5 s).
- Exactly one action-4 `command` and one report group inside the acceptance window gives a candidate. Two report groups reject the sample. None gives an own loss, or a late report if one arrives later in the listening interval.
- Report groups outside every acceptance window are foreign (counted, not fatal).
- vdev mismatch and `tsf - soc` delay arithmetic mismatch reject the sample.
- **Freshness:** consecutive accepted samples must satisfy `0.9999 * (L_j - U_i) - 1 <= T_j - T_i <= 1.0001 * (U_j - L_i) + 1` (microseconds). This uses no fitted value.
- **Misattribution estimate:** own losses x foreign-report rate x 2,000 us acceptance window.

**SoC domain test** ([`soc_domain_test.py`](../../research/clock_models/soc_domain_test.py)): one offset `k` with `10 * SoC + k` inside every window over the whole run, and a feasible SoC-to-QPC rate interval containing 10.

**Beacon check** ([`beacon_consistency.py`](../../research/clock_models/beacon_consistency.py)): each cached router beacon timestamp from `WlanGetNetworkBssList` must not exceed the predicted station TSF upper bound at the cache call's **return** by more than 1,000 us.

**Pass criteria (fixed before collection, both idle and load):** run completed; maximum proven half-width below 1,000 us; feasible coverage at least 90%; rejected samples at most 1%; estimated misattributed samples below 0.05; at least one beacon check and zero violations. A maximum of 100 us or less is a stretch result only.

## 5. Software built and how it was verified

| Module | Responsibility | Unit tests | Verification on real data or hardware |
|---|---|---:|---|
| [`bracket_bound.py`](../../research/clock_models/bracket_bound.py) | Exact polygon, half-width, sliding spans, coverage | 7 | Preview on saved samples; truth-containment test with a 40 ppm synthetic clock; exact single-window half-width |
| [`sample_screen.py`](../../research/clock_models/sample_screen.py) | Grouping, attribution, freshness, loss and foreign accounting | 10 | Saved campaign traces: 3 of 3 action-4 samples accepted, 8 action-3 groups classified as other activity |
| [`soc_domain_test.py`](../../research/clock_models/soc_domain_test.py) | SoC-to-QPC domain test | 3 | Saved runs and every live run: not compatible |
| [`beacon_consistency.py`](../../research/clock_models/beacon_consistency.py) | Coarse beacon check | 3 | Smoke run investigation (section 8.1) |
| [`analyze_bound_run.py`](../../research/clock_models/analyze_bound_run.py) | CLI: legacy preview, run analysis, evaluation | 5 | First real bundle exposed the decimal-string frequency field, fixed with a regression test |
| [`bss_reader.py`](../../research/acquisition/bss_reader.py) | Read-only public BSS cache reader | 4 | Live, unelevated: unique connected-BSSID match; structure layout 360/604 bytes asserted |
| [`run_bound_campaign.py`](../../research/acquisition/run_bound_campaign.py) | Long-run controller and load workload | 7 | Preview mode on the adapter; 20-second workload dry run (354 MB at 140 Mbit/s) |

Further checks:

- **Native helpers:** `live_observer.exe` and `decode_tsf_etl.exe` were rebuilt with MSVC ARM64 at `/W4 /WX`. The rebuilt decoder reproduced a saved trace's historical decoding byte for byte.
- **Repository suite:** 383 tests pass (50 skipped for absent private fixtures), including documentation link, synopsis and knowledge-index checks.
- **Test-first practice:** each module's tests were run and seen to fail on the missing module before the implementation was added. Each defect fix in section 8 started with a failing regression test where the defect was testable offline.

## 6. Live procedure

**Elevation.** Every live run was started with `Start-Process -Verb RunAs`, so Windows showed a UAC prompt that the user approved at the laptop. Bypassing UAC, for example by running as SYSTEM, was declined.

**Per run:**

1. Refuse to start if a quarantine marker exists.
2. Validate the adapter: Up on driver 1.0.4374.1300 with the pinned SHA-256, service running.
3. Start an owned ETW session for WlanLogger `{bb6f5b93-635c-47be-816f-e895e77064a8}`, keywords `0x2000000000000010`, level `0xff`, QPC clock, one sequential file, file plus real-time mode, 1-second flush.
4. Start the native live observer and wait for readiness and association.
5. For load runs, start the workload process.
6. Loop until the duration ends:
   - every 10 requests, re-check the adapter identity;
   - check the trace size against the cap;
   - every 10 seconds, read the cached router beacon;
   - send one action-4 request through the existing two-phase admission protocol;
   - wait up to 5 seconds for a report after the request's QPC;
   - check the own-loss budget (more than 1% after 100 requests stops the run);
   - sleep to a nominal 2-second spacing.
7. Stop the workload, the trace and the observer; re-check identity; decode the ETL offline; require live and offline timing records to be identical and the trace to report no lost events or buffers.
8. Write `run-result.json`. On any failure, write the quarantine marker.

**Stop conditions:** adapter or driver change; association change; observer exit; trace loss; trace cap; request failure; probe deadline; own-loss budget; workload exit or stall; live/offline mismatch.

**Marker handling.** After each stop the cause was investigated and reported. With the user's approval, the marker was moved into the stopped run's folder as `quarantine-marker-reviewed.json` (kept, not deleted).

**Command used (from an elevated prompt in the repository root):**

```powershell
$a = Get-NetAdapter | Where-Object { $_.InterfaceDescription -match 'FastConnect' -and $_.Status -eq 'Up' }
python research\acquisition\run_bound_campaign.py --if-index $a.ifIndex --condition load --duration-s 3600 --execute
```

## 7. Measurements from every attempt

All values from the analyzer. Stopped runs are diagnostics only and do not count towards the verdict.

| Run | Condition | Minutes | Outcome | Accepted / requests | Rejected | Foreign | Proven median / p95 / max (us) | Coverage | Beacon checks / violations | Trace MiB (MiB/min) | Download |
|---|---|---:|---|---|---|---:|---|---:|---|---|---|
| `eb49c4217b0a` | idle smoke | 5 | Completed, not counted | 98 / 98 | 0 | 0 | 145.3 / 167.9 / 169.2 | 100% | 25 / 0 | 60 (12.0) | not applicable |
| `00e0aa837bfa` | idle | 24.7 | Stopped: 250 MiB cap | 522 / 522 | 0 | 4 | 136.8 / 156.6 / 191.9 | 100% | 129 / 0 | 250 (10.1) | not applicable |
| **`ac08a44962b0`** | **idle** | **60** | **Completed, counted** | **1,276 / 1,277** | **1 late** | **6** | **134.8 / 160.1 / 352.2** | **100%** | **318 / 0** | **621 (10.3)** | not applicable |
| `90590c08b728` | load | 43.6 | Stopped: 425 trace events lost | 911 / 914 | 3 late | 6 | 135.0 / 154.3 / 175.1 | 100% | 229 / 0 | 465 (10.7) | 0 bytes (HTTP 403) |
| `948352ab3bd5` | load | 9.1 | Stopped: 1,000 MiB cap | 176 / 176 | 0 | 0 | 141.8 / 172.1 / 215.2 | 100% | 47 / 0 | 1,007 (110.4) | 3.8 GB |
| `a62689850d11` | load | 38.8 | Stopped: 1,000 MiB cap | 779 / 780 | 1 late | 4 | 138.9 / 160.1 / 198.0 | 100% | 199 / 0 | 1,000 (25.8) | 9.2 GB, 31.6 Mbit/s |
| `1a8a567bce2c` | load | 5.7 | Stopped: BSS cache gap | 105 / 105 | 0 | 4 | 147.5 / 280.8 / 296.5 | 100% | 28 / 0 | 135 (23.6) | 1.9 GB |
| **`04ddf1083b85`** | **load** | **60.1** | **Completed, counted** | **1,210 / 1,212** | **2 late** | **4** | **139.6 / 165.8 / 190.8** | **100%** | **310 / 0** | **1,315 (21.9)** | **15.8 GB, 35.1 Mbit/s** |

Across all eight attempts, 5,077 of 5,084 requests produced an accepted sample, no span was infeasible, no beacon check failed, and no worst-case proven error exceeded 353 us. Only the two counted runs carry evidential weight. Per-run analyzer outputs are in [`tsf-host-bound-2026-10-07/`](tsf-host-bound-2026-10-07/).

## 8. Investigations and fixes

Each fix was made only after the cause was established. None changed a pass threshold or the bound method.

### 8.1 Beacon check false violations (smoke run)

- **Symptom:** 2 of 25 beacon checks showed the router timestamp 2.9 to 3.1 ms ahead of the predicted station TSF.
- **Hypotheses tested:**
  - Action-4 TSF latched at beacon boundaries: rejected. TSF phases spread evenly across the 102.4 ms cycle (bins 12, 13, 7, 9, 9, 12, 8, 7, 9, 12), and the TSF fits a line against QPC within -120 to +159 us.
  - Multi-link connection with per-link TSF: rejected. `netsh wlan show interfaces` showed a single 802.11ac link on 5 GHz channel 149.
  - Cache refresh during the roughly 10 ms `WlanGetNetworkBssList` call: confirmed. Measured against the call's return, both readings were 6.1 and 7.4 ms inside the bound, and all 25 checks passed.
- **Fix (`d365782`):** compare against the call's return. Regression test: a beacon stamped 3 ms into a 10 ms call is not a violation.

### 8.2 Trace size cap (first idle attempt)

- **Symptom:** run stopped at the 250 MiB cap after about 25 minutes. Cleanup was clean.
- **Cause:** the trace grows about 10 to 12 MiB per minute at level `0xff`; the earlier campaign only ran 120-second captures.
- **Fix (`e0e2a49`):** cap raised to 1,000 MiB.

### 8.3 Trace event loss and a failed download (first load attempt)

- **Symptom:** run stopped at 43.6 minutes with `live_trace_loss`.
- **Localisation:** the ETW `events_lost` counter jumped from 0 to 425 between two health polls 263 ms apart, after about 9,800 clean polls. The last request had completed normally 1.6 seconds earlier, and every request/report pair in the preceding 10 seconds was intact. ETW counts lost events but does not identify them.
- **Where the buffers are:** ETW session buffers in kernel nonpaged pool, one set per CPU, flushed by the ETW logger to `tsf.etl` and to the real-time observer. The session used Windows default sizing.
- **Second finding:** the workload had downloaded 0 bytes with 2,205 errors. The endpoint returned HTTP 403 to these clients with and without a User-Agent, so that load was CPU-only.
- **Observer cleanup flag:** the native observer had stopped itself on the loss (`failed: true`, close status 7007, not forced). This was a consequence, not a separate fault.
- **Fix (`5b2be2d`):** public OVH and Hetzner 100 MB test files with a User-Agent (OVH measured 78 Mbit/s, Hetzner 52), plus a 60-second stall rule that fails the run. Explicit trace buffers were added; their first sizing is covered in 8.4.

### 8.4 Buffer size inflates the trace file (second load attempt)

- **Symptom:** with 256 KB buffers the trace grew about 103 to 110 MiB per minute and hit the cap at about 9 minutes, with 0 buffers lost (confirmed live with `logman query <session> -ets`).
- **Measurement:** the first 32-bit field of each ETL file's first buffer header is the buffer size. All earlier traces used 8,192 bytes, the 256 KB run used 262,144, and every file size was an exact whole number of buffers. Each per-CPU flush writes whole buffers, so file growth scales with buffer size.
- **Fix (`c56e1ba`):** keep the 8 KB size and raise the count to 256 to 2,048 buffers (at most 16 MiB).

### 8.5 Trace cap under real network load (third load attempt)

- **Symptom:** with the download working (9.2 GB, 31.6 Mbit/s) and no lost events, the trace grew about 26 MiB per minute and hit the 1,000 MiB cap at 39 minutes.
- **Fix (`83438b7`):** cap raised to 3,000 MiB, about twice the measured hourly need.

### 8.6 BSS cache gap (fourth load attempt)

- **Symptom:** run stopped at about 6 minutes because one cache read held zero or several entries for the connected BSSID.
- **Evidence it was not an association change:** the same BSSID hash in every read, no observer association change, adapter identity unchanged afterwards.
- **Fix (`1021390`):** such a read is recorded as a skip in `run-result.json`; an association change during a read still stops the run. Regression test added. The counted load run recorded one skip.

### 8.7 Documentation error caught before publication

- The results draft stated the idle misattribution estimate as 0.00033. Recomputed from the exact fraction it is 3.3 x 10^-6; the draft had been written from a truncated printout. Corrected before commit; the verdict was unaffected.

## 9. Work not done and stated limitations

- **Phase 0 raw-field check.** The callers of the driver's generic hex-dump routines, their gating and the raw received report length were not pursued in this work. The report-type and clock-ID fields therefore remain unobserved, and the report is assumed to describe the associated link's TSF.
- **Station TSF to access point TSF** is assumed (802.11 station synchronization) and checked only coarsely.
- **No UTC or external-timescale claim.**
- **Conditions not covered:** other access points, channels or link types; roaming, reconnection, suspend/resume; other driver or firmware builds; loads beyond those declared.
- **Private evidence preservation.** The raw run folders (traces, receipts, beacon reads) are local under the git-ignored `artifacts/` directory. Copying them into the private evidence repository is a separate step.

## 10. Environment, records and reproduction

| Item | Value |
|---|---|
| OS | Windows 11, build 10.0.26200.9457, ARM64 |
| CPU | Snapdragon X Elite X1E80100 |
| Wi-Fi | Qualcomm FastConnect 7800, `qcwlanhmt8380.sys` 1.0.4374.1300 |
| Python | 3.14.3 (ARM64), `pefile` 2024.8.26 |
| Compiler | Visual Studio 2022 Build Tools, MSVC ARM64, `/W4 /WX` |
| Base revision | `d1055a1` (main after PR #3) |

**Rebuild the native helpers:**

```powershell
$vs = & "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" -latest -products * -property installationPath
cmd /c "`"$vs\VC\Auxiliary\Build\vcvarsall.bat`" arm64 && cl /nologo /W4 /WX /O2 research\acquisition\live_observer.c /Foartifacts\live_observer.obj /Feartifacts\live_observer.exe /link advapi32.lib wlanapi.lib iphlpapi.lib kernel32.lib && cl /nologo /W4 /WX research\tsf\decode_tsf_etl.c /Foartifacts\decode_tsf_etl.obj /Feartifacts\decode_tsf_etl.exe /link advapi32.lib kernel32.lib"
```

**Run the tests:** `python -m unittest discover -s tests`

**Re-evaluate the counted runs** (requires the private run folders under `artifacts/`):

```powershell
python research/clock_models/analyze_bound_run.py evaluate artifacts/BoundCampaign-ac08a44962b0/idle artifacts/BoundCampaign-04ddf1083b85/load
```

**Derived records in this repository** ([`tsf-host-bound-2026-10-07/`](tsf-host-bound-2026-10-07/)): the evaluation of both counted runs, the smoke analysis, a diagnostic analysis of each stopped run, and the preview on saved samples. They contain counts, bounds and QPC-relative values only: no BSSIDs, SSIDs, MAC addresses or raw TSF captures.

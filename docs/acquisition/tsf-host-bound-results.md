# TSF-to-host bound: live campaign results

The current Qualcomm FastConnect 7800 laptop passed every predeclared criterion: across one hour idle and one hour under CPU and network load, its Wi-Fi TSF clock was bounded to within 352 microseconds at worst, and typically about 135 to 140 microseconds, at any Windows QPC instant. This is a proven worst-case bound under stated conditions, not a fitted residual. It covers the laptop's own TSF. The step from the laptop's TSF to the access point's TSF rests on the 802.11 station-synchronization rule plus a coarse check, because the equipment available cannot measure that step independently.

## Contents

- [Verdict](#verdict)
- [Scope and conditions](#scope-and-conditions)
- [Results per counted run](#results-per-counted-run)
- [All attempts, including stopped runs](#all-attempts-including-stopped-runs)
- [Changes made after data collection began](#changes-made-after-data-collection-began)
- [What this establishes and what it does not](#what-this-establishes-and-what-it-does-not)
- [Reproduce the evaluation](#reproduce-the-evaluation)

**Terms:** the **proven half-width** is the largest TSF error possible at any instant of an analyzed span, given that each firmware capture happened inside its host window. A **window** runs from the QPC reading just before a private action-4 request to the driver's trace timestamp for the matching report. See the [design](../overview/2026-10-07-tsf-host-bound-design.md), the [implementation plan](../overview/2026-10-07-tsf-host-bound-plan.md) and the [glossary](../glossary.md).

## Verdict

| Criterion (fixed before collection) | Idle | Load |
|---|---|---|
| Run completed without a stop condition | Yes | Yes |
| Maximum proven error below 1,000 us | Yes: 352.2 us | Yes: 190.8 us |
| Feasible coverage at least 90% | Yes: 100% | Yes: 100% |
| Rejected samples at most 1% | Yes: 1 of 1,277 | Yes: 2 of 1,212 |
| Estimated misattributed samples below 0.05 | Yes: 3.3 x 10^-6 | Yes: 4.4 x 10^-6 |
| Beacon check: at least one check, zero violations | Yes: 318 checks, 0 violations | Yes: 310 checks, 0 violations |
| Stretch result: 100 us or less | No | No |

**Overall: passed.** The stretch target of 100 us was not met; it was reported, not required.

## Scope and conditions

- **Hardware and driver:** Qualcomm FastConnect 7800 (`PCI\VEN_17CB&DEV_1107`), ARM64 `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`. The driver identity was checked every ten requests and again after each run.
- **Link:** one 802.11ac association on 5 GHz channel 149 to a consumer router without shell access. No multi-link operation.
- **Host clock:** QPC at 10,000,000 ticks per second.
- **Method:** one private action-4 request in flight at a time, about every 3 seconds, with WlanLogger traced at level `0xff` on a QPC event clock. Records were classified offline by the [sample screen](../../research/clock_models/sample_screen.py) and bounded by the [window polygon](../../research/clock_models/bracket_bound.py) over 60-second spans stepped by 10 seconds.
- **Idle run:** 2026-10-07, 60 minutes from 21:55:39 UTC, controller commit `e0e2a49`.
- **Load run:** 2026-10-08, 60 minutes from 01:02:18 UTC, controller commit `1021390`. The load was the campaign's SHA-256 CPU workload (10 ms on, 10 ms off) plus a looped HTTPS download: 15.8 GB at an average of 35.1 Mbit/s, with one transient download error and no stall.

## Results per counted run

| Measure | Idle | Load |
|---|---:|---:|
| Requests | 1,277 | 1,212 |
| Accepted samples | 1,276 | 1,210 |
| Rejected samples (all `late_report`) | 1 | 2 |
| Foreign report groups (scans and other activity) | 6 | 4 |
| Own losses | 1 | 2 |
| Proven half-width, median (us) | 134.8 | 139.6 |
| Proven half-width, p95 (us) | 160.1 | 165.8 |
| **Proven half-width, maximum (us)** | **352.2** | **190.8** |
| Spans analyzed / infeasible | 360 / 0 | 360 / 0 |
| Window width, min / median / max (us) | 196.8 / 262.7 / 1,004.6 | 211.0 / 271.8 / 1,040.7 |
| Beacon checks / violations / skipped cache reads | 318 / 0 / not recorded | 310 / 0 / 1 |
| Trace events or buffers lost | 0 | 0 |
| SoC compatible with the QPC domain | No | No |

- Single windows occasionally exceeded 1,000 us. Combining each span's windows still kept every proven half-width below 353 us.
- No span was infeasible. No TSF step or rate change too large for the 200 ppm prior occurred within either hour.
- The SoC counter again failed the fixed-rate test, so the bound comes from the window method alone.

## All attempts, including stopped runs

A stopped run is a failed run and contributes nothing to the verdict. All attempts on 2026-10-07 and 2026-10-08:

| Run | Condition | Outcome | Cause |
|---|---|---|---|
| `eb49c4217b0a` | idle, 5-minute smoke | Completed; not counted | Smoke run by design. 98 of 98 samples accepted, maximum 169.2 us |
| `00e0aa837bfa` | idle | Stopped at about 25 minutes | 250 MiB trace cap; the trace grows about 12 MiB per minute |
| `ac08a44962b0` | idle | **Completed; counted** | |
| `90590c08b728` | load | Stopped at 43.6 minutes | 425 trace events lost in one burst; download returned HTTP 403, so load was CPU-only |
| `948352ab3bd5` | load | Stopped at about 10 minutes | 1,000 MiB cap; 256 KB buffers inflated the file to about 103 MiB per minute |
| `a62689850d11` | load | Stopped at 39 minutes | 1,000 MiB cap under real network load (about 26 MiB per minute); no events lost |
| `1a8a567bce2c` | load | Stopped at about 6 minutes | One public cache read held zero or several entries for the connected BSSID; association unchanged |
| `04ddf1083b85` | load | **Completed; counted** | |

Every stopped run shut down with its adapter identity unchanged. Diagnostic analyses of the stopped runs gave maxima between 175 and 198 us; they are context, not evidence for the verdict.

## Changes made after data collection began

None changed a pass threshold or the bound method. Each fixed a defect exposed by a run:

| Commit | Change | Trigger |
|---|---|---|
| `d365782` | Beacon check compares against the cache call's return, not its start | Smoke run: two cache refreshes happened during the roughly 10 ms call |
| `e0e2a49`, `83438b7` | Trace cap raised from 250 MiB to 1,000 MiB, then to 3,000 MiB | Trace volume, 12 MiB per minute idle and 26 MiB per minute loaded |
| `5b2be2d`, `c56e1ba` | Download from public OVH/Hetzner files with stall detection; 8 KB trace buffers, 256 to 2,048 of them | Lost events under load; HTTP 403; file growth scales with buffer size |
| `1021390` | A cache read with zero or several entries for the connected BSSID is skipped, not a stop | Cache gap with the association unchanged |

The counted idle run used `e0e2a49`, before the buffer and cache-gap changes; it needed neither. The counted load run used `1021390`.

## What this establishes and what it does not

**Established for these conditions:** the laptop can state its station TSF at any QPC instant with a worst-case error of at most 352 us over an hour idle and 191 us over an hour under the declared load. That holds provided each action-4 TSF is captured between the request leaving the host and the driver logging its report. Attribution, freshness and trace completeness were screened for every sample.

**Not established:**

- **Station TSF to access point TSF.** Assumed from 802.11 station synchronization. The beacon check only rules out disagreement larger than about a millisecond beyond unknown cache age. An independent access point clock read or a second reference is required to measure this step.
- **Accuracy against UTC** or any external timescale.
- **Other conditions:** a different access point, channel or link type, roaming, reconnection, suspend and resume, other drivers or firmware, or sustained loads beyond those declared.
- **Firmware field semantics:** the report-type and clock-ID words are not logged by the driver, so the report is assumed to describe the associated link's TSF.
- **A clock provider:** no `userspace-clock` provider is enabled by this result. It supports a separate provider proposal.

## Reproduce the evaluation

From the repository root, with both run folders present under `artifacts/` (private evidence, not in Git):

```powershell
python research/clock_models/analyze_bound_run.py evaluate artifacts/BoundCampaign-ac08a44962b0/idle artifacts/BoundCampaign-04ddf1083b85/load
```

The command reads the decoded trace, probe receipts and beacon reads of each run and prints the screen, the analysis and the verdict as JSON. It writes nothing.

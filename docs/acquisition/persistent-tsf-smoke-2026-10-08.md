# Persistent TSF sampler: first live smoke result

> Historical report: the original source pins and JSON outputs are preserved. See the [2026-10-08 review reconciliation](../overview/pr-reconciliation-2026-10-08.md) for corrected threshold, settlement, and diagnostic results on the same retained captures.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__acquisition__persistent-tsf-smoke-2026-10-08.md).
<!-- /research-history -->

The persistent sampler completed one 300-second idle run on the qualified Qualcomm FastConnect 7800 Windows ARM64 profile. All 139 requests completed successfully in one recorded session; offline screening accepted 138 timing samples. Normal shutdown was clean. This supports live persistent acquisition on this exact build and a useful conditional TSF-to-QPC relationship. It does not complete phase 2 or establish calibrated physical, AP, UTC or multi-device accuracy.

## What ran

- Date: 2026-10-08. Launcher interval: 16:47:59.0076327 to 16:53:10.4827365 UTC, including startup and cleanup.
- Base revision: `c620f47c94e4691347c6a905860fe435be1aa575`, plus the sampler patch identified by the source hashes in the [public measurement summary](persistent-tsf-smoke-2026-10-08.json). The tree was uncommitted during collection; the base SHA alone does not identify the implementation that ran.
- Driver: ARM64 `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Profile: `--sampler persistent`, idle, 300 seconds, one-second requested spacing, existing report wait retained.
- The operator approved elevation on an explicit retry after the first UAC launch was canceled. There was one actual acquisition, with no automatic acquisition retry.
- Both native helpers were freshly built as ARM64 with MSVC `/W4 /WX`. All 109 source/build pins matched before and after the run.

Raw ETL, adapter identity, worker journal and observer records remain private. This document and its JSON publish aggregate results, authored-source hashes and input digests, not raw captures or endpoint identifiers. Possession of those hashes alone does not allow an independent reader to reproduce private data analysis.

## Acquisition and lifecycle

| Check | Result |
|---|---:|
| Configured collection duration | 300 s |
| Actual first-to-last request span | 297.999421 s |
| Requests / successful terminal completions | 139 / 139 |
| Initially returned `ERROR_IO_PENDING` | 139 |
| Cancellations / deadline failures | 0 / 0 |
| Final sampler state / actual handle closure | `CLOSED` / true |
| Outstanding operations at shutdown | 0 |
| Observer clean stop / evidence drained | true / true |
| Forced termination | false |
| ETW events / buffers lost | 0 / 0 |
| Final adapter identity | matched startup |
| New bound-campaign quarantine / unfinished marker | absent / cleared after successful persisted completion |

The real pending-to-success overlapped path was exercised. Live cancellation, stuck I/O, controller disappearance, device reset, sleep and roaming were not exercised. The historical strict-campaign quarantine remains unchanged; this bound-campaign profile separately retains foreign reports for offline classification. Kernel completion and clean process shutdown are not proof of firmware report drain.

## Actual spacing and delivery

| Measure | Median | p95 | Maximum |
|---|---:|---:|---:|
| Request gap | 2.005197 s | 3.004809 s | 4.009085 s |
| Accepted-sample gap | 2.005223 s | 3.004809 s | 4.009085 s |
| Required report-group delivery after original report timestamp | 1.486137 s | 1.999159 s | 2.167023 s |
| Retained controller report wait | 1.475685 s | 1.992648 s | 2.165165 s |
| Submission-to-observed-terminal QPC bracket | 4.3957 ms | 6.1479 ms | 7.1703 ms |
| Controller receipt after terminal observation | 5.5183 ms | 6.3514 ms | 7.6165 ms |

The mean request gap was 2.159416 seconds. The controller recorded 161 skipped slots and nine periodic identity checks. Identity, report-wait and processing delays remain in the measured gaps. The terminal-observation bracket includes completion polling, coordination and evidence handling; it is not the device's execution time.

One-second requested spacing did not produce one-second achieved cadence. The older approximately 2.99-second cycle, 1.96-second report wait and 1.04-second other work remain rounded user-reported context. This short run is not a controlled performance comparison against the earlier hour-long acquisitions.

## Screening and replay

The unchanged offline screen accepted 138 of 139 requests. Request 1 had a late report outside the fixed 2,000-us acceptance window. There were two foreign report groups and no foreign commands. Live report-wait losses were zero; offline own-loss accounting includes the late report and was one. These counters measure different conditions.

Accepted capture-window width was 254.5 us at the median and 1,028.2 us at the maximum. The coarse beacon check evaluated 27 observations, left one unchecked and found zero violations. It does not measure station-to-AP offset independently.

Arrival-aware replay uses `A = max(last required record receipt, terminal request observation, report QPC + 1)`. Its declared interval runs from the first request through five seconds after the last request: **302.999421 seconds**. That is distinct from configured duration and launcher wall time. Full-recording offline screening remains a prerequisite; the replay is not an online-admission demonstration.

| Replay state | Duration |
|---|---:|
| Acquiring | 3.317855 s |
| Tracking, conditional half-width below 1 ms | 281.438106 s |
| Stale | 18.243460 s |
| Invalid | 0 s |

Tracking coverage was **92.884041%** over that interval. The largest conditional half-width observed immediately before a subsequent sample was **1,348.809 us**; this metric excludes any subsequent tail without another sample and must not be presented as a whole-run or universal maximum. There were no incompatible accepted samples. Later queueing, IPC and ingestion delays are not newly added to the replay's availability boundary.

Settlement replay generated **297 one-second event-grid points**, and all 297 settled:

| Settlement measure | Median | Maximum |
|---|---:|---:|
| Wait until later sample was available | 2.341 s | 4.989 s |
| Conditional rate-only half-width at event-grid points | 280.429 us | 614.883 us |
| Optional affine half-width at event-grid points | 123.744 us | 256.073 us |

The exact retrospective rate-only maximum over the covered consecutive-pair intervals, including instants between grid points, was **648.30025 us** (reported rounded to 648.300 us). This applies to the bracketed recording, not arbitrary startup, post-recording or future times. The optional affine result adds a constant-rate assumption over the surrounding 60 seconds and is not interchangeable with the rate-only bound.

These are interval half-widths: for example, a 615-us half-width means approximately plus or minus 615 us around the midpoint under the assumptions. They are not measured absolute errors, statistical confidence intervals, or full interval widths. All results retain `conditional-research` and `physical_bound_proven: false`. See the [mathematics reference](../clock-models/tsf-mathematics.md).

## Verification and reproduction

The phase 1 Windows ARM64/Python 3.14.3 suite completed 469 tests: 432 passed and 37 skipped for optional fixtures/compiler environments. The five-minute live run is separate evidence. The normal completion path passed; real cancellation and firmware-drain qualification remain open.

Given authorized access to the original private run directory, the analyses are read-only:

```powershell
python research/clock_models/analyze_bound_run.py run <PRIVATE_RUN_DIRECTORY>
python research/clock_models/replay_causal_provider.py <PRIVATE_RUN_DIRECTORY> --mode all
```

Both CLI commands returned 0 and agreed exactly with the programmatic analyses. The controller verified equality of live and offline timing records, trace loss counters and final identity. The analytical outputs are identified in the JSON summary. Hosted CI, when present for a publication commit, validates software checks and does not rerun this live capture. Public-only readers can reproduce the offline unit tests but need the private input bundle to reproduce these measured results.

## What this permits next

The result supports developing a two-phase event timestamp API that preserves raw QPC, returns a provisional interval and derives a settled interval later. It does not justify an always-available sub-millisecond clock or removing the report wait. The next gates are longer idle/load qualification, failure-path evidence, causal online admission, and independent source/accuracy validation. Their dependencies and acceptance evidence are in the [phase 2 research and implementation roadmap](../overview/persistent-tsf-next-steps.md).

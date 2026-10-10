# Sub-millisecond live qualification, 2026-10-10

Five live runs of the persistent sampler on the qualified Qualcomm FastConnect 7800 Windows ARM64 profile cut the settled TSF-to-QPC median half-width from about 308 to 325 microseconds (2026-10-07 hour runs, v2 policy) to about 133 to 139 microseconds under the same policy, and raised declared tracking coverage from 78.6% and 72.3% to 99.98%. The first two runs each failed the acceptance gate for a concrete operational reason; those defects were fixed, and the last three runs, including one hour idle and one hour under load, passed all nine criteria. The results remain conditional research intervals under declared assumptions. They are not AP or UTC calibration and do not prove a physical bound.

## What ran

- Date: 2026-10-10. Five bound-campaign runs on one adapter, driver and host: three 300-second idle smokes, one 3,600-second idle hour and one 3,600-second hour under load. Requested spacing was one second throughout.
- Driver: ARM64 `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Native helpers: `live_observer.exe` SHA-256 `906122f00112622803dc684646a63c630d97dd794a0384948a236fbcef48eaa9`; `decode_tsf_etl.exe` SHA-256 `ecf4f59990b2fc8b1d8aa578fd42081ef865c62bec15e766bb0531c03f50daee`.
- Source revision per run (every replay reports an unmodified research tree): run 1 `5a4e66ea7633f2049243ba98121e49c9bb74afb8`; run 2 `37d450e018c491b6ec4b3b7ba8e1d717c3934f3f`; runs 3 and 4 `0976861026c2494a73b4b2e2a309083a6f8d7961`; run 5 `91a9f07ad44e7c53706d526debcdcd919a0c295c`.
- Three UAC elevation prompts (before runs 1, 2 and 4) were cancelled before an approved retry. Cancelled launches started nothing.
- Run 5 loaded the link with a looped HTTPS download plus a 10 ms on, 10 ms off hash workload. It downloaded 31,185,829,888 bytes at a mean of 69.2 Mbit/s with 9,406,492 hash operations, and recorded one download error without a stall.

Raw captures, adapter identity, ETL traces, launcher scripts and per-request records stay private. This page and its [JSON summary](sub-millisecond-qualification-2026-10-10.json) publish aggregates only.

## Results

| | Run 1 | Run 2 | Run 3 | Run 4 (hour idle) | Run 5 (hour load) |
|---|---:|---:|---:|---:|---:|
| Requests / accepted | 146 / 146 | 289 / 289 | 297 / 297 | 3,589 / 3,588 | 3,585 / 3,582 |
| Median accepted gap (s) | 1.999 | 0.997 | 1.000 | 0.998 | 0.999 |
| Report delivery median / p99 (ms) | 116.4 / 123.6 | 22.7 / 34.5 | 23.3 / 37.8 | 23.0 / 37.3 | 22.9 / 36.4 |
| Coverage, review interval / declared interval | 1.0 / 0.997076 | 0.993879 / 0.991437 | 1.0 / 0.996126 | 1.0 / 0.999764 | 1.0 / 0.999767 |
| Coverage, request interval (acceptance version 2 gate) | 0.999601 | 0.993799 | 0.999926 | 0.999993 | 0.999991 |
| Settled v3 median half-width (us) | 301.663 | 154.49 | 153.283 | 158.371 | 164.172 |
| Settled v2 median half-width (us) | 276.663 | 129.49 | 128.283 | 133.371 | 139.172 |
| Learned-rate median (us), holdout violations / checked | 161.842, 0 / 141 | 154.594, 0 / 284 | 153.579, 0 / 292 | 154.011, 0 / 3,583 | 159.88, 0 / 3,577 |
| Acceptance criteria passed | 6 / 9 | 8 / 9 | 9 / 9 | 9 / 9 | 9 / 9 |
| ETL growth (MiB per minute) | 10.48 | 10.24 | 11.36 | 9.99 | 8.03 |

Delivery is the time from the report timestamp to the delay-record receipt, computed over accepted samples with the acceptance checker's nearest-rank p99. Single late deliveries in the hour runs reached 137.4 ms (run 4) and 149.1 ms (run 5), well above the p99. The coverage "review interval" runs from the first to the last accepted sample's availability and is what the original (version 1) evaluation gated on; acceptance version 2 instead gates on the "request interval", coverage from the first to the last request submission, with the values in the table (outcomes unchanged); the "declared interval" runs from the first request through five seconds after the last. The v3 rows use the settlement-v3 policy with a declared jump allowance J = 25 us. The v2 rows apply the earlier policy to the same data and are the like-for-like comparison with the 2026-10-07 hour runs.

All ETW flush calls returned status 0 with no lost events or buffers: 385, 636, 651, 7,934 and 7,622 flushes across runs 1 to 5. Background identity checks (runs 3 to 5) numbered 9, 119 and 119, with no failures and maximum durations of 1.13 s, 1.36 s and 4.13 s. Trace growth stayed far below the 3,000 MiB cap: run 4 wrote 599 MiB and run 5 wrote 482 MiB, so the doubling the plan feared did not occur.

Acceptance limits (see `research/clock_models/sub_ms_acceptance.py`): guaranteed live coverage at least 0.995, no incompatible samples, every settled point under 1 ms, settled median at most 250 us, learned-rate median at most 180 us with no holdout violation, delivery p99 at most 0.1 s with none missing, and median gap within 1.1 times the requested spacing. Per-run check values are in the JSON. Run 1 failed settled median (301.663 us), delivery p99 (0.1236 s) and gap ratio (1.999). Run 2 failed only guaranteed coverage (0.993879). Acceptance version 2 (after this report's runs were first evaluated) additionally requires a completed clean lifecycle, whole-recording continuity eligibility, no continuity invalidations, no invalid replay time and no accepted sample available after the replay end, and measures live coverage from the first to the last request; all five runs were re-evaluated under it with the same outcomes.

## What changed between runs

Three operational defects, found one at a time by the runs, account for the failures.

1. **Skipped slots and a late report (run 1, commit 5a4e66e).** ETW flushing worked (all status 0) and delivery fell from about 1.5 s to 116 ms, but every request skipped a slot, giving a median gap of 2.0 s and 154 skipped slots over 146 requests. `RequestSlots.reserve` required a full spacing after the previous actual submission, and submissions always land a few milliseconds after their slot. The 161 skipped slots in the 2026-10-08 smoke had the same cause; the plan had attributed those 2-second gaps to the report wait. The report also arrived only after the second or third flush. Commit `37d450e` added a 10 percent gap tolerance (`MIN_GAP_FRACTION = 0.9`) and a flush retry every 10 ms, up to five times.
2. **Synchronous identity check (run 2).** Cadence was 1.0 s and delivery 22 ms, but one synchronous 30-second-cadence identity check took 4.67 s, producing a 6.0 s gap and coverage of 0.993879, below the 0.995 gate. Commit `0976861` moved the same checks, at the same cadence, into a background `IdentityMonitor`. Submissions are gated on a successful check started within the last 60 s; a failure, or a check running longer than 60 s, stops the run. One synchronous check still runs immediately before the loop.
3. **Follow-ups (commit 91a9f07, used for run 5).** End-of-run identity tail evidence is now persisted and the monitor was hardened.

In run 5, one of 119 identity checks took 4.13 s without affecting sampling, and screening rejected 3 late reports.

## Comparison with the 2026-10-07 hour runs

The baselines are the corrected hour runs in the [post-merge corrections](../overview/postmerge-corrections-2026-10-08.json), which use the v2 policies. Run 4 and run 5 are compared with the v2 replay rows.

| | 2026-10-07 hour idle | Run 4 (hour idle) | 2026-10-07 hour load | Run 5 (hour load) |
|---|---:|---:|---:|---:|
| Requests | 1,277 | 3,589 | 1,212 | 3,585 |
| Declared tracking coverage (v2 replay) | 78.632% | 99.980% | 72.350% | 99.980% |
| Stale intervals | 841 | 1 | 977 | 1 |
| Settled v2 median half-width (us) | 308.456 | 133.371 | 324.908 | 139.172 |

The 2026-10-07 runs spaced requests about two seconds apart with report waits of about 1.5 s. The new runs request one second apart and receive reports in about 23 ms. Load raised the settled median by about 6 us (164.172 against 158.371 us in v3) and did not change coverage in these hours.

## Evidence and privacy

The raw captures are held in the private repository `Protonmatter/wifi-hardware-time-evidence`: snapshot `snapshots/sub-millisecond-2026-10-10` (source ID `e3a4f24bfb249b904bb72606aac3e355dd82d5ccdbb833a03031cacb8f9c1e78`), release `sub-millisecond-2026-10-10`, and private PR #4. These are private and cannot be opened from this page. Raw records, ETL traces, adapter and interface identifiers, access point identifiers, console logs and launcher scripts are not published. The JSON holds counts, medians, percentiles, check values, revisions and hashes of the authored binaries. Public readers can reproduce the unit tests but not these measurements.

## Limits

- Intervals are conditional on the declared assumptions (bounded rate, causal capture, one continuous TSF, station TSF equal to AP TSF) and on offline screening. They are half-widths, not measured absolute errors or confidence intervals, and `physical_bound_proven` stays false.
- There is no AP or UTC calibration.
- The read point inside the roughly 250 us capture window is unknown. The constant-rate settled median of about 121 to 129 us is the floor for this method.
- J = 25 us is a declared allowance for TSF jumps, not a measured quantity.
- One adapter, one driver and one host were tested: two one-hour conditions and three five-minute smokes.
- Online admission is still offline screening of the complete recording, not a live admission demonstration. Cancellation, device reset, sleep and roaming were not exercised.

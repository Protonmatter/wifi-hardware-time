# Integrated TSF review reconciliation, 2026-10-08

This review preserves persistent sampler baseline `02459e780f9912b31c2ece951cf824d941972156` and reconciles research PRs #4, #5 and #6 against that complete tree. Their original heads are ancestors of the baseline. Corrections are new commits; original capture files, published analysis JSON, and the audited private request protocol remain unchanged. One integration PR is the merge candidate. The earlier PRs retain their historical component reviews.

The changes are software corrections and offline reanalysis. They do not qualify firmware sampling, AP/UTC accuracy, online admission, live cancellation/drain, or report-wait decoupling. The original live smoke remains evidence for its original pinned build.

## Review disposition

The table accounts for all 23 research review threads. “Already fixed” means the current integrated baseline contains the correction and its applicable tests; an outdated GitHub comment alone was not sufficient evidence.

| PR / comment | Disposition | Evidence or correction |
|---|---|---|
| #4 / 4214190602 | Already fixed | WLAN profile storage is an explicit 16-bit array; `test_bss_reader` verifies the ABI layout. |
| #4 / 4214190608 | Already fixed | `finalize` converts missing/failed/malformed decoder output into a failure reason; outcome persistence retains quarantine. |
| #4 / 4214190613, 4214190616 | Already fixed; duplicate report | Stopped-run maximum range is 175.1–296.5 us in the current report and covers the cited saved analyses. |
| #4 / 4214190622 | Already fixed | Adapter-scoped lock covers admission through cleanup/persistence; concurrent-controller regression. |
| #4 / 4214190624 | Already fixed | Non-QPC and missing trace-clock metadata reject before analysis. |
| #4 / 4214190630 | Already fixed | Recorded idle/load conditions and distinct run identities are required; duplicate/swapped-run tests. |
| #4 / 4214437572 | Reproduced; corrected | Any infeasible span rejects the verdict even if other overlapping spans provide full coverage. |
| #4 / 4214437582 | Reproduced; corrected | Every covering feasible span constrains a beacon; the tightest upper bound makes classification independent of span order. |
| #4 / 4214437591 | Already fixed | Durable adapter-scoped in-progress record survives process death; repeated admission remains blocked until reconciliation. |
| #4 / 4214553787 | Reproduced; corrected | At least `report_count - 1` collided report groups are foreign and contribute to the misattribution estimate. |
| #4 / 4214553795 | Reproduced; corrected | Workload stop-file, wait, and termination failures cannot skip trace/observer/final-identity cleanup or result persistence. Secondary workload cleanup errors are retained. |
| #4 / 4214553802 | Reproduced; corrected | The live loss-budget check requires one action-4 command and matching report within the inclusive 2-ms window. Late or structurally foreign reports still end the existing wait but count as losses. This is a health check, not complete online sample admission. |
| #5 / 4214739801 | Reproduced; corrected | Rejected reports lacking evidence are explicit `rejected_uncheckable` records rather than disappearing from diagnostics. |
| #5 / 4214739811 | Reproduced; corrected | Adjacent stale intervals are coalesced before count/longest-interval statistics. Diagnostic events cannot split a continuous stale period. |
| #5 / 4214739818 | Reproduced; corrected | Returned uncertainty is exact half-width plus a conservative 0.5-us rounding allowance; state, expiry, and coverage use that same bound. Exact endpoints and nearest-integer estimate are preserved. |
| #5 / 4214739830 | Reproduced; corrected | Causal replay supports zero/one accepted samples over its declared interval and omits an undefined review interval. Retrospective/settlement modes retain explicit sample requirements. |
| #6 / 4215523359 | Reproduced; corrected | Affine estimates use only evidence available by the returned settlement time, including when queried later. |
| #6 / 4215523369 | Reproduced; corrected | Affine count/share explicitly disclose the subset used for affine quantiles. |
| #6 / 4215523379 | Reproduced; corrected | Brackets are selected from available samples; delayed nearest neighbours do not hide an already available bracket. Replay uses earliest complete-bracket availability. Historical answers are prefix-invariant. |
| #6 / 4215523388 | Reproduced; corrected | True-before requires widened capture end `upper + 1 <= event`; true-after requires `lower > event`. An overlapping capture supplies neither side. |
| #6 / 4215523399 | Reproduced; corrected | Settle output includes the existing one-QPC-tick/one-TSF-microsecond quantization policy. |
| #6 / 4215523406 | Reproduced; corrected | Nonpositive, Boolean and noninteger replay steps reject before loop entry. |

Review comments are available at `https://github.com/Protonmatter/wifi-hardware-time/pull/<PR>#discussion_r<comment>` using the table IDs.

## Regression controls

Each reproduced defect has a failing regression before its correction. Existing resource ownership and persistent-worker tests remain in the full suite. Added acquisition tests inject processes and a clock; they do not send adapter requests. The workflow now runs the full Python suite on Windows as well as Linux, retaining the existing native/PowerShell checks.

Retained-data comparison covers the counted idle/load hour and the persistent smoke. Inputs are hashed before and after replay, and both the preserved baseline and candidate use the same captures. Revised results are recorded separately; differences in rounding threshold, beacon upper bound, diagnostic counts, or settlement semantics must be explicit. A consecutive-pair retrospective maximum is not a general bound on first-available nonadjacent settlement when arrivals are out of order.

## Merge and rollback

Use a merge commit for the integration candidate so the original source pins remain ancestors of `main`. Verify the final candidate against the current base, passing exact-head CI, and the tested source tree before merging. Earlier PRs are historical review units, not independent merge candidates after this reconciliation. Retire them only after their commits and corrected implementation are verified in `main`.

Rollback is a reviewed revert of the integration merge, preserving source/evidence history. A revert does not reconcile a live device quarantine or establish firmware drain. No source merge or rollback enables a live provider or changes the machine clock.

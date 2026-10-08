# TSF-to-host bound: design for a sub-millisecond proof on the current adapter

This design tests whether the current Qualcomm laptop can state, at any Windows QPC instant, the value of its Wi-Fi TSF clock with a **proven** error below 1,000 microseconds. It reuses the private action-4 TSF request that earlier campaigns already exercised, collects far more samples, and turns each sample's host timing window into a hard constraint. The result is a worst-case bound derived from logic, not a fitted residual. It does not claim UTC accuracy or a measured agreement with a second device.

**Status:** design only, 2026-10-07. Nothing in this document has been executed. Base revision: `d1055a1` (main after PR #3). Driver: ARM64 `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`, adapter `PCI\VEN_17CB&DEV_1107` (WCN7850, FastConnect 7800).

## Contents

- [1. Goal, claim and equipment](#1-goal-claim-and-equipment)
- [2. Why a window bound is a proof](#2-why-a-window-bound-is-a-proof)
- [3. Conditions and their tests](#3-conditions-and-their-tests)
- [4. Phase 0: raw-route check](#4-phase-0-raw-route-check)
- [5. Collection campaign](#5-collection-campaign)
- [6. Analysis](#6-analysis)
- [7. Pass and fail criteria](#7-pass-and-fail-criteria)
- [8. Outcomes and next steps](#8-outcomes-and-next-steps)
- [9. Code layout and tests](#9-code-layout-and-tests)
- [10. Risks and limits](#10-risks-and-limits)
- [11. Relation to other work](#11-relation-to-other-work)

**Terms used here:**

- **TSF:** the 802.11 Timing Synchronization Function counter, in microseconds. A connected station keeps its TSF aligned to the access point's beacons.
- **SoC counter:** the second counter in the TSF report. Its clock domain is unknown; testing it is part of this design.
- **QPC:** Windows `QueryPerformanceCounter`, 10,000,000 ticks per second on this machine.
- **Action 4:** the firmware TSF timestamp action that, in Qualcomm's public WMI headers, requests a TSF and QTIMER capture. Its behaviour on this firmware is what the campaign tests.
- **Window:** the QPC interval from just before a request is sent to the driver's trace timestamp for the matching report.
- **Epoch:** a period of continuous association with one access point. Samples are never combined across epochs.

See the [glossary](../glossary.md) for other project terms.

## 1. Goal, claim and equipment

**Goal (selected 2026-10-07):** the current Qualcomm machine tracks its associated access point's TSF with absolute error below 1,000 us at a stated QPC instant.

**Equipment:** the laptop and its existing access point only. No second node, GPS/PPS or wired reference is available (user decision, 2026-10-07). The access point is a consumer router without shell access, so its TSF cannot be read independently on the access point itself.

**The claim has two links:**

1. **QPC to station TSF:** proven by this campaign, with a worst-case bound.
2. **Station TSF to access point TSF:** an explicit assumption, supported by the 802.11 requirement that an infrastructure station adopts the access point's beacon timestamps and by a coarse falsification check (section 3). With laptop-only equipment this link cannot be measured at sub-millisecond resolution, and the report must say so.

**Out of scope:** UTC accuracy, measured agreement with another device, access point oscillator stability, Windows clock discipline, and the separately quarantined private campaign of 2026-10-03.

## 2. Why a window bound is a proof

Within one epoch, model the station TSF as a straight line in QPC time:

`TSF = r * Q + c`

For sample `i` the report gives TSF value `T_i`, and the host records `L_i` (QPC just before the request) and `U_i` (QPC trace timestamp of the matching report). If the firmware captured the TSF after the request left the host and before the driver logged the report, the capture instant lies in `[L_i, U_i]`. Then, for a positive rate:

`T_i - r * U_i <= c <= T_i - r * L_i`

TSF is an integer microsecond counter and QPC an integer tick counter, so the implemented constraint widens each window by one TSF microsecond and one QPC tick: `T_i - r * (U_i + 1 tick) <= c <= T_i + 1 - r * L_i`. A 200 ppm prior on `r` keeps the feasible set bounded.

Each sample contributes two linear constraints on `(r, c)`. The feasible set over all samples in a window is a convex polygon, computed exactly with rational arithmetic, as in the existing [counter-rate analysis](../clock-models/counter-rate-identifiability.md). **The proven error at a query instant `Q` is half the spread of `r * Q + c` over the feasible polygon**, reported against the polygon's centre. This is a worst case under the stated conditions, not a statistic.

The earlier campaign measured request completion in tens of microseconds and report emission in hundreds of microseconds after the request ([latency audit](../acquisition/private-acquisition-latency.md)). A single window is therefore expected to be well below 1,000 us. Intersecting many windows narrows the bound further. The roughly 1.6-second delay before the observer reads a record does not widen the window, because `U_i` is the driver's own trace timestamp.

## 3. Conditions and their tests

The bound holds only if these conditions hold. Each one has its own test, and a failed test rejects the sample or stops the run.

| Condition | Test | Failure handling |
|---|---|---|
| **Attribution:** each report answers the request in its window | Exactly one request in flight. Other activity, including scans, also produces TSF reports, so reports are classified rather than assumed to be ours: a report outside every window is **foreign** and counted; two reports inside one window reject that sample; a window that times out records an **own loss**. If Phase 0 shows that foreign reports carry a different vdev, or recovers the report-type field, that filter is applied first. | Foreign reports do not stop the run. The residual risk, an own loss coinciding with a foreign report inside the same window, is estimated as own-loss count x foreign-report rate x the 2,000 us acceptance window and reported per run |
| **Freshness:** action 4 returns a newly captured value | For consecutive samples `i` and `j`, with QPC converted to microseconds, `T_j - T_i` must lie inside `[0.9999 * (L_j - U_i) - 1, 1.0001 * (U_j - L_i) + 1]`. The fixed 100 ppm band exceeds any crystal tolerance, uses no fitted value, and still exposes a cached value by seconds. Repeated values or regressions are violations. | Reject the sample. More than 1% rejected in a run fails the freshness condition for that run |
| **Shared clock:** station TSF equals access point TSF | Assumption based on the 802.11 rule above. Coarse check: each public-cache beacon timestamp (`WlanGetNetworkBssList`) must not exceed the station TSF predicted for that query's QPC time by more than 1,000 us. A beacon can't be stamped after the instant it is read. The reference instant is the QPC reading taken when the cache call returns: the 5-minute smoke run on 2026-10-07 showed the call takes about 10 ms and the cache can refresh during it, so the call's start is not a valid reference (two false violations, both explained by this). | Any violation stops the analysis. The shared-clock link is reported as falsified |

**SoC domain test.** Fix the rate at exactly 10 QPC ticks per SoC unit and look for one offset `k` such that `10 * SoC_i + k` lies in `[L_i, U_i]` for every sample in the **whole run**. Also compute the feasible interval of the SoC-to-QPC rate across the run with no rate constraint.

- If such a `k` exists, and the feasible rate interval includes exactly 10 ticks per unit, SoC is reported as **compatible with the QPC domain**. The containment test is the decisive one; an hour of windows of a few hundred microseconds resolves the rate only to roughly 0.1 ppm. Windows can then be combined across the full run without drift, and each report gives its TSF at a known QPC instant.
- Otherwise SoC is reported as a separate clock, and the 60-second window bound from section 6 is the result.
- Compatibility is not proof of a shared oscillator. The report must state the test, not a stronger conclusion.

**Saved-data checks (2026-10-07, read-only, campaign `ecfaed68f20e`):**

- All 18 saved action-4 windows measured 214 to 740 us; the IOCTL itself returned in about 50 us.
- Scan-triggered reports carry vdev 0, the same as ours, so vdev cannot filter them. Every one of our requests logs a `command` record (action 4, vdev 0) before its report group, and the six scan-triggered groups in three scan captures had none. Attribution therefore uses the command record and a 2,000 us acceptance window.
- The SoC counter fails the fixed 10-ticks-per-unit test by 365 to 688 us within about 24 seconds in all six mixed runs, so SoC is unlikely to share the QPC domain.
- Without a limit on the rate, a single window leaves the polygon unbounded. A 200 ppm physical prior on the TSF-to-QPC rate is added; the fitted rates in saved runs lie between about -66 and -23 ppm.

## 4. Phase 0: raw-route check

**Purpose:** decide whether the full 60-byte TSF report can be captured alongside the logged values. The bytes the driver drops include `tsf_id`, `mac_id` and the uplink-delay-or-TSF report-type word ([field coverage](../tsf/tsf-association-and-quarantine-disposition.md)). These would strengthen the attribution and shared-clock conditions. They are not needed for the window bound itself.

**Already established by other work (2026-10-07, in progress in the main checkout):**

- The firmware-log path formats firmware diagnostics as text before trace submission, so raw bytes are not available from it.
- The WlanLogger provider's enable callback has a mutex wait without a finite timeout.
- The vendor WPP package's level `0xff`, full-logging and trigger scripts change extra driver state and restart the adapter, so they are unsuitable.
- The vendor script enables firmware diagnostics only for `DEV_1101`. This adapter is `DEV_1107`.

**Remaining offline questions (about half a day, read-only):**

1. Find the callers of the driver's two generic 16-byte hex-dump format strings, and of the format string `receive WMI_VDEV_TSF_REPORT_EVENTID on %d, tsf: %lu %lu`.
2. Determine which debug level and component bits gate each caller.
3. In the saved scan-experiment and campaign captures, compare the logged vdev of reports that followed our requests with reports produced during scans. A consistent difference becomes the first attribution filter in section 3.
4. Any raw capture must record the actual received length separately from the decoded 60-byte layout. If firmware sends 48 bytes, the words the driver pads to reach 60 bytes (including the candidate TQM words at `0x30` and `0x34`) are not firmware output.

**Outcomes:**

- **Raw dump reachable:** propose one reversible registry change and one adapter restart for a short test capture, approved separately by the user. If it works, the campaign records raw bytes and adds the report-type and clock-ID checks to section 3. Logging stays at the same level for every run.
- **Not reachable:** the campaign runs on the logged values. The missing fields are listed as a limitation. The window bound is unaffected.

Phase 0 is time-boxed. It must not grow into another open-ended search for a raw export.

**Result (2026-10-07):** question 3 is answered: scan-triggered reports carry the same vdev as ours, so attribution uses the command record instead (section 3). Questions 1, 2 and 4 (hex-dump callers, their gating, and raw received length) were not pursued in this session. The campaign therefore runs on the logged values, and the missing report-type and clock-ID fields stay a stated limitation. The window bound does not depend on them.

## 5. Collection campaign

**Reused tools:** `research/tsf/qualcomm_probe.py` (action 4 only), `research/acquisition/live_observer.c` and `research/tsf/decode_tsf_etl.c`. The provider is WlanLogger `{bb6f5b93-635c-47be-816f-e895e77064a8}`, as in the earlier campaign.

| Setting | Value |
|---|---|
| Firmware action | 4 only. Never 3, 5 or 6 |
| Requests in flight | One |
| Report timeout | 5 seconds. A timeout rejects the sample and counts an own loss; more than 1% own losses stops the run |
| Request spacing | Nominal 2 seconds, never below the earlier 500 ms minimum. Actual spacing is recorded; the earlier campaign achieved about 4 seconds |
| Run length | 60 minutes idle, then 60 minutes under load |
| Load | The earlier campaign's SHA-256 CPU workload (10 ms work, 10 ms sleep), plus a looped HTTPS download of a public 100 MB test file (OVH, Hetzner fallback), with throughput recorded. A download that makes no progress for 60 seconds fails the run. The first load attempt (2026-10-07) silently ran CPU-only because the original Cloudflare endpoint returned HTTP 403 |
| Trace session | New, uniquely named and owned. QPC event clock, frequency recorded. One sequential file capped at 3,072 MiB (run stops at 3,000 MiB; a loaded run with a working download measured about 26 MiB per minute, about 1,550 MiB per hour), with 8 KB buffers, 256 to 2,048 of them, after the first load attempt lost 425 events in one burst under CPU load. A 256 KB setting was tried first and rejected: ETL files hold whole buffers flushed every second, so the file grew about 103 MiB per minute instead of about 12; reaching the cap stops the run. The first 60-minute idle attempt on 2026-10-07 stopped at the original 250 MiB cap after about 25 minutes, because the trace grows by 10 to 12 MiB per minute |
| Beacon check | Public `WlanGetNetworkBssList` read every 10 seconds. A read where the cache holds zero or several entries for the connected BSSID is recorded as a skip, not a stop; an association change during a read still stops the run. A load attempt on 2026-10-07 stopped on such a cache gap with the association unchanged |
| Elevation | One UAC approval per run |

**Change to approved limits:** the earlier campaign capped each capture at 120 seconds. A 60-minute single-session run is a deliberate extension, so starting the first run needs explicit user approval. The alternative, 30 chained 120-second sessions, repeats the provider enable and disable 30 times and so multiplies the enable-callback risk in section 10.

**Stop conditions** (any one stops the run, which is then quarantined and excluded from results):

- the adapter is not Up, or the driver hash changes;
- the connected BSSID, channel or PHY changes;
- a report cannot be decoded;
- a request call fails, or own losses exceed 1% of requests;
- the trace reports lost events or buffers;
- the trace file reaches its cap;
- a controller operation exceeds its 5-second supervisory deadline.

**Identity record:** adapter, driver hash, BSSID hash, channel, PHY and association state are recorded before and after each run. A reconnection inside a run starts a new epoch.

**Evidence storage:** raw traces and receipts go to the private evidence repository. The public repository receives code, synthetic fixtures and a scoped summary.

## 6. Analysis

1. Validate each run: reject the whole run on any stop condition; reject individual samples for freshness violations.
2. Split each epoch into sliding 60-second windows advanced by 10 seconds. At about 2 to 4 seconds per sample, a window holds about 15 to 30 samples. An unmodelled rate change of 1 ppm adds at most 60 us across a window.
3. Compute each window's feasible `(r, c)` polygon exactly, and its proven error at every sample instant inside the window.
4. A window with an empty polygon is **infeasible**. Infeasible windows are reported with their samples and never dropped.
5. Run the SoC domain test once per run.
6. Run the beacon coarse check for every cache read.

**Reported per run (idle and load separately):**

- median, p95 and maximum proven error over all feasible windows;
- share of run time covered by feasible windows;
- count of rejected samples, by reason;
- foreign-report count and rate, own-loss count, and the estimated misattributed-sample count;
- infeasible-window count and positions;
- SoC domain test result, and the unconstrained SoC-to-QPC rate;
- beacon-check violation count;
- actual request spacing and window-width distribution.

## 7. Pass and fail criteria

These are fixed before any collection and must not change after seeing data.

**The claim passes only if, in both the idle and the load run:**

- every feasible window's maximum proven error is below 1,000 us;
- feasible windows cover at least 90% of the run's duration;
- rejected samples are at most 1% of samples;
- the estimated number of misattributed samples (section 3) is below 0.05 per run;
- the beacon check has zero violations.

A proven error of 100 us or less is reported as a stretch result, not as a pass condition. A run stopped by a stop condition is a failed run, not a pass with a smaller sample.

## 8. Outcomes and next steps

| Result | Meaning | Next step |
|---|---|---|
| Pass, SoC compatible with QPC | Firmware-captured pairs with a run-long bound, likely tens of microseconds | Propose a `userspace-clock` provider contract for this source |
| Pass, window method only | Sub-millisecond bound proven for these conditions, likely hundreds of microseconds | Same, with the larger stated bound |
| Freshness failure | Action 4 can return cached values | Investigate refresh conditions before any rerun |
| Many infeasible windows | TSF steps or a wrong drift model | Shorten windows and study TSF adjustment behaviour |
| Beacon-check violation | Station TSF not tracking the access point, or a wrong mapping | Stop; the shared-clock assumption is falsified |
| Stopped runs | Lifecycle or delivery problem | Diagnose the stop cause; no result is claimed |

## 9. Code layout and tests

Branch `prove-tsf-host-bound`, created from `d1055a1`, with its own pull request.

| New module | Responsibility |
|---|---|
| `research/clock_models/bracket_bound.py` | Exact window constraints, feasible polygons and proven-error output |
| `research/clock_models/soc_domain_test.py` | Fixed-rate containment test and unconstrained rate fit |
| `research/clock_models/beacon_consistency.py` | Coarse shared-clock falsification check |
| `research/acquisition/run_bound_campaign.py` | Orchestrates the existing probe, observer and cache collector; enforces stop conditions and receipts |

Each module is written test-first against synthetic fixtures. Required rejection fixtures:

- a stale value repeated across two windows;
- a foreign report outside every window, which must be counted without stopping the run;
- two reports inside one window, which must reject that sample;
- an own loss followed by a foreign report in the next window, which must feed the misattribution estimate;
- an epoch change inside a run;
- an infeasible window;
- a beacon timestamp ahead of the predicted station TSF;
- a SoC series with a 1 ppm rate offset that must fail the domain test.

No live request is sent until the modules and their tests pass, Phase 0 is complete, and the user approves the first run.

## 10. Risks and limits

- **Trace enable callback:** the WlanLogger enable callback can wait without a finite timeout. A controller deadline cannot prove kernel rundown. One session per run limits the exposure; a hang is a failed run.
- **Exact-build scope:** the private IOCTL and RVAs apply only to the pinned driver hash. Any driver update invalidates the results and the tooling gate.
- **Logging overhead:** trace and probe activity consume CPU and may widen windows. That affects the size of the bound, not its validity.
- **TSF adjustment:** the station may step or slew its TSF on beacon reception. Short windows and infeasible-window reporting expose this rather than hide it.
- **Multi-link operation:** the FastConnect 7800 can operate more than one link. Without `tsf_id` and `mac_id`, the report's clock is assumed to be the associated link's TSF.
- **Shared-clock link:** it remains an assumption with a coarse check. Proving it at sub-millisecond resolution needs equipment that is out of scope here.
- **Quarantine:** the 2026-10-03 private campaign remains quarantined. Passing this design does not release or relabel its records.

## 11. Relation to other work

- **Public-cache experiment (in progress, main checkout, 2026-10-07):** two 200-observation runs of `WlanGetNetworkBssList` produced held-out residuals of 32 to 52 ms, rejecting the cached-pair model as a sub-millisecond solution. This design uses the same public cache only for the coarse shared-clock check.
- **[Hardware-route decision](../evidence/hardware-route-decision-2026-10-06.md):** the complete-event route remains no-go. This design does not depend on it. It uses the already exercised action-4 request and its logged report.
- **[Counter-rate identifiability](../clock-models/counter-rate-identifiability.md):** the 18 existing action-4 samples show about 7.3 to 8.0 ppm between TSF and SoC increments and a 176 to 194-unit spread in their difference. This campaign targets about 900 to 1,800 samples per run so those observations can be tested rather than re-fitted.
- **`userspace-clock`:** no provider is enabled by this design. A passing result supports a separate provider proposal.
- **Gap register (2026-10-07, Codex planning output):** this design is one concrete attempt at G02, G04, G20 and G21, and partially addresses G03, G06, G08, G24 and G26. G01 and G09 (an independent access point comparison) cannot be closed with a consumer router and no second reference, which is why the shared-clock link stays an assumption. The alternative routes G30 to G54 (QUTS, QMSL, WPP raw bytes, FTM, QDSS, ART2/UTF, packet log, MLO and CAPTUREH) are deferred until this campaign reports a result.

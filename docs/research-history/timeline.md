# Research timeline and changes of direction

The research progressed from source discovery to live diagnostic acquisition, then to evidence ownership and conditional clock models. Each phase below records what we tried, what happened and what changed in the interpretation. Calendar dates use America/New_York; some original filenames and reports use the following UTC date. Commit order alone is not experiment time.

[Research guide](README.md) · [Results](results-and-validation.md) · [Hypotheses](hypotheses-and-lessons.md) · [Archive](../../archive/README.md)

## 1. October 1–2: identify sources and distinguish APIs from counters

**Goal:** find an accessible Wi-Fi hardware clock or packet-timestamp route on the available Windows equipment. Inspect ALFA AWUS036AXML/MT7921AUN packages, pinned mt76 source and the WiFi PTP reference; investigate the active Qualcomm driver and standard Windows timestamp APIs.

**Steps and results:** package/source inspection located MediaTek TSF and RX/TX fields, plus a Windows private register dispatcher. The supplied Windows package had x86/x64 variants, no ARM64 variant, and no live MediaTek register experiment was qualified. WiFi PTP was an ath9k reference, not a ready-made API for the USB MediaTek device. Qualcomm private commands exposed diagnostic counters; standard timestamp queries returned `23 / ERROR_CRC`. Repeated diagnostic captures and selected FTM operations worked. The error left standard capability unknown; it did not establish absent hardware support.

**Direction change:** keep Qualcomm/Windows as the selected route, study the actual asynchronous report path, and treat register addresses or function names as leads requiring an operation contract.

Evidence: [AXML](../adapters/axml.md), [Qualcomm](../adapters/qualcomm.md), [Windows follow-up](../windows-timestamps/windows-timestamp-path-followup.md), [FTM provenance](../ftm/ftm-result-provenance.md). Publication begins at [5a42286](https://github.com/Protonmatter/wifi-hardware-time/commit/5a4228690106469944510d19e0bd1331388dd008); repeated series and latch work followed at `c960dcc` and `e7da355`.

## 2. October 2: guarded acquisition succeeded, but delivery was slow

**Goal:** make diagnostic acquisition repeatable, attributable to one stated profile and safe to stop. Build finite controllers with exact source/driver pins, explicit interfaces, traces, observer health, workload profiles and saved receipts.

**Result:** 12/12 captures and 138/138 requests completed across idle/workload and read/mixed phases; 14 owned trace sessions were cleaned up. Eighteen capture actions refreshed the second counter and 108 eligible reads reused it. Log-to-reader delivery had roughly 1.6-second medians, far larger than the request-call time. Simultaneous TSF/SoC latching and hardware-to-QPC accuracy were not established.

**Lesson:** successful collection is a bounded acquisition result. Request completion, firmware sampling, driver logging and application availability need separate timestamps.

Evidence: [completed campaign](../acquisition/acquisition-campaign-2026-10-02-results.md), [latency audit](../acquisition/private-acquisition-latency.md), [clock relationships](../clock-models/clock-relationship-investigation.md); acquisition qualification commit `a65ab66`.

## 3. October 3: later unmatched reports broke request-ownership assumptions

**Goal:** repeat the campaign with corrected observer health checks. The corrected observer passed passive checks, but the private repeat stopped during its third capture after extra reports could not be assigned to the issued requests.

**Result:** 33 action-3 requests were issued; the first two complete bundles held 24 observations. The rejected capture and quarantine were retained. Three controlled scans then produced two TSF report groups each without private timing requests. All three scan trials failed the original four-second completion criterion; the third retained a tail showing completion around 6.027 seconds. These were three instrument revisions, not three identical successful repetitions.

**Direction change:** distinguish operational scan association from firmware transaction identity. Preserve foreign reports and failures rather than pairing every next report with our request. Quiet time or a restarted observer does not clear firmware work or quarantine.

Evidence: [quarantine](../acquisition/private-campaign-2026-10-03-quarantine.md), [association review](../tsf/tsf-association-and-quarantine-disposition.md), [scan results](../acquisition/scan-tsf-results-2026-10-03.md), [passive cleanup](../acquisition/passive-and-retrieval-validation-2026-10-03.md); commits `911c7c7`, `a82c07d`, [fdcc22f](https://github.com/Protonmatter/wifi-hardware-time/commit/fdcc22f80ad173a2f4f2844c0f6b666794fda54a). PRs #1 and #2 merged, establishing the topic layout and historical reproduction snapshots.

## 4. October 3–5: trace the producer, byte ownership and return boundaries

**Goal:** obtain a complete event with raw fields, identity and explicit lifetime. Trace RX/FTM/management data, packet logs, MLO state, WMI/HTC/HIF receive buffers, DMA backing, cleanup and driver-to-application returns.

**Results:** static work located producer fields and specific reductions or lifetimes. A ring cursor can become visible before record copying; two of ten finite model schedules defeated equal-copy/stable-position checks. Copying a pointer-bearing wrapper did not retain its payload. General command, completion and event histories preserved different data. The saved-byte audit found numeric text plus one NUL, with no hidden trailer, in 88 selected records from two captures. That absence applies only to that selection.

Authored owned-record exporters, a concurrent response broker and strict decoders established useful software contracts and rejection behavior. One elevated service GET returned eight expected test bytes through the installed driver. It proved that operation's transport; its 166.5-us API duration was not a radio sampling bracket. Nested IHV selectors included state-changing operations and stayed deferred.

**Direction change:** aim at a supported copy/return point before timestamp information is reduced. Existing dump paths, cursor polling, packet capture resolution and alternate endpoint names did not remove the producer problem.

Evidence: [ring counterexample](../memory-ring/timing-boundary-investigation-2026-10-03.md), [management handoff](../adapters/qualcomm-management-rx-handoff.md), [ingress](../tsf/tsf-event-ingress-and-owned-copy.md), [DMA](../tsf/dma-backing-contract.md), [shutdown](../tsf/receive-shutdown-contract.md), [byte audit](../tsf/saved-trace-byte-audit.md), [broker](../evidence/raw-event-response-broker.md), [positive control](../evidence/device-service-positive-control.md), [IHV map](../adapters/ihv-query-producer-map.md).

## 5. October 4–6: vendor software yielded real ownership paths, not a qualified Wi-Fi source

**Goal:** determine whether QPST, QXDM, QUTS, QUD, QMSL and QSPR already supplied the missing event route. Extract/inspect files as data, trace exact images and perform bounded discovery where separately authorized.

**Results:** later packages superseded early missing-runtime conclusions. QUTS client deserialization allocated owned payload arrays; native receive and complete-frame paths made copies. Live discovery evidence established particular adapter-key query failures, not a usable firmware protocol. QXDM time accessors could fall back to host time. QMSL queue getters had capacity, timeout and formatting hazards; V2 callbacks supplied an original pointer/length with a lifetime that must be respected. Installed QMSL 6.1.365.1 required a fresh trace; historical RVAs could not be reused. Its worker/listener path was connected statically, with live producer and shutdown limits remaining.

**Decision:** the complete-original-event route was no-go pending supported/vendor/instrumented producer access. The public/private evidence split and repeatable static inspection/indexing were substantial completed work. Downstream diagnostic replay and host API acceptance were separate local software/profile results.

Evidence: [archive transport findings](../adapters/qualcomm-archive-transport-findings.md), [QUTS enumeration](../evidence/quts-enumeration-2026-10-04.md), [endpoint receive](../adapters/quts-endpoint-writer-and-receive.md), [QMSL queue](../adapters/qmsl-diagnostic-queue.md), [installed 6.1.365.1](../adapters/qmsl-runtime-365.md), [route decision](../evidence/hardware-route-decision-2026-10-06.md), [PR #3 review](../overview/pr3-review-2026-10-06.md). PR #3 merged at [d1055a1](https://github.com/Protonmatter/wifi-hardware-time/commit/d1055a1078456a5ef9e98fcee476d68ac6db38fb) on October 6 local time (October 7 UTC).

## 6. October 7–8: long runs supported a conditional station-TSF/QPC bound

**Goal:** test a predeclared bound from action-4 request/report windows. Implement structural screening, exact affine polygons, rate-only checks, trace/workload acceptance and a coarse beacon consistency test.

**Result:** one counted hour idle and one under CPU/network load passed the conditional campaign criteria. Median affine half-widths were 134.8/139.6 us; maxima 352.2/190.8 us. The 100-us stretch goal was missed. Five other long-run attempts stopped on trace limits, loss, failed network load or cache ambiguity; a short smoke was not counted. All attempts remain in the [original results](../acquisition/tsf-host-bound-results.md).

**Critical correction:** a synthetic constant 5-ms capture delay still passed the freshness screen. A rate-varying clock could leave the affine interval between samples. Therefore the result remained conditional on capture inside the window and, for the affine model, constant rate within each 60-second span. Retrospective rate-only maxima were 894.669/785.584 us. Neither number established physical accuracy or live availability.

Evidence: [methodology and attempts](../acquisition/tsf-host-bound-methodology.md), [bound results](../acquisition/tsf-host-bound-results.md), [model mathematics](../clock-models/tsf-mathematics.md); PR #4 and historical head `64da8f2`.

## 7. October 8: availability, settlement and persistent acquisition

**Goal:** make the conditional clock honest for a real reader. Separate capture from availability, reject incompatibility before updating the model, expose acquiring/tracking/stale/invalid states, and preserve raw/provisional timestamps before later settlement.

**Results:** arrival-aware replay had much lower coverage than a model that treated ETW log time as immediate availability. Two-phase settlement produced conditional sub-millisecond intervals for every point on the declared one-second grids. A persistent worker then completed one five-minute idle smoke: 139 normal pending-to-success operations, 138 screened samples and clean normal shutdown. Requested one-second spacing produced 2.005-second median and 4.009-second maximum gaps because the report wait remained.

**Direction change:** use two-phase event timestamps as the leading application path, while explicitly retaining stale periods, settlement waits and online admission as separate work. The persistent smoke did not qualify cancellation, firmware drain or persistent hour/load operation.

Evidence: [causal replay](../clock-models/causal-provider-replay.md), [settled timestamps](../clock-models/settled-timestamps.md), [persistent smoke](../acquisition/persistent-tsf-smoke-2026-10-08.md), [sampler contract](../acquisition/persistent-tsf-sampler.md). Preserve original heads `ebae8cc`, `c620f47` and persistent baseline [02459e7](https://github.com/Protonmatter/wifi-hardware-time/commit/02459e780f9912b31c2ece951cf824d941972156).

## 8. October 8: review changed evidence handling and numerical interpretation

The integrated review accounted for 23 research review threads and compared corrected code against the same hashed inputs. Corrections covered actual run acceptance, source identity, cleanup, loss counting, stale intervals, rounding allowance, available brackets and settlement causality. Tracking coverage changed because the integer estimate's 0.5-us allowance was included. Later corrections preserved finalized successful requests across later session failure, hardened quarantine and cleanup bookkeeping, and versioned continuity, arrival order, settlement overlap and SoC quantization.

The [version comparison](results-and-validation.md#why-older-numbers-differ) retains the old and corrected numbers. Source fixes did not rerun or retroactively qualify hardware. PR #7 integrated the stack; #5 and #6 were closed as historical components. PR #8 merged corrections, and #9 merged directly readable diagram previews. Their exact statuses are in the [publication snapshot](publication-status.md).

Evidence: [integrated review](../overview/pr-reconciliation-2026-10-08.md), [post-merge corrections](../overview/postmerge-corrections-2026-10-08.md), [corrected result JSON](../overview/postmerge-corrections-2026-10-08.json). Review-source pins are `498758f` and `0f41db0`; merged documentation baseline is `e9d71b8`.

## 9. October 9: consolidate the account without changing the experiment

This documentation review preserves every pre-refresh tracked Markdown file and selected earlier milestone entry points. It adds the linked history, result/hypothesis summaries, full source catalogue and prioritized next steps. No measurement, driver request, tracing session, vendor invocation or system-clock change is performed. Private unpublished findings are maintained separately. PR #10 was corrected to remove inactive controls and hover/focus affordances from static exports, independently reviewed and merged at `da4f55e` after passing Linux/Windows checks. The documentation refresh follows as a separate PR.

Read [what comes next](next-steps.md), or compare the [archived versions](../../archive/README.md) in date order.

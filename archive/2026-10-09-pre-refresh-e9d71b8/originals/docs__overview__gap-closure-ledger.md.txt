# Qualification gap closure ledger

This page tracks which research questions have useful answers and which clock capabilities still lack evidence. Scans can introduce extra counter reports, and software tests can reject unsafe assumptions. Safe hardware sampling, complete record retrieval and calibrated synchronization remain open, so downstream applications must keep those capabilities disabled or experimental.

<!-- current-context:2026-10-08 -->
**Current context (2026-10-08):** The persistent diagnostic-TSF profile has a clean five-minute live smoke and conditional offline timing results. Complete original-event export, firmware-drain qualification, online admission and physical/shared-clock accuracy remain separate open gates. The older [hardware route decision](../evidence/hardware-route-decision-2026-10-06.md) remains relevant to complete-event producer access; it does not erase the later diagnostic-window result.
<!-- /current-context -->

**Key terms:** A gate is an explicit requirement before a capability may be enabled. Calibration compares results against an independently characterized reference. A model is a mathematical or software explanation, not a measurement by itself. See the [glossary](../glossary.md).

Updated 2026-10-08, America/New_York. This ledger distinguishes an answered
research question from a passing acquisition profile or enabled clock capability.
The private campaign remains quarantined.

## Persistent diagnostic-TSF status, 2026-10-08

<!-- tsf-headlines:smoke -->
**Current retained smoke analysis:** 139 recorded requests, 138 offline-screened samples; **92.862589%** tracking coverage under the conditional integer-estimate uncertainty threshold. **297/297** event-grid points settled, with median/max rate-only half-widths of 280.429/614.883 us and median wait 2.341 s. [Versioned results and source pins](postmerge-corrections-2026-10-08.json). This is offline-screened replay of the retained capture, not online admission or calibrated AP/UTC accuracy.
<!-- /tsf-headlines:smoke -->

| Gate | Current disposition | Evidence / next dependency |
|---|---|---|
| Persistent sampler software | Implemented, independently reviewed and offline-tested | [Contract and acceptance map](../acquisition/persistent-tsf-sampler.md); the audited per-request probe is unchanged |
| First live persistent smoke | Passed for normal completion on the exact build | [139 requests, 138 screened samples and clean lifecycle](../acquisition/persistent-tsf-smoke-2026-10-08.md); long-run/load and real failure paths remain open |
| Conditional TSF/QPC results | Useful with explicit assumptions | [Mathematics](../clock-models/tsf-mathematics.md); versioned numerical summary above, with offline screening and capture assumptions |
| Report-wait decoupling / online admission | Not implemented | Need supported report lifecycle/association and causal admission contracts before consumer ingestion |
| Physical/AP/UTC/multi-node accuracy | Unqualified | Need independent reference and combined error budget; `physical_bound_proven` remains false |
| Publication / merge | Separate from qualification | [Sequenced roadmap](persistent-tsf-next-steps.md); verify exact-head CI and dependency stack, then obtain the relevant user authorization |

## Complete-event track snapshot, 2026-10-06

| Slice / gate | Current disposition | Evidence / next dependency |
|---|---|---|
| S0 current handoff | Documentation stabilization and component software review complete; subsequent publication/merge tracked on PR #3 | [Final review](pr3-review-2026-10-06.md): four reproduced findings corrected and 344 configured tests passed. The [220-file map](pr3-component-review-map-2026-10-06.md) remains the published baseline inventory; local review is not a GitHub approval or hardware qualification |
| S1 QMSL current-build trace | Completed static slice; do not repeat without changed evidence | [6.1.365.1 callback, worker, ownership and shutdown evidence](../adapters/qmsl-runtime-365.md); attributed live endpoint and bounded lifecycle remain open |
| S2 route decision | **No-go for the complete-original-event export route** | [Gate-by-gate decision and reopening criteria](../evidence/hardware-route-decision-2026-10-06.md); primary Windows producer requires demonstrated supported/vendor/instrumented access |
| S3 downstream diagnostic replay | Implemented and reviewed locally; 15 focused tests pass | Five pinned source-record profiles, immutable observations, explicit digest/source selection and CLI; isolated standard-library-only smoke passed; hardware/conversion capabilities remain disabled |
| S4 producer / S5 G1a first event / G1b lifecycle | Gated | Need actual route integration, then a reviewed finite acquisition and ownership/lifecycle results; fixed-byte return is not the required event |
| S6 hardware/host relationship / S7 synchronization | Gated separately | Source semantics, fresh sampling and independent reference/controlled peers remain missing |
| S8 host API acceptance | Declared local profile passed; not a consumer SLA or accuracy claim | 12 runs / 300,000 record calls passed fixed 5 us / 250 us per-reader and pooled p99 rules. Corrected process/provenance rejection checks requalified the unchanged evidence; four calls exceeded 1 ms and the maximum was 2.5444 ms |
| S9 spectral preservation | Local nine-file patch preserved and verified; not published | Coordinator reports exact hashes, successful application to the pinned base, 43 tests and local parser/managed/render checks; no spectral command, commit or capture claim |
| WPP External 2.3.1.1 | Installed files and state-changing trace helpers inspected | [88-file assessment](../evidence/wpp-external-2311-file-assessment.md); useful collection/configuration leads, no new complete-event producer or live route |
| Dedicated Linux backend | Conditional alternate, not selected | Requires physical compatible hardware/OS and explicit backend selection before implementation and live qualification |
| Nested IHV controls / private campaign | Deferred / quarantined | No reopening or new lifecycle authorization in this documentation change |

Publication snapshot before the review corrections: [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3)
was open at `aca5b7ca7c96ca8731f15202361c34faf003f350`, against remote main
`0e866ed6b2409231c100af75a6aef97c6bdd2fa3`. Both `protocol` and
`windows-syntax` succeeded in the exact-head
[PR run](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37558308352)
and [push run](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37558305170).
These hosted checks predate this local documentation refresh; no hosted check
for uncommitted changes is claimed. No submitted GitHub PR reviews were present.

The subsequent [software review](pr3-review-2026-10-06.md) covers the accumulated
PR and local status changes, with source fixes and focused regressions added.
All 344 configured tests passed; ten offline PowerShell helper runs and 34 parser
checks passed. At review completion those corrections were local; subsequent
head-specific hosted checks and merge state are recorded on PR #3. Historical
evidence below retains its original source and validation scope.

The initial documentation refresh passed 14 navigation, index,
diagram and repository-layout tests with zero skips. The index regenerated and
an immediate second apply returned unchanged; index/diagram consistency and Git
whitespace checks passed. The 220-file inventory reconciles to the remote PR
counts. The full native/private-fixture suite and hardware/vendor execution were
not rerun for this documentation-only change.

S3/S8/S9 outcomes above were supplied by their coordinating implementation and
qualification tracks; this documentation pass did not independently rerun them.
Their scope is local software/profile/preservation evidence, separate from this
repository's hardware gates and hosted checks.

The downstream `userspace-clock` local tree passed 64 tests after review fixes.
Its diagnostic contract is `docs/contracts/diagnostic-observation-v1.md`;
the host result and separate verifier correction are recorded in
`docs/qualification/host-api-acceptance-2026-10-06.md` and
`host-api-acceptance-post-review-2026-10-06.md`. The old measurement receipts
were preserved. These new implementation changes are uncommitted; existing
hosted CI does not cover them. The preserved spectral patch is likewise local.

## Earlier evidence retained with its original scope

The following findings and historical test counts retain their experiment dates.
The current table above supersedes older pending-work and publication statements.

The [current finding and correction ledger](../knowledge/current-findings.md)
adds the complete QPST/QXDM payload inventory, QUD request-boundary review and
the installed QUTS client-owned byte-array path. This closes a static client
ownership question, not the adapter-to-diagnostic producer association, server
publication, sampling or clock-conversion gates. Review the
[assumptions challenged by evidence](../knowledge/assumptions-and-corrections.md)
before reusing older absence or timestamp-origin interpretations.

Follow-up: [timing boundaries](../memory-ring/timing-boundary-investigation-2026-10-03.md)
narrows reset/crash ring consumers, reproduces a double-copy counterexample and
locates RX PPDU diagnostic fields. The [lifecycle cases](../acquisition/lifecycle-qualification-preparation.md)
are preparation only, as requested. None promotes a hardware clock capability.

The next [raw-export gate](../evidence/raw-timestamp-export-gate.md) remains closed.
[Normal RX tracing](../adapters/qualcomm-rx-export-boundary.md) now reaches the
OS-facing queue, without identifying a timestamp/packet-identity export in the
inspected routes. [FTM tracing](../ftm/ftm-buffer-ownership-and-identity.md) establishes
buffer reuse, wrapping request identity and separate parse completion. No live
complete-record acquisition has occurred, so later collector and acceptance
campaign work remains gated under the requested sequence.

[Private output tracing](../adapters/qualcomm-private-output-routes.md) also
narrows two candidates: `get_rx_stats` formats radio statistics and can refresh
internal state; the device-service test GET constructs fixed bytes. Neither
inspected output supplies the required timestamp record. These are offline
findings, with no new live command or allowlist expansion.

[FTM ingress tracing](../ftm/ftm-ingress-to-owned-response.md) connects the event
decoder to the registered FTM callback and post-callback cleanup. The temporary
decoded object and reusable merge buffer still have no established owned
application export. The inspected event-history writer retains event ID and
host system time, not the raw measurement payload.

[Vendor-tool inspection](../adapters/qualcomm-software-center-timing-leads.md)
found inherited WCN7850 RTT methods in the installed WLAN assembly. Its QMSL
runtime and QSPR kernel dependencies were missing in that bounded search;
the inspected four-byte buffer and 16-bit RTT result do not establish a complete
absolute timestamp export. The [2026-10-06 installation and trace](../adapters/qmsl-runtime-365.md)
supersede that runtime-absence snapshot. No vendor method or live operation was
executed in either static investigation.

The [TSF evidence reader](../tsf/tsf-evidence-reader.md) now returns owned
diagnostic observations from saved bundles. Offline integration replayed 138
historical observations from 12 captures, with zero clock-qualified results.
The [minimum transport decision](../adapters/qualcomm-minimal-transport-contract.md)
keeps new live acquisition and model admission blocked on unresolved attribution,
fresh sampling and quarantine disposition. Replay does not requalify that campaign.

The [association/quarantine review](../tsf/tsf-association-and-quarantine-disposition.md)
confirms two unattributed report groups and retains quarantine. The exact driver
expects a 60-byte TSF structure while its handler omits seven payload words.
A newer vendor header supplies candidate clock-identity/report-type labels;
firmware parity, live contents and their export remain unqualified.

[Autonomous frame decoding](../tsf/autonomous-management-tsf.md) now separates
peer-advertised TSF from local RX time and request identity. Authored beacon/probe
tests pass without requiring a host request token. Real capture provenance,
hardware clock mapping and synchronization qualification remain open.

The [management RX trace](../adapters/qualcomm-management-rx-handoff.md) identifies
event `0x7001`, its frame copy and queued radio metadata. The selected handler
does not read positions labelled local RX TSF in a matching-sized vendor reference
layout. An owned frame/local-timestamp export and firmware semantics remain missing.
The follow-up traces all twelve schema slots and selected downstream consumers:
the handler uses only the header/frame slots, and the inspected port callback
receives the reduced metadata. Conditional frame logging takes no original
firmware header. None of these paths establishes a paired timestamp export.

The [BSS serializer trace](../adapters/qualcomm-bss-serialization.md) now locates
the exact station indication, entry builder and eight-field serialization schema.
The selected builder leaves host-age information absent and conditionally copies
28 bytes of MBSSID profile state. The follow-up traces peer TSF and host tick-based
cache aging separately. The [Windows host-time trace](../adapters/windows-bss-host-time.md)
identifies the system-time source, conditional driver-age override and API copy.
An additional link-quality writer can refresh the stored host time without
replacing the frame; these cached fields are not a qualified simultaneous pair.

The [private return-path inventory](../adapters/qualcomm-private-output-routes.md#backward-trace-from-the-return-helpers)
finds 70 direct completion-call candidates and four calls to one serializer.
The newly traced allocated result carries interface information; it is not
connected to a complete timestamp producer. Its shared service also has a setter
branch, so no live opcode is admitted by this finding.

The [IHV binary bridge](../adapters/qualcomm-private-output-routes.md#ihv-binary-request-bridge)
connects another mutable binary request/result buffer to serialization and common
completion. A timing-producing selector and safe external binding are still missing.
In parallel, an [owned-export C prototype](../evidence/owned-timestamp-export-prototype.md)
implements a synthetic record boundary. Its software tests do not qualify the
hardware producer, physical event semantics, real cancellation or firmware drain.

| Gap | Current disposition | Evidence / next prerequisite |
|---|---|---|
| Can ordinary host activity produce additional TSF reports without our private request? | Operational pattern reproduced | Three controlled documented scan calls, each with a quiet baseline, one scan command and two TSF/SoC report groups; [results](../acquisition/scan-tsf-results-2026-10-03.md) |
| Why did the four-second scan-completion check fail? | Late completion directly observed in the final diagnostic run | Driver COMPLETED logs at about 6.025 s; both WLAN clients notified at about 6.027 s. Earlier runs ended before their completion could be measured |
| Has the scan comparison passed its original acceptance profile? | No | All three trials remain failed against four seconds; any changed deadline needs a separately declared experiment |
| Native-source provenance across checkout | Corrected and regression-tested | LF attributes restore exact qualified source bytes; selected native binaries unchanged |
| Normal observer cleanup | Observed again | Three owned trace/client/observer cleanups; no forced termination; trace absence and wrapper exit checked |
| Unique firmware request/report identity | Open | Operational scan association does not supply a firmware transaction ID; keep unassigned reports out of private-request evidence bundles |
| Freshness / simultaneous TSF and SoC capture | Open | Changed SoC values also occur around scans; neither an increment nor an action name proves a simultaneous latch |
| Hardware-to-QPC sampling relationship | Open | Need a qualified fresh bracket or documented hardware cross timestamp; regression and log receipt times are insufficient |
| Live memory-ring getter and consistent copying | Open; unsafe inference ruled out in a finite model | Direct consumers narrowed to reset/crash/recovery; two of ten schedules defeat equal-copy/stable-position checks without writer exclusion. Safe userspace reachability and publication semantics remain missing |
| Raw absolute FTM events | Open | Internal response comparison uses a request-context byte, not a qualified unique exchange/epoch token; absolute export, units and reference points remain missing |
| Arbitrary RX/TX packet timestamps | Open; RX diagnostic fields located | Descriptor +0x60/+0x68 are labeled high/low PPDU words. Live validity, units, packet identity and export remain unqualified; no new TX result |
| Host API one/four-reader overhead and basic thread invariants | Historical measurement; later S8 local profile passed | Earlier contention measurements covered 150,000 timed reads. The current S8 row above records the separate 300,000-call profile; neither run establishes a consumer SLA or synchronization accuracy |
| Shared cross-process clock identity | Open | Current SDK deliberately scopes identity to one clock instance in its owning process |
| Reset, suspend and roaming | Latest phase is preparation only | Separate cases and collector requirements are documented; prior single restart remains historical evidence |
| Calibrated/sub-millisecond synchronization | Equipment and semantics prerequisites unmet | No second controlled node or independent characterized reference; no qualified hardware/host conversion yet |
| Hosted CI | Recorded published snapshot passed; corrected-head checks tracked on PR #3 | Snapshot runs and immutable base/head are recorded above; historical runs do not validate later changes |

Published scan/tooling revision `fdcc22f80ad173a2f4f2844c0f6b666794fda54a`
passed [hosted CI](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37121148165).
The later timing-boundary package passed 149 local tests with owned fixtures
(146 plus three skips without them). Its own publication/CI must be checked
separately; neither CI nor those offline tests qualifies hardware.

## Downstream rules supported by the new result

- Do not infer a private capture action from a changed SoC value. Scan-associated
  reports changed it without a private TSF request from the harness.
- Do not treat a successful private getter as owning the next report merely by
  sequence. Ordinary scan activity introduces another operational context.
- Preserve observation origin as unknown or diagnostic when association is not
  established. The existing private evidence contract is not silently widened to
  admit unassigned reports; raw diagnostics are not clock-conversion inputs.
- Do not mark the failed scan profile passing by retrospectively increasing its
  deadline. The six-second measurement is evidence for designing a future profile.
- Keep QPC application reads independent of scan completion, ETW delivery and
  hardware requests. Measured call latency is not a synchronization-error bound.

## Work that current equipment cannot establish

Sub-millisecond accuracy needs both a qualified time-transfer/acquisition path
and comparison against a second controlled node or a characterized independent
reference. A rough AP distance estimate, synthetic offset estimator, local QPC
benchmark or additional same-machine TSF reads cannot substitute for that test.

The next hardware-interface work should target a narrow, reviewable producer-to-
userspace return path with explicit record completion and clock identity. A driver
change or firmware cooperation would be a separate engineering project; the
existing dump paths are not a safe polling API and no blind register or kernel
memory access is justified by these findings.

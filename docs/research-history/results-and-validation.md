# Results, failures and validation boundaries

The useful result is conditional station-TSF/QPC timing from retained diagnostic observations, including one live persistent-session smoke. This page puts the successes, failed attempts and revised results beside their evidence limits. It does not turn software tests, replay or narrow live controls into calibrated physical timing.

[Guide](README.md) · [Timeline](timeline.md) · [Hypotheses](hypotheses-and-lessons.md) · [Next steps](next-steps.md)

## Current corrected results

The authoritative retained-data comparison is [postmerge-corrections-2026-10-08.json](../overview/postmerge-corrections-2026-10-08.json), corrected source `0f41db0175e3601e899c51143b46bb8b3df02135`. It records unchanged input hashes, `qualification: conditional-research` and `physical_bound_proven: false`. The table below reads its **corrected** fields, not the original smoke or component-PR numbers.

| Measure | Idle hour | Loaded hour | Persistent idle smoke |
|---|---:|---:|---:|
| Requests | 1,277 | 1,212 | 139 |
| Offline-screened samples | 1,276 | 1,210 | 138 |
| Rejected samples, all late reports | 1 | 2 | 1 |
| Foreign report groups | 6 | 4 | 2 |
| Declared replay duration, rounded seconds | 3,602.426 | 3,601.487 | 302.999 |
| **Tracking coverage, integer-estimate uncertainty below 1 ms** | **78.632051%** | **72.349583%** | **92.862589%** |
| Maximum uncertainty immediately before a subsequent sample, us | 1,979.211 | 1,732.143 | 1,349.309 |
| Settled points / declared one-second event grid | 3,598 / 3,598 | 3,597 / 3,597 | 297 / 297 |
| Conditional settled half-width, median / maximum, us | 308.456 / 894.669 | 324.908 / 766.954 | 280.429 / 614.883 |
| Settlement wait, median / maximum, seconds | 3.112 / 8.029 | 3.347 / 7.823 | 2.341 / 4.989 |
| Affine estimate available / settled points | 3,595 / 3,598 | 3,595 / 3,597 | 295 / 297 |
| Nominal SoC/QPC-domain compatible | No | No | No |

The causal maximum row is a sampled boundary metric immediately before a later sample, not a whole-run/tail supremum or universal worst case. Settled values are interval **half-widths**, not full widths, observed absolute errors or confidence intervals. The integer point estimate's conservative uncertainty additionally includes 0.5 us of rounding allowance. Fractions in the source JSON retain precision; displayed numbers are rounded.

All 7,492 declared grid points settled below 1 ms in conditional rate-only half-width. That is a finite replay result. It does not say every possible event always settles, that a current application receives results at these times, or that station/AP error is below those bounds.

**Conditions:** capture inside the stated host window; a TSF rate within ±200 ppm of nominal relative to QPC at every instant; no unmodelled phase step within the epoch; integer-bin widening. The affine estimate adds constant rate over a surrounding 60-second span and has its own availability subset. AP-referenced use adds a station/AP relationship that was not independently measured. Full-recording sample screening was offline; the model's causal use of accepted inputs does not qualify online admission. See [mathematics](../clock-models/tsf-mathematics.md).

## Why older numbers differ

The inputs were retained, while code and interpretation changed. These are separate analysis versions, not new acquisitions or evidence that the hardware became more accurate.

| Version / source | Idle tracking | Load tracking | Smoke tracking | What changed |
|---|---:|---:|---:|---|
| Original integrated baseline `02459e7` | 78.690368073% | 72.417402177% | 92.884040848% | Original component policies; preserved in historical outputs |
| Reviewed source `498758f` | 78.632051394% | 72.349582965% | 92.862588662% | Included 0.5-us integer rounding allowance in status/expiry; repaired stale-period and settlement rules |
| Post-merge source `0f41db0` | 78.632051394% | 72.349582965% | 92.862588662% | Arrival-order-v2, screen-v2 continuity, settlement-v2 overlap and quantized SoC checks; no new capture |

The [first comparison](../overview/pr-reconciliation-2026-10-08.json) records the first two rows. The [post-merge comparison](../overview/postmerge-corrections-2026-10-08.json) records the last transition. Loaded-hour median settlement half-width changed from 324.908 to 325.406 us when overlapping captures were excluded as bracket sides, then returned to 324.908 us when already-available overlaps were allowed to narrow a complete true-before/true-after bracket. Its actual settled-grid maximum remained 766.954 us in these comparisons. This is a policy distinction, not silent result replacement.

Earlier 99.440%/99.223% causal coverage used a boundary one tick after ETW logging and a different review interval. It omitted the roughly two-second reader delivery delay incorporated by arrival-aware replay. It is not current application coverage. Similarly, retrospective consecutive-pair maxima of 894.669/785.584 us differ from actual settled-grid maxima; the loaded 785.584-us figure is not an erroneous spelling of 766.954 us.

The original affine campaign medians/maxima—134.8/352.2 us idle and 139.6/190.8 us loaded—remain valid as that report's conditional constant-rate model result. They are neither physical error measurements nor the weaker rate-only model. [Original campaign](../acquisition/tsf-host-bound-results.md), [current causal explanation](../clock-models/causal-provider-replay.md), [current settlement explanation](../clock-models/settled-timestamps.md).

## What succeeded, and what each success means

| Work | Evidence | Supported conclusion | Not established |
|---|---|---|---|
| Initial guarded acquisition | 12 captures / 138 requests; 14 trace cleanups; retained run receipts | The declared idle/workload profile collected diagnostics and shut down | Universal request ownership or physical sampling semantics |
| FTM operations and aggregation analysis | Six same-target operations with successful completions; selected aggregation model matches saved callbacks | Working ranging diagnostics and specific signed-difference/selection behavior | Absolute four-event offset inputs or calibrated variance |
| Standard API investigation | Python/native queries and NDIS path investigation | Exact observed errors and host/driver path limits | A conclusion that hardware support is absent |
| Source/byte ownership research | Static traces, strict decoders, native synthetic exporters and broker tests | Concrete copy, reduction, ownership and rejection contracts | A live original firmware timing source |
| Eight-byte device-service control | One exact operation returned the expected literal through the installed driver | That driver-to-application return works | Other selectors, radio timestamps or firmware-event integration |
| Counted bound campaign | Hour idle and hour load passed predeclared **conditional** criteria | Useful station-TSF/QPC window-model result under stated assumptions | Physical capture bound, AP offset or continuous immediate accuracy |
| Persistent acquisition | 139/139 pending-to-success requests, one closed session, unchanged final identity | Normal persistent operation on the exact tested build | Persistent hour/load, cancellation, stuck-I/O recovery or firmware drain |
| Reviewed replay and versioned publication | Same hashed inputs; corrected code/policies; generated summary blocks | Reproducible software interpretations and explicit numerical changes | New live measurements or external calibration |
| Research packaging and CI | Public scripts/docs, private evidence boundary, source catalogue, diagrams, exact-main hosted checks | Reviewable and reproducible public software checks | Private fixture completeness or production clock readiness |

Sources: [historical validation](../overview/validation.md), [acquisition report](../acquisition/acquisition-campaign-2026-10-02-results.md), [FTM provenance](../ftm/ftm-result-provenance.md), [positive control](../evidence/device-service-positive-control.md), [smoke](../acquisition/persistent-tsf-smoke-2026-10-08.md), [review corrections](../overview/postmerge-corrections-2026-10-08.md), [hosted status](publication-status.md).

## Related downstream work, with its original evidence scope

The research also supplied contracts and review evidence to related repositories. These are accomplishments reported by their original coordinating tracks, not fresh downstream execution by this documentation task.

| Work | Reported result | Limit and source |
|---|---|---|
| Diagnostic observation consumer | Five pinned replay profiles, immutable observations, explicit source/digest selection and CLI; 15 focused tests and a later 64-test downstream suite | Software/replay only; the [October 6 ledger](../overview/gap-closure-ledger.md#historical-complete-event-track-snapshot-2026-10-06) retains local/publication scope |
| Host-only API acceptance | 12 runs / 300,000 record calls met declared per-reader and pooled p99 rules; unchanged evidence requalified after verifier fixes | Four calls exceeded 1 ms, maximum 2.5444 ms; no worst-case latency, radio-clock accuracy or consumer SLA claim; [same ledger](../overview/gap-closure-ledger.md) |
| Corrected consumer model port | 103 tests and exact golden-v3 parity reported after post-merge fixes; older v1/v2 fixtures preserved | Model parity and software behavior, not live radio admission or calibration; [post-merge report](../overview/postmerge-corrections-2026-10-08.md#validation-and-remaining-gates) |
| Spectral work preservation | A nine-file local patch, exact hashes and 43 tests reported by its coordinator | Separate repository and scope; no spectral command/capture or new publication implied; [October 6 ledger](../overview/gap-closure-ledger.md) |

## Failed or stopped experiments remain part of the record

| Experiment / attempt | Outcome | What was learned / changed |
|---|---|---|
| Standard timestamp capability queries | `23 / ERROR_CRC`, no valid capability/tuple | Capability unknown; pursue exact-path evidence without treating failure as unsupported hardware |
| Corrected-observer private repeat | Stopped on unmatched reports; quarantine retained | Tighten association and preserve foreign/rejected groups |
| Three controlled scans | All failed four-second completion criterion | Final tail showed about six-second completion; do not retrospectively pass the old profile |
| Bound idle attempt `00e0aa837bfa` | Trace cap at about 25 minutes | Increase declared storage allowance for subsequent runs |
| Load attempt `90590c08b728` | 425 lost events; HTTP 403 meant no intended network load | Fix workload evidence and buffering; do not label CPU-only as the load profile |
| Load attempt `948352ab3bd5` | 1,000-MiB cap after about 10 minutes | Large buffers inflated file growth; return to smaller buffers with more of them |
| Load attempt `a62689850d11` | 1,000-MiB cap after about 39 minutes | Real network-load volume required a larger declared cap |
| Load attempt `1a8a567bce2c` | Ambiguous/missing matching cache entry | Skip that coarse beacon check if association remains unchanged; preserve its missing-evidence count |
| 100-us campaign stretch objective | Not achieved | Do not replace the achieved conditional range with the desired target |

The [bound report](../acquisition/tsf-host-bound-results.md#all-attempts-including-stopped-runs) records eight attempts: one short smoke, five stopped long-run attempts and two counted completed hours. Stopped-run analyses are diagnostic context, excluded from the verdict. The original strict quarantine, later bound profile and persistent smoke are different scopes. Successful later work does not silently clear the earlier disposition.

## What this review did and did not revalidate

This documentation review checked source history, public result JSON, reported metrics, local document provenance, navigation, generated summaries and offline software checks. The [validation receipt](documentation-review-2026-10-09.md) records fresh commands/results. It did not rerun private capture analysis, vendor tracing, real acquisition, downstream qualification or independent timing measurement. Those historical results remain linked to their original evidence and source versions.

Public-only reproduction can validate the software suite and documentation. Reproducing retained-run metrics requires the authorized private inputs named and hashed by the original reports. A digest identifies an input; it does not make unavailable data independently reproducible.

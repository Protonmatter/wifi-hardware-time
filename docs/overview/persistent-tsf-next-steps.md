# Persistent TSF: research, implementation and testing roadmap

The persistent sampler has passed offline adversarial tests and one five-minute idle live smoke run. The immediate objective is to turn that bounded result into a qualified TSF-referenced timestamp service with explicit uncertainty and failure states. This roadmap separates research questions, implementation changes and the evidence needed to close each gate. It is not authorization for a live experiment, a lifecycle disruption or a merge.

## Current position

<!-- tsf-headlines:smoke -->
**Current retained smoke analysis:** 139 recorded requests, 138 offline-screened samples; **92.862589%** tracking coverage under the conditional integer-estimate uncertainty threshold. **297/297** event-grid points settled, with median/max rate-only half-widths of 280.429/614.883 us and median wait 2.341 s. [Versioned results and source pins](postmerge-corrections-2026-10-08.json). This is offline-screened replay of the retained capture, not online admission or calibrated AP/UTC accuracy.
<!-- /tsf-headlines:smoke -->

| Area | Established | Still open |
|---|---|---|
| Persistent acquisition | 139 real pending-to-success requests, one closed session, no trace loss or forced termination | Long-run/load behavior and real failure-path recovery |
| Screening | 138 accepted samples, one late report, foreign groups retained | Causal online admission and stronger physical attribution |
| Immediate time | Versioned conditional tracking coverage in the generated summary above | Continuous availability and application-observed end-to-end latency |
| Settled time | Versioned settled-grid counts and half-widths in the generated summary above | Live API integration, longer-gap behavior and physical validation |
| Mathematics | Exact fraction-based bounded-rate and separately labeled affine models | Any optimized clipping, new settlement policy or qualified wander model |
| External accuracy | Coarse beacon consistency, zero violations in checked smoke observations | Independent station/AP, multi-node and UTC/reference validation |

Read the [measured results](../acquisition/persistent-tsf-smoke-2026-10-08.md), [sampler contract](../acquisition/persistent-tsf-sampler.md) and [mathematics](../clock-models/tsf-mathematics.md) before reusing the numbers. The baseline stack consists of the bound campaign, causal provider and settlement changes; publication of this branch is not a merge or a production release.

## 1. Preserve the measured baseline

**Implementation:** keep persistent mode optional, legacy defaults unchanged, report wait enabled, raw receipts immutable and request/session lifecycles distinct. Keep the exact driver/profile validation and adapter-scoped lock/unfinished-run protection.

**Testing:** use the existing full offline suite, targeted pending/cancel/ownership cases, Windows mutex/file-sharing tests, CLI parser tests, schema failures, syntax checks and generated-document checks. Existing tests must reject stale permits, unknown schemas, impossible initial/final I/O transitions, premature release and fabricated clean closure. Source hashes and live evidence must identify the bytes that actually ran.

**Completion evidence:** recorded commands with exit codes and skips, reviewed diff, hosted checks for the published commit, and unchanged audited probe/mathematical references. Hosted software checks do not validate live capture.

## 2. Qualify acquisition across time and load

**Research:** characterize accepted-sample gaps and record-delivery tails under the existing idle and CPU/network load profiles. Determine which delays are ETW batching, controller work, admission IPC or kernel completion observation.

**Implementation:** add only necessary stage instrumentation, retaining original timestamps and actual elapsed denominators. Any new availability boundary must be versioned. Do not subtract identity checks or processing from achieved gaps.

**Testing:** after explicit authorization, run separately identified hour-long idle and load campaigns with the qualified exact build, unchanged report wait and reviewed request budget. Preserve all attempts, including stopped runs, losses, beacon gaps and tail periods. Use existing predeclared campaign acceptance checks; if the acceptance profile changes, declare and version it before collecting data.

**Completion evidence:** clean controller/sampler/observer lifecycles, actual request and trace spans, input hashes, loss accounting, accepted/rejected groups, gap distributions, acquiring/tracking/stale/invalid durations and settle-wait distributions. Compare like-for-like runs before attributing a change to an optimization.

## 3. Establish live failure and continuity behavior

**Research:** distinguish kernel I/O completion from firmware/report drain. Identify what proves that the next experiment can start after owner loss, cancellation, device change or an unresolved operation.

**Implementation:** maintain sticky failure, no future permits and retained buffers/event/device while completion is unresolved. Keep durable quarantine and unfinished-run evidence; a new directory, restart or quiet window is not reconciliation. Propagate epoch/identity invalidation into consumers once online integration exists.

**Testing:** first extend deterministic offline scenarios if needed. Deliberate live controller-loss, cancellation, timeout, disconnect, sleep, roam or reset tests require separately reviewed profiles and applicable authorization. Start with the least disruptive bounded case, one variable at a time. Do not kill a pending sampler for a convenience deadline.

**Completion evidence:** original failure, cancellation result, actual terminal completion or explicit unresolved retention, resource ownership, process identity, observer tail, adapter continuity and the decision that allows or prohibits re-admission. The successful smoke's normal shutdown does not close this gate.

## 4. Separate report delivery from request scheduling only after research

**Research:** determine a safe firmware/report boundary for issuing the next action-4 request while earlier diagnostic records may still be in delivery. Establish association behavior for delayed, reordered, duplicate, missing and foreign reports. One outstanding kernel request alone is not a firmware exclusion contract.

**Implementation:** only after that contract is supported, introduce an explicit optional mode with bounded queues, sequence/session linkage, overflow handling and unchanged raw timestamp semantics. Preserve the current coupled mode as a baseline. Avoid autonomous queued future permits and catch-up bursts.

**Testing:** deterministic association/ordering/loss tests before any live experiment, then a separately authorized bounded campaign comparing matched conditions. Rejected and missing reports must never be silently replaced by nearby foreign reports. Measure actual accepted-sample gaps and reader/API availability.

**Completion evidence:** source/lifecycle justification plus measured attribution, loss, continuity, ownership and coverage. Neither a short IOCTL nor a predicted one-second schedule establishes safety or 99% coverage.

## 5. Implement causal online admission and the consumer boundary

**Research:** specify what each admission decision knows at that time. Identify any current offline screen rule that depends on later requests or later records; an earlier decision must not be silently revised as if it had been known then.

**Implementation:** a distinct online admission state machine owns association, event completeness, deadlines, duplicates, foreign traffic, freshness and epoch changes. The numerical provider checks feasibility but cannot establish acquisition provenance. Feed accepted samples to the maintained `userspace-clock` API only through this gate; the sampler itself must not call `WifiTsfClock.ingest()` directly.

The application contract preserves raw event QPC and its epoch, an immutable provisional result and a separately derived settled record. Report `pending`, `stale`, `invalid` or unavailable honestly. The `tracking` state uses exact half-width plus the conservative 0.5-us rounding allowance. Consumers must distinguish that exact quantity from outward-rounded whole-microsecond display values; downstream records expose `uncertainty_exact_us`.

**Testing:** feed event prefixes and assert decisions never inspect future suffixes. Test out-of-order delivery, missing group tails, duplicate sequence/session IDs, queue overflow, incompatible samples, initial acquisition, exact threshold equality, integer rounding, stale holdover and epoch changes. Differential replay may compare policies, but offline hindsight is not the oracle for an earlier online decision.

**Completion evidence:** versioned admission and timestamp contracts, executed prefix/failure tests, actual application availability latency, immutable raw/provisional records and explicit settlement policy. Research stays here; maintained consumer implementation remains a separate repository change.

## 6. Change mathematics only through a separately verified contract

| Candidate | Required evidence before replacement |
|---|---|
| Exact polygon clipping optimization | Exact equivalence to the current fraction-based vertex reference on feasible, empty, degenerate and adversarial rational cases; reproducible timings and outputs |
| All-sample or revised settlement policy | Versioned semantics, availability-order invariants, no future-information leakage, preservation of already issued results, oracle/reference comparisons |
| Bounded-wander model | Defined parameter with independent supporting data, its valid conditions and failure behavior; no parameter inferred merely to obtain narrower intervals |
| Threshold/rounding contract | Tests at exact boundary and adjacent rational values, with separate interval half-width and rounded-estimate uncertainty |

Retain the rate-only result and separately label any constant-rate affine estimate. Keep exact arithmetic until display. Do not narrow the 200-ppm prior or acceptance thresholds to improve a chart without independent evidence and a versioned policy. Earlier unsupported synthetic-test counts and the median-derived 740-us worst-case claim remain withdrawn; new claims require executable commands and retained outputs.

## 7. Validate physical and shared time

**Research:** establish the actual capture event and an independent host relationship, then quantify station-to-AP offset/continuity if AP-referenced time is the objective. For multiple devices, construct the combined error budget rather than assuming individual sub-millisecond bounds imply pairwise sub-millisecond alignment. UTC needs an explicit external-reference chain.

**Implementation:** retain source/clock identity, calibration or qualification version, epoch and validity with each result. Keep unsupported capabilities disabled. A systematic capture bias can remain numerically consistent and must not be hidden by a good fit.

**Testing:** compare against an independent, qualified reference or controlled observation path with a documented uncertainty budget. Repeat across relevant load, power, association and device/build conditions. Validate event-detection latency separately if application events originate in a sensor, packet or another device.

**Completion evidence:** attributable event/clock provenance, reference uncertainty, measured residuals and bounds, tail/failure behavior and a claim limited to the tested conditions. Until then, retain `conditional-research` and `physical_bound_proven: false`.

## 8. Review, publication and merge

Keep code and results reviewable on the sampler branch. Resolve substantive review findings with reproductions and tests. Recheck the dependency stack, exact remote head, visibility and hosted checks. Commit, push, PR creation/update, merge and release are distinct actions governed by the user's authorization. A green software workflow is not a hardware qualification or an instruction to merge.

The next technical step is the unchanged-profile longer-run/load qualification, alongside the source/association research needed before decoupling. Preserve the two-phase timestamp design as the leading application path while those gates remain open.

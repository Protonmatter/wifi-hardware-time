# Research-to-Userspace-Clock Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to execute the bounded work packages below. This document is a research and adoption roadmap, not authorization to execute disruptive experiments, publish changes, install services, or adjust clocks. Use checkbox steps to track evidence and deliverables.

**Goal:** Turn reproducible Wi-Fi timing findings into useful, independently qualified capabilities in `userspace-clock`, while maximizing information gained from each experiment.

**Architecture:** `wifi-hardware-time` owns exploratory probes, exact-build qualification, evidence and falsifiable hypotheses. `userspace-clock` owns maintained APIs, providers, correlation models, client examples and operational behavior. Versioned, sanitized evidence packages connect the repositories; the runtime does not depend on the research checkout.

**Tech Stack:** Existing research Python 3.11+, Windows PowerShell 5.1-compatible wrappers, native Windows ARM64 C and offline ETW analysis. The downstream reference SDK now uses Python 3.11+ and direct Windows QPC, with a pure conditional estimator. IPC, native ABI, hardware integration and system discipline remain future work.

**Spec:** [Research API direction](../../api-direction.md), [validation ledger](../../validation.md), [new result provenance](../../ftm-result-provenance.md), and downstream [requirements](https://github.com/Protonmatter/userspace-clock/blob/1abc438be29b25eda9e831b50591023b995e598d/docs/REQUIREMENTS.md).

## Baseline and boundaries

Research HEAD inspected: `8bd9051510cacc1b0bac805bf57d55e6605a12ff`.
Downstream HEAD inspected: `1abc438be29b25eda9e831b50591023b995e598d`.
At planning time, the FTM aggregation model, provenance report and variance-semantics flag were uncommitted working-tree findings. They are not contents of `8bd9051`; downstream must pin their actual publication revision. The subsequent offline implementation and live campaign are tracked in the execution status below. The host-only reference SDK and pure conditional estimator are now implemented. Current qualification is tracked in the execution status below and the [gap ledger](../../qualification/gap-closure-ledger.md); original checklist items remain the historical work-package specification.

## Global constraints

- Application-neutral consumers: OMS/event processing, telemetry, scientific measurement and wireless analysis are examples, not dependencies.
- Separate measurement, node synchronization and system discipline; distinguish implemented, available, enabled and qualified for each capability.
- Preserve raw ticks, declared units, source identity, clock domain, acquisition status and epoch. Keep QPC, TSF, network time and UTC distinct.
- Preserve host observation windows; neither report arrival nor IOCTL completion is a firmware sampling instant. Unknown accuracy/uncertainty remains null.
- Reject stale, incomplete, ambiguous, mixed-build and mixed-epoch evidence. Residuals and representation resolution are not accuracy bounds.
- Fast application timestamp reads do not open the private device or wait for ETW/firmware. Measurement clients need no clock-setting privilege.
- Retain exact-build guards and nonzero FTM measurement checks. Raw FTM variance is not a qualified uncertainty input.
- No new dependency, network listener, service installation, profile modification, register operation or clock write is implied by approving a plan.
- Raw traces, proprietary files and endpoint identifiers remain private. Any exported numeric fixtures require explicit sanitization review.
- Commits and pushes require the user's publication instruction; no automatic merge or history rewrite.

## Review focus

1. A delayed report after timeout must not become the next request's measurement: R2 and D2 test timeout/quarantine, duplicates and late delivery.
2. Adapter identity can remain constant across a clock discontinuity: R3 and D1/D2 test restart, reassociation, suspend, counter regression and reconnect.
3. A clean affine fit can hide a constant sampling bias: R2 and D2 test injected bias and keep external uncertainty null.
4. Nearby timestamps from different nodes do not establish event order: D1/D3 return indeterminate ordering when domains or uncertainty do not support comparison.
5. Process/service loss can leave a client with a plausible old model: D2 tests model expiry, provider restart and immutable snapshot publication.

## Priorities: information gained and practical contribution

| Priority | Research question | Downstream value | Evidence needed before promotion |
|---|---|---|---|
| First | Can we identify and reject every unusable observation? | Safe ingestion and reproducible support diagnostics | Versioned fixtures, exact-build receipts, negative tests |
| First | What useful event timing is independent of Wi-Fi? | Immediately useful application API | Host provider semantics, concurrency and process-lifecycle tests |
| First | How do TSF reports age, arrive late and cross epochs? | Experimental provider, correct freshness and invalidation | Replay plus bounded live sampling, lifecycle matrix |
| Next | Does TSF add information beyond QPC and cached beacon timestamps? | Justified correlation feature and power/performance tradeoff | Held-out predictive evaluation and controlled baselines |
| Next | Can two nodes share a qualified reference relation? | Multi-node logical-clock capability | Two-node measurements, delay/asymmetry tests, reference evidence |
| Conditional | Can Linux expose better sampling/packet semantics? | A stronger portable hardware provider | Physical AXML node and descriptor/reference-point qualification |
| Conditional | Can FTM diagnostics explain biased/empty results? | Better result validation and capability reporting | Aggregation replay, controlled responder and independent measurements |
| Later | Can a qualified external source drive OS time safely? | Independent system-discipline capability | Reference epoch/uncertainty, authority and rollback qualification |
| Low until justified | Can arbitrary registers be read? | Only a specifically identified missing observation | Proven benign target, exact address-space mapping and return validity |

Do not spend the critical path searching arbitrary private commands. A register result or additional diagnostic string is useful only if it resolves a documented clock/API requirement.

## R1 — Reproducible evidence package and research contract

**Files:** create `docs/evidence-contract.md`, `tools/export_clock_evidence.py`, `tests/test_export_clock_evidence.py`, `fixtures/synthetic/clock-observations-v1.jsonl`; update `docs/validation.md`. Review existing uncommitted FTM additions before including them in a published baseline.

**Interfaces:** propose `normalize_run(run: Path) -> EvidenceBundle` and `export_sanitized(bundle: EvidenceBundle, output: Path) -> ExportReceipt`. Define both dataclasses in the exporter before callers use them. Output version 1 contains a manifest and observation JSONL; malformed or ambiguous input fails explicitly.

- [ ] Define the manifest: schema version, source commit plus dirty-patch hash if local, tool hashes, driver/DLL hashes, architecture, capture configuration, trace loss, start/end adapter state, review status and claim-specific evidence references.
- [ ] Define observations with opaque source/domain/epoch IDs, sequence, raw counter and width, unit provenance, host clock/frequency, request-start/completion/report times, association method, action and freshness semantics. Decimal-string encode large integers in JSON for lossless language-neutral interchange.
- [ ] Keep `sampling_interval` null unless causality and freshness establish it. Store host observation windows separately; do not put request/report bounds into a field promising a hardware sampling bound.
- [ ] Separate validity, experimental qualification, model residuals and external uncertainty. Include structured rejection reasons and source capability states.
- [ ] Write tests for missing/duplicate reports, mixed identities/builds, unsupported schema, trace loss, malformed numbers, clock regression and accidental identifier export; then implement the exporter.
- [ ] Export existing TSF/latch/FTM cases locally, review a sanitized fixture subset and verify identical normalized output across repeated runs. Include negative evidence and failed captures rather than selecting only successes.

**Gate/output:** a reviewed schema and deterministic fixture package with no raw binaries or machine identifiers. Tests: `python -m unittest discover -s tests -p test_export_clock_evidence.py -v`; then the full existing suite. Downstream can implement ingestion before a hardware source becomes production-qualified.

## D1 — Useful local clock and consumer contract

**Repository/files:** `userspace-clock`: create `docs/design/measurement-clock-v1.md`, `docs/contracts/clock-record-v1.md`, `docs/qualification/consumer-targets.md`, and `fixtures/clock-record-v1/`. Runtime source layout follows the approved language/transport design; do not freeze a public ABI in the research repo.

**Proposed logical operations:** `capabilities()`, `now(domain)`, `convert(timestamp, target_domain, epoch, model_version)`, `status(source)` and explicit event comparison. These describe behavior, not finalized language signatures. Conversion must return either a value with provenance or an explicit unavailable/stale/epoch-mismatch result.

- [ ] Select two generic scenarios: same-machine request lifecycle timing and cross-process event correlation. Add a synthetic OMS-style order lifecycle example without integrating Polaris internals or claiming compliance-grade audit timing.
- [ ] Specify timestamp location: event occurrence versus queue receipt versus log emission. Record event IDs and causal links separately from timestamp ordering.
- [ ] Define host monotonic timestamps as the default local domain; wall time is a separately labeled observation. QPC is independent of UTC, per [Microsoft's timing guidance](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps).
- [ ] Decide native/library fast reads versus local IPC for discovery/model delivery; benchmark a prototype before promising latency. Keep hardware collection out of `now()`.
- [ ] Set use-case acceptance targets for maximum added read latency, freshness, acceptable conversion error and outage behavior before qualification. Record these as consumer requirements, not measured guarantees.
- [ ] Approve representation, rounding, overflow handling, clock/boot identity, schema evolution and concurrency semantics. Test 64-bit counter transport, huge values, repeated ticks, restart and indeterminate comparisons.
- [ ] Implement the host-only vertical slice after design review, with at least two independent processes consuming consistent metadata and a reproducible latency benchmark reporting p50/p95/p99/max, sample count and load conditions.

**Gate/output:** a usable local event-timing API requiring no Wi-Fi, elevation or clock changes. No UTC accuracy or multi-node ordering guarantee. Specify exact build/test commands in the implementation plan after the runtime/toolchain decision; the reference SDK now exists; broader ABI and consumer acceptance qualification remain open.

## R2 — TSF acquisition semantics and host-correlation experiments

**Files:** create `experiments/qualcomm/analyze_observation_quality.py`, `tests/test_observation_quality.py`, `docs/qualification/qualcomm-observation-matrix.md`; extend the capture wrapper only where a missing datum is demonstrated. Preserve existing action allowlists and sample limits initially.

**Interface:** `analyze_quality(bundle: EvidenceBundle) -> QualityReport`; define `QualityReport` to contain counts, loss/ambiguity, latency distributions, per-epoch relative rate, prediction residuals and limitations. It must never create calibrated uncertainty from fit residuals.

- [ ] First replay all saved READ_VALUE/capture sequences. Separate action 3's cached SoC values from action 4's refresh behavior. Do not assume a constant TSF/SoC offset implies simultaneous latching.
- [ ] Test synthetic delayed reports, timeout followed by a new request, duplicates, missing trace groups, counter wrap, regressions and injected constant sampling bias. Without transaction IDs, quarantine ambiguous windows instead of assigning the closest timestamp.
- [ ] Resolve whether transport request/response identifiers or firmware definitions can establish stronger causal association. Record exact bytes/RVAs and counterexamples; transport acknowledgement alone is not a sampling fence.
- [ ] Run a first live pilot of three bounded captures per approved sequence using the current wrapper limits. Record actual cadence, QPC frequency, load/power/association context, trace loss and final driver state. Start at the already-tested request rate; increases require a separate load experiment.
- [ ] Compare idle and representative user workload only after baseline cleanup succeeds. Stop on driver mismatch, unexpected state transition, unexplained timeout, loss or inability to stop the trace. Recheck interface state after every run.
- [ ] Fit centered relative-rate models within epochs; evaluate on later held-out samples and whole held-out runs. Compare with a simple last-observation/baseline model. Report residual percentiles, maximum error, observation age and coverage without treating the report timestamp as ground truth.
- [ ] Determine whether TSF materially improves the named consumer requirement. If host QPC alone meets it and the hardware model adds no demonstrable value, retain TSF as optional observation metadata.

**Gate/output:** defensible experimental observation semantics and a rejection policy. Hardware-to-host conversion remains labeled experimental when sampling bias is unknown. Exact sampling is promoted only by authoritative firmware semantics or independently validated instrumentation, not by additional repetitions.

**Existing commands:** `python experiments/qualcomm/analyze_latch.py <saved-run>` and `python tools/analyze_tsf_series.py <saved-run>`; new quality tests use `python -m unittest discover -s tests -p test_observation_quality.py -v`. Live commands and limits remain those in [operations](../../OPERATIONS.md) and [experiments](../../experiments.md).

## R3 — Epoch, loss and recovery qualification

**Files:** create `docs/qualification/lifecycle-matrix.md`, `fixtures/synthetic/lifecycle-v1.jsonl`, `tests/test_lifecycle_evidence.py`; reusable live harnesses only after each operation has an exact target and recovery procedure.

- [ ] Model provider start/stop, client disconnect, trace loss, late reports, interface disconnect/reconnect, reassociation, adapter restart, suspend/resume and driver-build change as distinct events. A process restart need not prove a hardware reset, but it invalidates unverified correlation state.
- [ ] Define explicit transitions: unavailable → acquiring → usable-experimental/qualified; any unknown continuity or expired model → stale/invalid. Require fresh evidence before returning to usable.
- [ ] Test synthetic lifecycle sequences first, including counters that appear continuous across a real interruption. Never infer continuity solely from increasing endpoints.
- [ ] Repeat disconnect/restart and suspend/resume only with local console access, a saved-profile recovery method, precise adapter identity and separate approval for the disruptive phase. Keep the previous successful single restart as evidence for that one run.
- [ ] Test roaming only with a known second controlled AP and documented target topology. Test cancellation during reset only on dedicated test hardware after ordinary lifecycle recovery works.
- [ ] Record interruption duration, cleanup success, model invalidation, fresh-sample recovery and preserved driver/profile state. Distinguish logical adapter restart from a firmware reset or physical power cycle.

**Gate/output:** a provider lifecycle contract with qualified and untested transitions enumerated. Downstream expires mappings conservatively even when full live lifecycle testing is unavailable.

## D2 — Experimental hardware provider and replayable correlation

**Repository/files:** `userspace-clock`: create `docs/design/provider-lifecycle-v1.md`, `docs/design/correlation-v1.md`, `docs/qualification/qualcomm-windows.md`; import reviewed R1 fixture packages by version and digest, not via a filesystem link to research source.

- [ ] Implement replay ingestion and rejection behavior before privileged live collection. Version provider qualification separately from the consumer API.
- [ ] Specify an observation-only Qualcomm mode that exposes raw observations and status. Enable estimated conversions separately only after R2 semantics and consumer requirements have been reviewed.
- [ ] Keep collection in an explicitly launched privileged process when necessary; clients remain unprivileged. Decide IPC authorization, bounded buffers, single-writer ownership, crash recovery and shutdown before making collection resident. No service installation in the first prototype.
- [ ] Define immutable model snapshots with source/target domain and epochs, model version, validity range, sample age, raw evidence reference, residual metrics and independently qualified uncertainty or null.
- [ ] Use integer/rational counter scaling or explicitly tested centered numerical arithmetic. Test near-wrap/large counters, negative deltas, outliers, gaps, duplicate inputs and extrapolation expiry; no fit may bridge an invalidated epoch.
- [ ] Ensure a dead collector or stale model cannot silently keep producing apparently current hardware time. Return host time only as an explicitly labeled fallback domain.
- [ ] Run a non-elevated consumer and qualified collector end-to-end, then terminate/restart the collector and demonstrate prompt invalidation and recovery. Benchmark collection overhead separately from timestamp-read latency.

**Gate/output:** usable host timestamps plus an honest experimental hardware-observation capability. No requirement to claim accurate TSF-to-QPC conversion to ship the host API.

## R4 — Targeted deeper investigations, run when they unblock a consumer

| Track | Concrete next experiment | Stop/promotion criterion | Downstream contribution |
|---|---|---|---|
| FTM | Extend saved-result replay to all available nonempty/empty/canceled records; trace firmware sample insertion and pre-filter arrays; identify per-exchange timestamps and units if actually exposed | Aggregate RTT alone cannot supply clock offset; do not enable clock synchronization from it. Controlled distance and responder evidence required for ranging claims | Completeness checks, diagnostic quality flags, reusable negative fixtures |
| Standard Windows timestamps | Trace return-code provenance for the existing error-23 query; compare with a known-capable NIC using documented APIs and exact SDK layouts | Successful documented tuple plus declared semantics needed; absence of strings/imports remains inconclusive | A separate standard cross-timestamp provider if qualified |
| Cached beacons | Compare cached AP timestamp/host receive metadata age against fresh observations without initiating scans | AP identity, freshness and host timestamp semantics must be known; cache timestamp does not prove local TSF sampling | Optional AP-domain observations; possible two-node research input |
| Linux AXML | Inventory physical adapter/kernel/firmware; add a serialized, status-returning TSF snapshot and qualify RX descriptor epochs, wraps and aggregation; examine TX completion association later | Need live hardware evidence; named TX descriptor fields alone do not qualify packet timestamps | Source-accessible provider and portable observation fixtures |
| Registers | Trace exact Windows memory-type/address map, result-buffer validity and documented side effects for one candidate needed by a stated requirement | No verified benign target means no live read; successful IOCTL alone is insufficient | Only the specific qualified read, never an arbitrary register API |

Linux PHC/socket-timestamp work follows counter/reference-point qualification. Do not advertise adjustable clock operations the hardware backend cannot implement. Windows AXML testing needs a supported host architecture; the inspected installer does not provide an ARM64 driver.

## R5 / D3 — Two-node logical synchronization

**Prerequisites:** two controlled nodes, identified topology, explicit peers, a test plan for asymmetric paths, and a consumer error target. A common SSID or increasing TSF does not establish a common clock domain.

**Files:** research `docs/qualification/two-node-plan.md`, `tools/analyze_two_node.py`, `tests/test_two_node.py`; downstream `docs/design/node-synchronization-v1.md`, `docs/qualification/node-synchronization.md`.

- [ ] Begin with recorded/synthetic exchanges and a software-timestamp baseline. Specify clock domains, message identifiers, four-event timing where applicable, authentication/replay protection and bounded network behavior before a listener is implemented.
- [ ] Separate offset, rate, transport delay and asymmetry assumptions. Shared AP timing and FTM are candidate observations only; neither removes unknown one-way delay by itself.
- [ ] Test dropped/reordered/duplicated packets, deliberate path asymmetry, reference changes, peer restart, stale mapping and partition/rejoin. Preserve causal message order separately from time estimates.
- [ ] Run both nodes against an independent common reference to measure actual offset/error when available. Without it, report internal consistency and estimated offset, not absolute synchronization accuracy.
- [ ] Implement a logical reference domain without OS clock writes; publish validity/uncertainty and return indeterminate event ordering where evidence is insufficient.

**Gate/output:** independently enabled node correlation with an explicit tested envelope. Simulation passes do not qualify network behavior; an independent reference is required for calibrated error claims.

## R6 / D4 — Reference qualification and system-clock discipline

**Prerequisites:** independent reference with known epoch and measurement uncertainty, documented connection/timestamp path, test host, and an approved OS clock ownership/rollback policy. No such reference is currently available; the rough AP-distance estimate is not one.

**Files:** research `docs/qualification/reference-method.md`; downstream `docs/design/system-discipline-v1.md`, `docs/operations/system-discipline.md`, `docs/qualification/system-discipline.md`.

- [ ] Select reference classes against the required error budget: qualified hardware-timestamped PTP or GNSS/PPS with a characterized delivery path. A generic USB receiver or unsynchronized host clock is not automatically an independent precision reference.
- [ ] Establish traceability, offset versus frequency-error metrics, sample size, environmental conditions, holdout runs and the combined uncertainty budget. Do not fit a correction to guessed AP distance.
- [ ] Evaluate supported OS time integration and current time-service ownership. On Windows, review the [time-provider interface](https://learn.microsoft.com/en-us/windows/win32/sysinfo/creating-a-time-provider) before choosing an implementation.
- [ ] Build dry-run correction proposals first. Test wrong epoch, stale reference, drift, steps, leap/time-scale handling, correction limits, loss of privilege, service conflict and restart persistence.
- [ ] After explicit live-clock approval, exercise bounded corrections on a test system and prove rollback/ownership restoration and reference-loss behavior. Measurement-only clients remain isolated from clock-setting authority.

**Gate/output:** a third separately enabled capability. Raw TSF, FTM RTT, a low residual, or a successful local-clock API cannot qualify it.

## Promotion packet: what crosses repository boundaries

Each accepted finding supplies: immutable research revision, source/driver identities, manifest and fixture digests, precise claim and non-claim, acquisition semantics, known invalidation events, negative cases, validation commands, live qualification scope and review disposition. Link upstream evidence; downstream owns its implementation and tests.

Downstream adoption requires a contract test demonstrating both the supported behavior and at least one rejection/fallback case. Track a research finding ID and provider qualification version in release notes. A new driver hash defaults to unsupported for the private provider; a research update does not silently widen the allowlist.

Publication order when authorized: publish the reviewed research evidence/contract first, obtain its real commit SHA, then update downstream `docs/RESEARCH_BASELINE.md` and qualification records to that SHA. Keep PRs small and independently reviewable. Do not copy the experimental PowerShell harness wholesale into a production service.

## Execution order and decision gates

1. **Qualcomm first: R2/R3 live-acquisition readiness and bounded qualification.** The offline R1/D2a foundation exists. Validate the installed FastConnect 7800 as the first hardware target: identity/build, repeated acquisition, report association, freshness, workload behavior and lifecycle invalidation. A successful private command or final Up state alone does not qualify a provider.
2. **D1 design and implementation informed by those findings:** finalize the application contract and host-only timestamp path. Host monotonic timing remains useful independently, but it must not substitute for Qualcomm qualification or imply hardware conversion support.
3. **D2 hardware integration only after the Qualcomm gate:** promote the individually established observation capabilities; retain experimental or unavailable status for sampling/cross-timestamp conversions that remain unresolved.
4. **R4 comparison and portability:** use a known-capable NIC to diagnose the standard Windows path if one is available; qualify Linux AXML as the next hardware backend. Neither is a prerequisite for beginning the current Qualcomm campaign.
5. **R5/D3:** two-node logical correlation after the extra node/topology exists.
6. **R6/D4:** independent-reference qualification and dry-run discipline, then separately approved live clock control.

Work packages may overlap in engineering time, but do not require subagents or simultaneous live experiments. No schedule or precision target is promised before the relevant hardware, workload and acceptance requirements exist.

**Completion of this roadmap's first useful milestone:** two generic applications can timestamp local events, preserve domain/epoch/quality information, reject invalid conversion attempts and reproduce behavior from fixtures. Wi-Fi findings enrich that capability only to the extent their evidence supports.

## Execution status through the 2026-10-03 follow-ups

- R1: exporter, strict v1 validator, source/input hashes and synthetic positive/negative fixtures implemented and locally tested. Downstream publication must pin the actual research commit and artifact digests.
- R2: the earlier campaign completed 12 captures and 138 requests. The later corrected-observer repeat quarantined on unmatched reports after 33 requests. Three controlled scans then reproduced another report-producing context; all failed their four-second profile. Firmware identity, exact sampling and calibrated accuracy remain open. See the [current ledger](../../qualification/gap-closure-ledger.md).
- R3: normal cleanup and fail-closed rejection have offline/live evidence at their recorded scopes. One historical adapter restart recovered, but broader lifecycle and firmware-drain guarantees remain open. The latest restart/suspend/roam authorization is preparation only; the continuous diagnostic collector needed for those tests is not yet implemented.
- D1: experimental Python/Windows QPC SDK and pure conditional estimator implemented downstream. Six one/four-reader runs covered 150,000 timed reads; provisional p99 targets are 5 us / 250 us, pending a separate acceptance campaign. Shared cross-process identity, native ABI and consumer freshness policy remain open.
- D2a: standalone downstream v1 validator, fixture copies and contract tests implemented. D2b/D2c hardware collector/conversion are not implemented.
- R4: documented Windows API/NDIS path and pinned mt76 source rechecked; concrete next experiments and equipment gates recorded. No new register, packet or cross-timestamp support claimed.
- R5/D3 and R6/D4: await their controlled-node/reference and operational prerequisites. No network synchronization or clock writes performed.

See [offline results](../../qualification/qualcomm-observation-matrix.md),
[evidence contract](../../evidence-contract.md) and
[delivery record](../../qualification/research-delivery-2026-10-02.md).

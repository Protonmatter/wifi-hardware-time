# First hardware-backed clock implementation plan

Build toward sub-millisecond relative synchronization by first qualifying TSF readout and obtaining a fresh, identifiable hardware observation with a bounded relationship to host time. Start with Qualcomm, keep NTP as a sanity check, and use a source-accessible backend if needed. Reading a counter, converting its time and synchronizing nodes require separate evidence.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** Current findings now include complete vendor package inventories, QUTS client ownership and a correction ledger. Historical acquisitions retain their original scope and limits. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

**Status:** proposed mini plan, 2026-10-03. No new hardware operation is authorized
or executed by this document. Existing quarantine and lifecycle restrictions remain.

**Execution update:** the [transport decision](../adapters/qualcomm-minimal-transport-contract.md)
is recorded. Milestone 2 has an implemented [diagnostic TSF replay subset](../tsf/tsf-evidence-reader.md)
and tests, reusing the existing evidence schema. This is not full qualified-record
admission. Milestones 3 through 6 remain gated on live attribution/sampling and
reference prerequisites. No native live client or downstream provider is enabled.

The autonomous branch also has a [saved management-frame decoder](../tsf/autonomous-management-tsf.md)
with authored-frame tests. It extracts peer TSF without a request match, but
does not establish a local RX timestamp, source epoch or fresh capture.

**Goal:** an application-facing clock whose supported error, freshness and failure
behavior are explicit. The first milestone is a qualified observation, not UTC
accuracy or Windows system-clock adjustment.

**Architecture:** research owns acquisition and evidence; `userspace-clock` owns
the maintained provider and application API. Fast application reads use QPC plus
a published conversion model; they do not issue a hardware request on every read.

**Tech stack:** existing Python 3.11+ tooling, native Windows acquisition only where
its ABI is established, existing tests; no new dependencies assumed.

**Spec:** [complete-record gate](../evidence/raw-timestamp-export-gate.md),
[FTM ownership](../ftm/ftm-ingress-to-owned-response.md), and
[vendor timing leads](../adapters/qualcomm-software-center-timing-leads.md).

**Execution:** implement sequentially with review at each acceptance gate. Use
the executing-plans skill when implementation is requested. Commit/push only
when requested. The paths below are proposed additions unless marked existing.

**Terms:** QPC is the Windows host interval counter. TSF is the Wi-Fi timer.
An ABI is a calling/buffer contract. An epoch identifies a period of continuity.
An owned copy remains valid after the producer reuses its buffer. See the
[glossary](../glossary.md).

## Contents

- [Required TSF readout](#required-tsf-readout)
- [Milestones](#milestones)
- [Constraints and review focus](#constraints-and-review-focus)
- [Checks and delivery](#checks-and-delivery)

## Required TSF readout

**TSF access is mandatory for this first clock implementation.** FTM, RX event
timestamps and SoC may add capabilities later; they cannot substitute for proving
that we can retrieve and identify the TSF counter itself.

The [existing TSF route](../tsf/README.md) has produced counter values through
asynchronous driver reports. Its IOCTL completion does not return the counter
tuple or prove fresh sampling. That historical result is a starting point, not
current permission to resume the quarantined campaign.

Milestones 1 through 4 must explicitly establish:

- [ ] **Read path:** trace `tsf_read_value` and its report delivery using existing
  exact-build protocol guards. QMSL and ART2 are not prerequisites for inspecting
  or qualifying this already discovered route. Alternative transports must prove
  their own connection to the same identified clock.
- [ ] **Value and source:** preserve raw TSF words/value, source interface/vdev,
  clock domain, meaningful width, units and qualified rate. A counter snapshot
  identifies its acquisition; do not invent packet identity for a non-packet read.
- [ ] **Observation profile:** distinguish solicited counter samples from
  autonomous frame/event observations. Both require clock identity and valid
  capture timing; only the solicited profile must bind a response to its request.
  Keep peer-advertised TSF separate from the local RX timestamp and QPC.
- [ ] **Freshness and ownership:** return an owned observation, retaining request
  times where applicable and report/receipt times with their actual meanings. Reject unknown/stale or
  ambiguously associated samples for clock-model updates. An advancing value
  alone does not establish the sample's age or host sampling bracket.
- [ ] **Continuity:** check repeat behavior in one permitted, bounded window at
  the existing approved limits/cadence. Test wrap, unexpected steps, duplicate
  reports and uncertain epochs offline; reserve disruptive lifecycle tests for
  their separate authorization. Do not force monotonicity across unknown resets.
- [ ] **SoC separation:** retain the distinction between cached action-3 SoC
  values and action-4 refresh behavior. Neither operation proves simultaneous
  TSF/SoC capture or establishes QPC correlation by itself.

**Acceptance:** first record diagnostic TSF readout as its own result; then
require fresh, attributable TSF observations for the hardware clock. A bounded
TSF-to-QPC mapping remains the separate milestone 4 gate. No successful RTT,
synthetic fixture, endpoint open or host-only timestamp satisfies this requirement.

## Milestones

### 1. Establish the minimum Qualcomm transport contract

**Deliverable:** `docs/adapters/qualcomm-minimal-transport-contract.md`.

- [ ] Trace endpoint, access rights, request layout, active-mode gate, response
  framing, valid lengths, identity, ownership and completion from exact-build
  evidence, starting with TSF readout. Use available driver/firmware evidence if
  QMSL remains unavailable.
- [ ] If pursuing ART2, resolve whether its shared consuming mailbox is reachable
  and appropriate for this operation. Reconcile its 2048-byte allocation and 4096-byte QMSL
  chunks; do not assume they describe the same layer or a safe request size.
- [ ] Record a go/no-go decision for one operation during normal connected Wi-Fi.
  Unknown mode, unresolved bounds, unowned results or absent timing semantics
  means no live client. Do not add selectors to the existing TSF allowlist.

**Done when:** a reviewer can trace one complete operation or identify its precise
missing dependency. If no usable path is established, retain Qualcomm findings
and propose a separately scoped Linux AXML exporter on physical test hardware.
Do not extend the search indefinitely or silently switch the active adapter mode.

### 2. Implement offline record admission

**Files:** `research/evidence/hardware_observation.py`,
`tests/test_hardware_observation.py`; reuse existing evidence validators where
their contracts match rather than changing the existing schema implicitly.

- [ ] Define `validate_observation(record: dict) -> dict`: return a validated
  owned record or raise `ValueError` with a stable rejection reason.
- [ ] Carry exact provenance, raw value/domain/unit/meaningful width, event
  reference point, packet/exchange identity, validity/loss, epoch, payload length
  and explicitly named host observations. Unknown semantics stay diagnostic-only.
- [ ] Write failing fixtures first, then implement admission. Test missing fields,
  wrong build/domain, wrap ambiguity, partial/duplicate/overwritten/late records,
  stale generations and caller claims unsupported by qualification evidence.

**Done when:** positive and negative synthetic fixtures behave correctly. This
does not establish a real producer or count as the successful hardware case.

### 3. Acquire one bounded, owned hardware record

**Files:** `research/acquisition/native_timing_once.c`,
`research/acquisition/run_timing_once.py`, `tests/test_timing_once.py`, and a
dated report under `docs/acquisition/`.

- [ ] After milestone 1, implement only its proven operation, with one transport
  owner, one outstanding request, exact target/build checks and fixed bounds.
  Pin the deadline, byte cap and cleanup procedure in the experiment profile
  from that contract before any live execution.
- [ ] Test the wrapper offline: child failure/timeout, identity change, late
  result, length mismatch and unconfirmed cleanup must reject and quarantine.
- [ ] Review the concrete live profile and existing quarantine disposition.
  No automatic rearm or assumption that a process restart drains firmware.
- [ ] Run one permitted acquisition, preserve the owned payload and host brackets,
  and verify cleanup and adapter state. Validate through milestone 2. The first
  clock path must include a TSF observation meeting the requirements above.

**Done when:** one actual record meets the complete-record gate. A returned blob,
successful IOCTL or synthetic pass alone cannot complete this milestone.

### 4. Establish hardware-to-QPC correlation

**Files:** `research/clock_models/analyze_hardware_qpc.py`,
`tests/test_hardware_qpc.py`, and `docs/clock-models/hardware-qpc-qualification.md`.

- [ ] Establish that the hardware sample occurred within a defined host bracket,
  or obtain an equivalent qualified cross timestamp. Request/receipt times and
  refreshed counters alone are insufficient. Qualify TSF-to-QPC specifically;
  FTM and SoC are optional inputs, not substitutes for this relationship.
- [ ] Implement `evaluate_pairs(records: list[dict]) -> dict` for qualified pairs:
  offset/rate fit, whole-run holdout error, sample age and invalidation outcomes.
- [ ] Test wrong domains, cached values, wrap/reset, future/stale observations and
  discontinuities. Measure bounded repeated idle/workload runs only after the
  preceding gates pass; keep sampling uncertainty separate from fitting residual.

**Done when:** a defensible mapping and freshness/error budget exist. Unknown
sampling uncertainty prevents publication of a bounded hardware clock model.

### 5. Integrate the qualified provider downstream

**Repository:** `userspace-clock`. **Files:** proposed
`userspace_clock/hardware.py`, `tests/test_hardware_clock.py`; update existing
`userspace_clock/__init__.py` and `docs/contracts/host-clock-v1.md` additively.

- [ ] Publish a provider model from the immutable research evidence package.
  Keep hardware source/domain/epoch distinct from the existing host clock.
- [ ] Expose the latest qualified raw TSF observation with sample-age status and
  provenance separately from the model-derived current time. A projected clock
  value must not be labelled as a newly read hardware counter.
- [ ] Serve reads from QPC and the qualified model. Expose age, quality and
  supported error; expired or invalid models return explicit unavailable status.
  Any host fallback must be labelled as host-only.
- [ ] Test expiration, model replacement, identity changes and one/four-reader
  consistency. Preserve existing host API behavior and counter conversions.

**Done when:** an application can use or reject the clock without understanding
the private transport. Local hardware correlation is not yet node synchronization.

### 6. Demonstrate relative synchronization; retain NTP as a comparison

**Files:** `docs/clock-models/two-node-validation-profile.md`,
`research/clock_models/analyze_peer_error.py`, `tests/test_peer_error.py`.

- [ ] Provide a second controlled node and qualified reference-message/time-transfer
  path. Specify whether RX/TSF alone suffices or raw FTM events add useful evidence;
  aggregate RTT alone does not establish offset.
- [ ] Predeclare a first statistical target: p99 absolute relative-clock error,
  including the validated comparison uncertainty, below 1 ms at prescheduled
  evaluation instants. Missing/unavailable evaluations count as misses, not
  discarded samples. Record maximum error, miss rate, duration and workload.
- [ ] Test the evaluator with injected offsets, drift, delay asymmetry, drops and
  reset/epoch changes before collecting real idle/workload measurements.
- [ ] Collect NTP offset/delay/source-quality observations as a separate sanity
  channel. Do not train and validate against the same observations or treat
  agreement with uncharacterized NTP as proof of sub-millisecond accuracy.

**Done when:** the declared profile passes against a characterized comparison
reference. With no controlled peer/reference, report NTP agreement and functional
results only. UTC accuracy and OS clock discipline remain separate later work.

## Constraints and review focus

- Stay exact-build and fail closed on identity changes. Hardware units and epochs
  are producer facts, not values callers may assert into existence.
- Preserve quarantine. No reset, suspend, reassociation, roaming, test-mode switch,
  register access or clock adjustment is added by this plan.
- Keep vendor bytes, traces and endpoint identifiers outside Git. Synthetic
  fixtures must be explicitly synthetic; pin reviewed sources before promotion.
- Review mismatched identity/domain (2/4), buffer reuse and competing readers (3),
  late results after timeout (2/3), partial parse followed by failure (2), and
  unobserved continuity loss/model expiration (4/5). Each needs a rejection test.
- Existing host-only consumer acceptance and disruptive lifecycle campaigns do
  not become complete or authorized through these milestones. Their separate
  qualification remains required; this plan does not lift earlier gates.

## Checks and delivery

For each implemented slice: add focused failing tests, implement the minimum,
run them to pass, review the diff and preserve the evidence limits. Then run:

```powershell
python -m compileall -q research tests
python -m unittest discover -s tests -v
git diff --check
```

Use the exact owned driver fixture for static integration checks where available.
Native compilation and live checks are added only for the relevant slice and
reported separately. Downstream runs its own suite from its repository root.
Each milestone ends with a small reviewable change and explicit supported claim;
publication requires a requested commit/push and CI on that exact revision.

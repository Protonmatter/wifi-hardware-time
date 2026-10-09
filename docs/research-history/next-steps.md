# Next steps and evidence required to complete them

The immediate opportunity is a more thoroughly qualified conditional TSF event-timestamp service on the selected Qualcomm Windows system. The complete original-event path remains a separate access problem. Work below is sequenced by evidence dependencies; it does not authorize a live experiment or imply that a documented plan has run.

[Guide](README.md) · [Current results](results-and-validation.md) · [Detailed implementation roadmap](../overview/persistent-tsf-next-steps.md)

## Priority sequence

| Order / scope | Concrete work | Acceptance evidence | Current status |
|---|---|---|---|
| 1. Preserve the corrected baseline | Retain source/input hashes, original results, current policy versions, immutable receipts, quarantine and unfinished-run state | Exact-head software checks and no alteration of original capture/result files | Implemented in the merged baseline; this review adds documentation provenance |
| 2. Persistent acquisition across time and load | Design and then separately authorize matched hour-long idle/load runs using persistent mode with report wait retained | Actual request/trace/workload duration; accepted-gap and delivery distributions; all losses/stops; normal lifecycle; both runs meet their predeclared profile | Existing hours used the earlier acquisition mode; persistent evidence is one five-minute idle smoke |
| 3. Failure and continuity behavior | Complete offline cases first, then choose a least-disruptive bounded real failure profile | Actual terminal result or explicit unresolved ownership; sticky failure; durable records; justified re-admission; original successful requests preserved | Software corrections exist; real cancellation/owner-loss/drain qualification remains open |
| 4. Causal online admission | Define association, completeness, delivery watermark/bound, duplicates, foreign traffic, deadlines and epoch rules using only information available at decision time | Prefix-invariance, delayed/reordered/contradictory evidence tests; bounded queues and honest loss; measured end-to-end availability | Not implemented as a qualified live admission path; full-recording screening remains in the published replay |
| 5. Maintained consumer integration | Feed admitted samples into the maintained provider; preserve raw QPC/epoch, provisional value/state and separately derived settlement | Versioned contract, exact research/consumer parity, explicit stale/invalid/pending behavior and application latency | Research code and historical downstream software results exist; no claim of a qualified live radio provider |
| 6. Source semantics and independent time | Determine physical capture reference, source clock/link and station/AP relation; build an independent comparison budget | Measured bias, error/tails, reference uncertainty and validity limits on the tested hardware/conditions | Open; a second controlled observation/reference is missing from the retained qualification |
| 7. Multi-device or UTC extension | Combine per-node/source/reference uncertainty and test controlled peers or a traceable UTC reference | Demonstrated combined bound across epochs, load and relevant transitions | No qualified result yet |

Orders 2–4 share research inputs, but passing normal long-run acquisition does not substitute for the failure or admission gate. Physical validation can be prepared in parallel as a research design; it cannot be inferred from further same-machine fitting.

## The report-wait optimization needs a contract first

The persistent worker still waits for diagnostics. Before issuing another request while earlier reports may be in delivery, establish what bounds association and outstanding firmware work. One outstanding kernel request is not necessarily one outstanding firmware report. A proposed decoupled mode needs sequence/session identity, bounded queueing, overflow handling, stale/duplicate/foreign rejection and no catch-up bursts. Compare matched conditions and actual accepted-sample gaps; do not infer a coverage improvement from a short IOCTL or requested cadence. See [roadmap phase 4](../overview/persistent-tsf-next-steps.md#4-separate-report-delivery-from-request-scheduling-only-after-research).

## Reopening the complete original-event track

The useful dependency is an owner-supported API or instrumentable copy point before fields become text or reduced metadata. Establish the exact adapter/firmware/build binding, input extent, schema, ownership/publication, loss counters and bounded lifecycle. Then obtain one complete real record that survives source-buffer reuse, followed by controlled lifecycle qualification. Only afterward can its clock fields enter a timing model.

Use the [existing complete-event plan](../overview/complete-event-2026-10-05/engineering-plan.md) and [route decision](../evidence/hardware-route-decision-2026-10-06.md). The public plan specifies the required producer access, ownership and lifecycle evidence. Private unpublished follow-ups remain outside this public account.

## Work kept in reserve

- **Nested IHV controls:** retain the static map, including scan/GPIO/channel/host-state effects. The eight-byte positive control does not admit other selectors.
- **Linux/MediaTek or another hardware backend:** retain as a conditional alternative requiring physical target selection and its own qualification. Do not transfer ath9k or mt76 findings across incompatible hardware/transport assumptions.
- **Reset, suspend, roaming and clock discipline:** separate explicit operational profiles. Documentation refresh and prior normal shutdown do not authorize them.
- **Mathematical optimization:** retain exact reference arithmetic and the ±200-ppm prior unless independent evidence and a versioned contract justify change. Benchmarking or narrower output alone is insufficient.

## Maintaining the research account

For each new experiment, record the question, predeclared criteria, exact source/build, operation and authorization scope, raw-evidence location/digests, all attempts, actual conditions, failures, interpretation and next decision. Update the timeline and hypothesis ledger only after linking the original report. Add a new result version rather than overwriting earlier measurements. Archive the superseded narrative before changing current status; use the [archive policy](../../archive/README.md).

For publication, recheck [the recorded repository/PR state](publication-status.md), current remote head and hosted checks. Commit, push, PR update and merge remain separate actions. The corrected interactive atlas PR #10 is merged. Its README/gallery navigation and export checks are retained in this documentation branch. This documentation refresh is published as a separate PR; it does not add a live experiment or physical qualification.

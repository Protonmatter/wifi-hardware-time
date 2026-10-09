# Complete-event integration: implementation plan

The bounded receive-shutdown audit and current QMSL callback trace are complete within their static scope. The 2026-10-06 route decision is no-go for current installed Qualcomm live integration: demonstrated supported/vendor/instrumented producer access remains missing. A real retained event is still required to qualify that connection. Diagnostic replay and host API acceptance can proceed independently; timing interpretation and host-clock correlation retain separate gates.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../../research-history/README.md) · [Timeline](../../research-history/timeline.md) · [Previous version](../../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__overview__complete-event-2026-10-05__engineering-plan.md).
<!-- /research-history -->

**Current status:** [S0/S2 closure and the qualification ledger](../gap-closure-ledger.md),
[exact PR component map](../pr3-component-review-map-2026-10-06.md), and
[hardware route ruling](../../evidence/hardware-route-decision-2026-10-06.md).
S1's [6.1.365.1 worker/listener trace](../../adapters/qmsl-runtime-365.md) has already
finished; do not restart it from the old runtime. The coordinator reports S8's
local host profile passed and S9's local patch was preserved/verified without
publication. S3 replay implementation, documentation and review are complete for
the five-profile diagnostic slice: 15 focused and 64 downstream tests passed.
The [WPP file assessment](../../evidence/wpp-external-2311-file-assessment.md)
adds collection tooling but no demonstrated complete-event producer. Linux has
not been selected.

## Read the decisions first

- [Context and existing components](context-map.md).
- [Outcome and acceptance criteria](problem-and-scope.md).
- [Primary-source route comparison](route-research.md).
- [Interface and operational review](devex-review.md).
- [Test matrix](test-matrix.md) and [decision log](decision-log.md).

## Sequenced work

| Phase | Concrete work | Completion evidence | Status |
|---|---|---|---|
| A. Reassess routes | Compare vendor/private, NDIS, WPP, cross-timestamp and Linux producer routes | Pinned source receipts and qualified decision table | Research completed |
| B. Audit Windows source lifetime | Follow HIF disable/stop, queued receives, callback clearing, MDL/backing release and DMA-enabler ordering | Exact-image receipt, branch/call evidence, tests and unresolved edges | Bounded audit implemented and tested; full live ordering remains open |
| C. Integrate an actual producer | Supported event facility or reviewed source/instrumented driver; copy at WMI pre-mutation or earlier HIF boundary | Buildable integration against a real callback/return contract | No-go now; demonstrated external integration access required under S2 |
| D. Retrieve one event | One bounded existing-event acquisition; validate owned response and compare original bytes/metadata | Hardware receipt plus rejection, pressure, cancellation and teardown results | Depends on C and reviewed live experiment |
| E. Adopt live diagnostic observations | Versioned live provenance and consumer tests; retain raw event and explicit unknowns | Research handoff to `userspace-clock`, with independent capability states | Live adoption depends on D; separate five-profile S3 replay is implemented/reviewed with 15 focused tests passing and hardware disabled |
| F. Establish clock use | Prove event/clock meaning, request association where required, fresh sample relation and hardware/host conversion | Sampling bounds and independent accuracy validation | Separate hardware/reference gates |

Phase B is bounded to the selected exact-build shutdown chain and its immediate
dispatch targets. If it leaves an indirect target or join unproven, record that
edge rather than extending a success claim. It cannot substitute for phase C.

**2026-10-05 executed result:** [receive-shutdown evidence](../../tsf/receive-shutdown-contract.md)
and the inspector now preserve ignored drain status, a caller-unreported
completion timeout, conditional thread waits and selected release order.
All 320 configured offline tests passed with zero skips. The remaining callback
coverage and DMA-enabler release-order gaps are explicit in the receipt; no live
producer or timing capability was enabled.

## Required data flow

```text
Actual receive callback owns valid event storage
    |
    | Validate span + source + required synchronization
    v
Copy original event into bounded producer-owned slot
    |
    | Finish bytes and metadata, then publish
    v
Ready queue -> pair with validated application request
    |
    | Return exact initialized bytes, complete once
    v
Application owns diagnostic record -> validate -> retain or quarantine
                                                |
                                                ? Separate clock-use gate
```

The arrows after the actual callback are required implementation behavior, not
an installed exporter. Existing user-mode broker tests cover part of this flow.

## Lifecycle and failure rules for phase C

```text
UNBOUND -> READY -> ACCEPTING -> CLOSING -> QUIESCENT -> RELEASED
                         |          |
                         |          +-> timeout/failure: retain referenced storage
                         v
                    QUARANTINED -> CLOSING
```

- `UNBOUND`: no producer contract; hardware acquisition is unavailable.
- `ACCEPTING`: admit only validated events; one owned copy per admitted event.
- `QUARANTINED`: stop admission on unknown continuity, source ambiguity or loss
  requiring review; process restart does not prove old firmware reports drained.
- `CLOSING`: deny new producers/read requests, unregister the source, join entered
  callbacks, settle application requests, then release queued events.
- `QUIESCENT`: every relevant user of the storage has finished; only then free it.
- Timeout must return failure while preserving still-referenced storage. No retry
  may duplicate a completion or reinterpret an old event as a new firmware reply.

Output-too-small must not return a successful partial event. Local overflow and
source-reported loss remain distinct; unobservable firmware loss stays unknown.
Client cleanup and producer shutdown are separate operations. Caller-owned source
storage must remain stable throughout the copy, including any lock wait.

## Validation and rollback

Phase B changes `research/tsf/inspect_tsf_ingress.py`, its tests and linked evidence.
Risk is low: ordinary file reads, no device operations. Run focused exact-image
tests, then the configured native/image suite, documentation/index/diagram checks
and diff review. Keep raw Ghidra outputs private. Remove only newly chosen private
output files if abandoning the run; preserve existing working-tree changes.

Phase C has no deployment recipe until its actual integration mechanism exists.
Its future review must cover build/signing, access control, callback execution
level, DMA visibility, unregistration, device removal and a tested rollback path.
Reset/suspend/roaming, test mode, logging-mask changes and boot debugging remain
outside this run. Publication and hosted CI require a separate commit/push request.

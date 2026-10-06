# Complete-event integration: implementation plan

First resolve what the selected receive shutdown actually stops, waits for and frees, and make that evidence repeatable. Then connect a supported or instrumented producer to an owned response. Only a real retained event can qualify that connection. Timing interpretation and host-clock correlation follow as separate phases, with explicit failure and continuity rules.

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
| C. Integrate an actual producer | Supported event facility or reviewed source/instrumented driver; copy at WMI pre-mutation or earlier HIF boundary | Buildable integration against a real callback/return contract | Requires external integration access |
| D. Retrieve one event | One bounded existing-event acquisition; validate owned response and compare original bytes/metadata | Hardware receipt plus rejection, pressure, cancellation and teardown results | Depends on C and reviewed live experiment |
| E. Adopt diagnostic observations | Versioned live provenance and consumer tests; retain raw event and explicit unknowns | Research handoff to `userspace-clock`, with independent capability states | Depends on D |
| F. Establish clock use | Prove event/clock meaning, request association where required, fresh sample relation and hardware/host conversion | Sampling bounds and independent accuracy validation | Separate hardware/reference gates |

Phase B is bounded to the selected exact-build shutdown chain and its immediate
dispatch targets. If it leaves an indirect target or join unproven, record that
edge rather than extending a success claim. It cannot substitute for phase C.

**Executed result:** [receive-shutdown evidence](../../tsf/receive-shutdown-contract.md)
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

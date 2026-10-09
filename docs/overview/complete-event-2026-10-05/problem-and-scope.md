# Complete-event integration: outcome and scope

The next useful hardware result is one complete, attributable event retained in application-owned storage after the producer can reuse its buffer. It may initially be diagnostic data with unknown timing semantics. This plan advances that result without treating a working byte transport, trace timestamp or successful software test as a hardware clock qualification.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../../research-history/README.md) · [Timeline](../../research-history/timeline.md) · [Previous version](../../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__overview__complete-event-2026-10-05__problem-and-scope.md).
<!-- /research-history -->

## Acceptance criteria

- Identify exact source/driver/firmware provenance and the capture boundary.
- Establish valid source spans, length, required synchronization and lifetime.
- Preserve original bytes and identity before reduction; no borrowed pointers.
- Publish only a complete copy and account for local loss and unknown source loss.
- Define exact returned lengths, rejection, cancellation and teardown behavior.
- Preserve unknown clock identity, units, sampling instant and epoch explicitly.
- Demonstrate at least one actual hardware record before enabling live provenance.

## Current executable scope

1. Reassess candidate routes using primary documentation and pinned source.
2. Trace receive shutdown through buffer/MDL release in the exact Windows image.
3. Add repeatable static receipts and tests for the established links and limits.
4. Produce an implementation handoff with explicit external prerequisites.

The remaining phases are conditional on a demonstrated producer integration.
No kernel installation, new firmware operation, debug-boot change or disruptive
lifecycle experiment is implied by executing the file-only phases.

Clock conversion, two-node synchronization and system discipline retain separate
gates. Full driver source is not mandatory if a supported complete-event interface
supplies the required contract.

See [engineering sequencing](engineering-plan.md) and [test gates](test-matrix.md).

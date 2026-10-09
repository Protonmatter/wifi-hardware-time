# Complete-event integration: interface and operational review

Reuse the existing file-only inspector and application broker. The immediate change should make shutdown evidence reproducible, not introduce another speculative device ABI. A future live adapter must have its own reviewed provenance and completion contract; the current fixture/replay interface must continue rejecting promotion to a hardware clock.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../../research-history/README.md) · [Timeline](../../research-history/timeline.md) · [Previous version](../../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__overview__complete-event-2026-10-05__devex-review.md).
<!-- /research-history -->

## Interface decisions

- Add structured static evidence to the existing inspector without removing fields.
- Preserve exact-image hashing, bounded file input, new-output-only behavior and
  documented exit codes. No network or device operations inside the inspector.
- Keep image offsets, host software generations and firmware identities separate.
- Keep diagnostic retention separate from clock-sample admission.
- Do not add a new native dependency, kernel driver or resident service for this slice.

## Failure and security review

- An unknown image fails before interpreting offsets.
- An unresolved indirect call stays unresolved; a function name cannot certify a join.
- Static waits, flags and queue operations do not establish live firmware drain.
- Raw traces and endpoint identifiers remain private; public receipts contain
  authored conclusions, hashes and code locations only.
- No new allocation/free/read primitive is exposed to untrusted applications.
- Live integration later needs access control, bounded buffers, client cleanup,
  exact returned lengths and cancellation arbitration.

Product review is unnecessary: the observation outcome is already defined.
UI/design review is unnecessary: this slice has no application UI. Engineering,
API/error behavior, lifecycle and publication risks are included in the plan.

See the [test matrix](test-matrix.md) and [engineering plan](engineering-plan.md).

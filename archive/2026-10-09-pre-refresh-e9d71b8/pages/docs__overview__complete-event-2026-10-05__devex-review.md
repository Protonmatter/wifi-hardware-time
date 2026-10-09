# Complete-event integration: interface and operational review

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__overview__complete-event-2026-10-05__devex-review.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Reuse the existing file-only inspector and application broker. The immediate change should make shutdown evidence reproducible, not introduce another speculative device ABI. A future live adapter must have its own reviewed provenance and completion contract; the current fixture/replay interface must continue rejecting promotion to a hardware clock.

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

See the [test matrix](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/complete-event-2026-10-05/test-matrix.md) and [engineering plan](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/complete-event-2026-10-05/engineering-plan.md).

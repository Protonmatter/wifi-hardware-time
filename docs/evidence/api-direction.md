# Proposed hardware-time boundary

Applications need timestamps with clear clock identity, sampling meaning and limits, not just a raw number. This proposed boundary separates hardware observations from validated conversions and optional synchronization. The host-only implementation can serve local event timing now; the Wi-Fi backend still needs a trustworthy way to return complete, attributable samples.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** A QUTS client-owned byte return is now located statically. Keep client ownership, server publication, firmware identity and timing accuracy as separate qualification states. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

**Key terms:** An API is an interface used by software. A backend implements it for a specific source. Epoch identifies a period of continuity; changing sources or losing continuity may require a new epoch. See the [glossary](../glossary.md).

This is a direction for future work, not an implemented stable API.

Linux instrumentation and Windows vendor diagnostics should feed the same explicit observation model. Workstations on Windows, macOS, or Linux can consume measurements from a Linux timing node without requiring native low-level adapter support on every platform.

A clock snapshot needs:

- Raw counter ticks and their units.
- Clock, virtual-interface and epoch identities (which counter, interface and period of continuity).
- Host timing before/after the acquisition and its success or failure status.

A packet observation also needs:

- Transmit/receive direction and the exact event being timestamped.
- Packet identity and the descriptor format that carries its metadata.
- Retry/aggregation context and flags saying whether the value is valid.

Keep these stages separate:

```text
raw hardware observation -> validated clock conversion -> correlation model
                                                      -> optional PHC/PTP service
                                                      -> analysis/capture consumer
```

The first useful mt7921 implementation is a status-returning, serialized TSF snapshot plus RX observations. Raw TXS capture is a subsequent qualification milestone. PHC registration and socket timestamp integration follow only after counter semantics and completion association are established.

The Windows Qualcomm path first needs a reliable TSF report-return mechanism. Host-only getters and accepted firmware commands are useful diagnostic milestones, not a completed backend.

The [latest boundary findings](../memory-ring/timing-boundary-investigation-2026-10-03.md)
make that requirement concrete: complete-record publication/lifetime, propagated
request and epoch identity, and known sampling/reference points must precede
conversion. Existing ring dump consumers and RX descriptor diagnostic fields
are investigation leads, not application APIs. Downstream already implements an
experimental host-only QPC API and pure conditional estimator; that implementation
does not supply these hardware semantics or enable synchronization/discipline.

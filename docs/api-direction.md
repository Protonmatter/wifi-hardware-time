# Proposed hardware-time boundary

This is a direction for future work, not an implemented stable API.

Linux instrumentation and Windows vendor diagnostics should feed the same explicit observation model. Workstations on Windows, macOS, or Linux can consume measurements from a Linux timing node without requiring native low-level adapter support on every platform.

A clock snapshot should preserve raw ticks, units, clock identity, virtual-interface/OMAC identity, epoch, host-before/after, and acquisition status. A packet observation should additionally preserve RX/TX direction, the hardware reference instant, packet identity, descriptor format, retry/aggregation context, and validity flags.

Keep these stages separate:

```text
raw hardware observation -> validated clock conversion -> correlation model
                                                      -> optional PHC/PTP service
                                                      -> analysis/capture consumer
```

The first useful mt7921 implementation is a status-returning, serialized TSF snapshot plus RX observations. Raw TXS capture is a subsequent qualification milestone. PHC registration and socket timestamp integration follow only after counter semantics and completion association are established.

The Windows Qualcomm path first needs a reliable TSF report-return mechanism. Host-only getters and accepted firmware commands are useful diagnostic milestones, not a completed backend.

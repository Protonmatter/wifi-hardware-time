# Stronger timestamp paths and equipment gates

Which experiment would resolve the remaining timing gaps? Windows needs a matched comparison with a known-capable adapter; the ALFA path needs a dedicated Linux host and live validation. Neither source inspection nor a generic equipment label establishes timing accuracy, safe register access, or a suitable reference.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__backend-and-reference-next-steps.md).
<!-- /research-history -->

A cross timestamp pairs hardware-clock and host-clock observations. QPC (QueryPerformanceCounter) is the Windows host counter; an independent reference supplies a separately characterized timing measurement. See the [glossary](../glossary.md).

This pass rechecked the pinned local mt76 source and Microsoft's documented
Windows entry points. No new hardware capability or safe register target was
established. The purpose is to identify the experiment that would resolve each
remaining uncertainty, rather than repeat an inconclusive probe.

## Contents

- [Windows documented path](#windows-documented-path)
- [Linux AXML path](#linux-axml-path)
- [Equipment by question](#equipment-by-question)

## Windows documented path

`CaptureInterfaceHardwareCrossTimestamp` is the supported adapter cross-timestamp
entry point on the documented Windows versions. Its contract is different from
an asynchronous diagnostic report. [Microsoft API reference](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-captureinterfacehardwarecrosstimestamp).

NDIS handles `OID_TIMESTAMP_CAPABILITY` from the miniport's timestamp-capability
indication. Therefore failing to locate an explicit OID handler in the private
driver is not proof of missing hardware support. [Microsoft OID reference](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/oid-timestamp-capability).

The next useful experiment is a matched SDK-built query on a known-capable NIC
and the Qualcomm adapter, with the same OS/SDK, exact LUID conversion, return
codes and validated output layouts. Then trace the error-23 return path to the
OS/provider boundary or prepare a minimal vendor support reproduction. Do not
interpret failed output buffers as data. No additional interface is assumed
available, and no new query was issued in this pass.

## Linux AXML path

Local mt76 revision rechecked: `be5ce7910521492d4a2e4ce7ee3843680a46c047`.

- `mt792x_core.c:332`, `mt792x_get_tsf`: serialized control-register update then
  low/high TSF reads. The existing callback returns a value, so a research
  snapshot interface must separately surface transport errors and its reference
  point. A nominal read operation includes a capture-control write.
- `mt7921/mac.c:308`: group-2 RX descriptor provides a 32-bit timestamp and
  `RX_FLAG_MACTIME_START`; A-MPDU subframes can share a timestamp. An application
  must not infer independent per-subframe RF event times from this field.
- `mt76_connac2_mac.h:174`: the TX status timestamp field is defined. That does
  not establish a working userspace TX timestamp delivery path.

Next: obtain a dedicated Linux node with the actual USB adapter, pin kernel and
firmware, demonstrate a status-returning snapshot, then join RX timestamp width,
wrap/epoch and aggregation metadata with controlled traffic. TX retry/completion
association follows after RX semantics are understood. No PHC or socket timestamp
claim is promoted from source inspection alone. See [AXML research](axml.md).

## Equipment by question

| Question | Minimum additional setup | What it resolves / does not resolve |
|---|---|---|
| Ingestion, lifecycle models, local host API | None | Offline correctness; no physical accuracy |
| AXML source-level live backend | Dedicated Linux host, actual AXML, reproducible kernel/firmware and recovery connection | Device access, RX semantics and transport behavior; no independent clock truth |
| Generalized reset/suspend/cancellation | Dedicated recoverable test host and local console | Lifecycle behavior without risking the primary workstation's connection |
| Actual roaming | Two controlled APs with known association topology | Roam events/epochs; not a common time reference merely because SSIDs match |
| Two-node correlation | Second controlled node and explicit network topology | Offset/rate estimation, loss/asymmetry behavior; accuracy still needs a reference |
| Calibrated clock error | Independent reference delivered through a characterized hardware timestamp path, such as qualified PTP hardware or GNSS/PPS with appropriate timestamp input | Reference epoch and an uncertainty budget; generic USB receipt time alone is insufficient |
| FTM ranging accuracy | Identified responder, measured geometry/uncertainty, controlled conditions and preferably independent RF evidence | Range bias and variance; does not automatically establish clock offset |

Do not purchase a reference from a generic feature label alone. First specify
the target error/freshness requirement, supported host interface, reference time
scale, timestamp reference point and a way to measure delivery uncertainty.
No specific product has been evaluated here.

Raw-register work remains gated on an exact address-space mapping, a needed benign
target, side-effect knowledge and reliable result validity. No live register
read is justified by these source checks.

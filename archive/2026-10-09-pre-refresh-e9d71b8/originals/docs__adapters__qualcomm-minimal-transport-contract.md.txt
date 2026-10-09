# Minimum Qualcomm TSF transport: current implementation decision

The known private command produces asynchronous TSF reports, not a counter tuple in its immediate reply. Saved reports can now be read through an owned diagnostic API. Fresh sampling, report ownership and a hardware-to-host bracket remain unresolved, so this decision permits offline replay but does not enable a new live client or clock provider.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

## Known contract

- Exact ARM64 driver SHA-256:
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- The existing `qualcomm_protocol.py` validates the build and constructs the
  128-byte named-command request. `tsf_read_value` maps to the recorded TSF
  firmware path; the legacy IOCTL output is a 100-byte argument block.
- Historical calls returned no counter tuple in that output. Counters arrived
  through report event `0x5005` and diagnostic logging.
- Action 3 and action 4 have distinct observed SoC cache/refresh behavior.
  Neither establishes simultaneous capture or the exact TSF sampling instant.
- Request-window association is not a firmware transaction identifier. Ordinary
  scans have also generated reports; one outstanding user request does not
  establish exclusive ownership of the next report.

ABI means argument and buffer layout. QPC is the host interval counter. A
sampling bracket must contain the actual hardware sample, not just command
submission or log delivery. See the [protocol findings](qualcomm.md) and
[glossary](../glossary.md).

## Decision

| Operation | Disposition | Reason |
|---|---|---|
| Read saved TSF evidence | Implemented, diagnostic-only | Can validate the existing format and return detached records |
| New live TSF request | No-go under current admission state | Campaign quarantined; fresh attribution and late-report isolation unresolved |
| Native synchronous TSF getter | Not implemented | No verified immediate counter-return contract identified |
| Clock-model admission | Reject | Units/rate, meaningful width, physical source/epoch and sampling bracket remain unqualified |
| ART2/QMSL replacement | Separate candidate | No proven equivalence to this TSF path; test mode, lengths and consuming-mailbox ownership unresolved |

The precise next dependency is a response association and fresh-sampling contract
for the solicited TSF profile, plus reviewed quarantine disposition. An autonomous
profile can instead qualify event/source-clock identity and capture timing without
a host request token; neither profile is qualified by current diagnostic logs.
A wider host request number or
quiet interval does not prove old firmware responses have drained. New live work
must retain the established request limits, target checks and recovery conditions.
The observed endpoint open/close result does not resolve these dependencies.

The [association review](../tsf/tsf-association-and-quarantine-disposition.md)
retains quarantine and identifies omitted report-type/clock-context fields as
a concrete next lead. Their candidate meanings come from a different platform's
header and are not yet verified on this firmware or available in existing logs.

## Implemented boundary and validation

The [TSF evidence reader](../tsf/tsf-evidence-reader.md) reuses the existing bundle
validator. It does not open the device, start a trace, change a mode or alter any
quarantine marker. Its application copy is owned Python data; it does not extend
or establish driver-buffer lifetime.

Offline replay read 138 observations from 12 retained historical captures.
All remain diagnostic-only. This is a saved-evidence integration result, not
another hardware campaign. The [implementation plan](../overview/2026-10-03-first-hardware-clock-plan.md)
therefore advances its offline portion only; live export and TSF-to-QPC remain
open. No clock capability is promoted by this transport decision.

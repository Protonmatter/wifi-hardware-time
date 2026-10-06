# Complete-event integration: decisions and execution

The immediate implementation is a bounded, repeatable audit of receive shutdown and source lifetime. The preferred native exporter remains conditional on a real integration point. Alternative packet, trace and Linux routes are retained with their actual limitations, so software progress cannot accidentally enable an unqualified hardware clock.

| Decision | Reason / evidence | Owner and status |
|---|---|---|
| Reuse the current inspector and broker | Existing interfaces/tests already cover exact-image and application ownership boundaries | Research implementation; selected |
| Execute the Windows lifetime audit first | New allocation/free evidence makes shutdown ordering the next concrete source-validity question | Research implementation; bounded audit completed, live qualification open |
| Prefer supported or instrumented producer integration | It can copy bytes while their lifetime is valid | Vendor/OEM or controlled driver-development owner; access not established |
| Do not treat NDIS/WPP as arbitrary private-event taps | Their actual observation/emission points constrain available data | Research decision; source-backed |
| Keep Linux as a controlled alternative | Source can be changed; inspected stock trace/test routes are not a generic connected-mode WMI export | Hardware/backend owner; physical qualification outstanding |
| Keep nested IHV controls deferred | Direct user scope decision | User decision; unchanged |
| Retain quarantine and separate timing gates | Existing unmatched reports and absent independent reference remain unresolved | Research qualification; unchanged |

## Execution record

Route comparison is complete in [route research](route-research.md). Phase B is
implemented in the existing TSF ingress inspector, with findings in
[receive-shutdown evidence](../../tsf/receive-shutdown-contract.md).

- Six Ghidra runs: 29 distinct functions, complete exports, no decompilation failure.
- Two added exact-image tests passed; focused ingress suite: 10 tests, zero skips.
- Configured full suite: **320 tests passed, zero skips**, including native and
  exact driver/Windows fixtures. Python compilation passed.
- Fresh inspector receipt keeps live rundown, all-callback coverage and DMA-enabler
  release ordering unqualified. Public-source files have private hash receipts.
- Final read-only status: Wi-Fi **Up**, driver **1.0.4374.1300**.
- No elevation, device command, reset, kernel-memory read or driver change.

Private receipts are in `artifacts/export-route-reassessment-20261005/`.
At this experiment's validation time, the changes were local and uncommitted.
Publication and revision-specific hosted checks are tracked in
[PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

**Next gate:** obtain or identify a real producer integration with valid copying,
publication and application return. No hardware export, live teardown or
clock-accuracy result is claimed by completing phases A and B.

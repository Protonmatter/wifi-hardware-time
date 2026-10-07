# Complete-event integration: decisions and execution

The bounded receive-lifetime audit and current QMSL callback trace have finished within their static scope. The 2026-10-06 hardware ruling is no-go for current installed Qualcomm live integration because a supported/vendor/instrumented producer connection has not been demonstrated. The WPP installation adds trace tooling without closing that gap. Linux remains a conditional alternate requiring a physical target and explicit selection. Independent software, host-profile and preservation results enable no hardware clock capability.

## 2026-10-06 S0/S2 closure

- S0 pins PR #3 at base `0e866ed6b2409231c100af75a6aef97c6bdd2fa3` and head
  `aca5b7ca7c96ca8731f15202361c34faf003f350`. Its 220 changed files are classified
  in the [component map](../pr3-component-review-map-2026-10-06.md), including
  actual available review evidence, tests, risks and outstanding review scope.
  The map and passing CI are not full-review approval.
- S1 is the completed [6.1.365.1 static trace](../../adapters/qmsl-runtime-365.md),
  including worker/listener payload transfer and indefinite lifecycle waits.
  Runtime absence is superseded; live attribution and lifecycle bounds remain open.
- S2 records an explicit [no-go and route reopening criteria](../../evidence/hardware-route-decision-2026-10-06.md).
  The next dependency is demonstrated supported/vendor/instrumented producer
  access, not another generic package inventory or repeated callback trace.
- The coordinator reports S3 implementation/documentation/review complete with
  15 focused tests and 64 downstream tests passed; S8's 12-run local host profile passed, including revalidation after verifier corrections; and S9's
  nine-file local patch was preserved/verified without publication. S8 is not a
  consumer SLA or accuracy qualification. S4/S5 remain gated; deferred IHV work
  and the private campaign quarantine are unchanged.
- The [WPP External 2.3.1.1 file assessment](../../evidence/wpp-external-2311-file-assessment.md)
  records 88 hashed files, ETL collection/configuration leads and state-changing
  Wi-Fi trigger behavior. No vendor code ran; the current no-go remains.

## Decisions retained from the receive-lifetime phase

The later [PR #3 software review](../pr3-review-2026-10-06.md) completed the
component assignments and corrected four reproduced defects. Its configured
344-test pass and bounded offline validations do not reopen the hardware route.
Publication, hosted CI for the corrected revision and merge remain separate.

| Decision | Reason / evidence | Owner and status |
|---|---|---|
| Reuse the current inspector and broker | Existing interfaces/tests already cover exact-image and application ownership boundaries | Research implementation; selected |
| Execute the Windows lifetime audit first | New allocation/free evidence makes shutdown ordering the next concrete source-validity question | Research implementation; bounded audit completed, live qualification open |
| Prefer supported or instrumented producer integration | It can copy bytes while their lifetime is valid | Vendor/OEM or controlled driver-development owner; access not established |
| Do not treat NDIS/WPP as arbitrary private-event taps | Their actual observation/emission points constrain available data | Research decision; source-backed |
| Keep Linux as a controlled alternative | Source can be changed; inspected stock trace/test routes are not a generic connected-mode WMI export | Hardware/backend owner; physical qualification outstanding |
| Keep nested IHV controls deferred | Direct user scope decision | User decision; unchanged |
| Retain quarantine and separate timing gates | Existing unmatched reports and absent independent reference remain unresolved | Research qualification; unchanged |

## Historical execution record: 2026-10-05

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

**Current next gate:** obtain demonstrated access to a real producer integration
with valid copying, publication and application return, then satisfy the S2
reopening criteria above. No hardware export, live teardown or clock-accuracy
result is claimed by completing phases A/B or S1/S2.

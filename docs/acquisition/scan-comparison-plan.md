# Bounded scan/TSF source comparison

This plan tests whether extra clock reports appear after a normal Wi-Fi scan without private timing requests. It defines quiet periods, deadlines and rejection rules before execution. The later three trials reproduced the report pattern but all failed the four-second completion limit; the private campaign therefore remains quarantined.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** The private campaign remains quarantined. The new QUTS client ownership finding does not establish firmware drain, report association or a new live acquisition. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

TSF is the Wi-Fi timing counter; SoC denotes the reported system-on-chip counter. QPC is Windows' high-resolution host counter. WLAN means wireless LAN; ACM notifications report Windows Wi-Fi connection and scan events. See the [glossary](../glossary.md) for related terms.

## Contents

- [Design and stop conditions](#design-and-stop-conditions)
- [Implementation and validation](#implementation-and-validation)

Question: do unassigned TSF/SoC reports recur in a controlled scan intervention
without a private TSF request, and are they absent in the preceding quiet window?
The earlier trace contained a START_SCAN command about 28.6 ms before the first
unmatched TSF report. This experiment tests that lead; it does not assume causality.

Scope: exact Qualcomm adapter/build already qualified for observation, existing
selected observer/decoder, three trials maximum. The private campaign remains
quarantined. A new branch isolates this follow-up from the merged baseline.

## Design and stop conditions

Each trial follows this sequence:

1. Check the exact driver identity and create a fresh 32 MiB circular ETW capture
   with a native lifecycle observer. ETW is Windows event tracing.
2. Establish readiness, health and association during a separate 2.5-second
   startup phase, then record an eight-second quiet baseline.
3. Recheck driver identity. Open one documented WLAN client and issue one
   `WlanScan` with null SSID/IE filters, recording the API's QPC brackets and status.
   Null filters mean no specific network name or extra information element.
4. Wait at most four seconds for completion on the selected interface, then
   observe an eight-second tail.
5. Close the WLAN client, stop the owned trace, drain the observer and compare
   complete live/offline timing records.

Execution outcome and instrument revisions are recorded in
[scan/TSF results](scan-tsf-results-2026-10-03.md). The current diagnostic revision
registers on the requesting WLAN handle and retains the eight-second tail even
after a four-second deadline miss. The miss remains a failure. It also keeps
bounded callback headers to distinguish absent, late and differently routed
notifications, without recording interface GUIDs or payloads in those headers.

Microsoft documents that `WlanScan` requests a scan, returns before completion,
uses ACM notifications for completion, and can increase network latency during
scanning. See [WlanScan](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlanscan).
The four-second notification limit is an experimental rejection bound, not an
assertion that every driver/API call must meet it. The synchronous API call and
cleanup/discovery operations add wall time outside that wait.

Stop the remaining trials on baseline timing/scan notifications, any failed API
status or deadline, duplicate/failure scan notifications, mismatched identity,
association/lifecycle invalidation, trace loss, unexpected private timing command,
more than 64 timing records in a trial, malformed/reordered records, live/offline
disagreement or cleanup failure. A scan access-denied result is a failed test,
not permission to change privacy settings or retry with another interface.

The separate observation gate has no private admission operation. Reports after
the scan boundary are retained as unassigned observations, not matched to a
private request. Reports timestamped before the actual scan call reject the
trial even if ETW delivers them after the phase transition. The original private
`ReportGate`, command allowlist and persistent quarantine are unchanged.

ACM completion notifications do not carry our transaction identifier. Even one
completion inside the request window is not a fully bound firmware response.
The saved trace must also be inspected for background/overlapping scan activity.
Positive repeated results establish the bounded observation pattern; absent
reports are a negative result for these trials, not proof that scans can never
produce reports. Quiet periods do not establish firmware drain.

## Implementation and validation

- `run_scan_comparison.py`: exact manifest/driver checks, one-call WLAN client,
  bounded observation gate, three-trial controller and offline assessment.
- `Invoke-PassiveObservation.ps1 -ScanComparison`: explicit experiment selection;
  the default remains passive-only.
- `tests/test_scan_comparison.py`: quiet-window interference, no private admission,
  record bounds, completion ambiguity/deadlines, false clock claims and ABI checks.
- `.gitattributes`: LF checkout for the two native source files whose hashes were
  qualified. Only CRLF conversion is undone; the resulting bytes match both the
  recorded source hashes and committed Git blobs. Binary files remain unchanged.

The manifest schema is `qualcomm-scan-comparison/v1`, with one to three remaining
`trials` and explicit `prior_scan_attempts`; their sum must not exceed three.
It also contains an explicit
interface index/GUID, unchanged quarantine SHA-256, and every script/native hash
in the runner's `PINNED_PATHS`. The manifest and capture contain private identities
and must stay in ignored artifacts. Preview is mandatory before elevation:

```powershell
python research/acquisition/run_scan_comparison.py --manifest '<private manifest>' --manifest-sha256 '<hash>'
# Elevated Windows PowerShell, after matching preview and independent review:
./research/acquisition/Invoke-PassiveObservation.ps1 -ScanComparison -ManifestPath '<private manifest>' -ManifestSha256 '<hash>' -PythonPath '<existing Python>'
```

No profiles, registers, driver installation, auto-report settings, device resets
or system clocks are changed. Failure retains the separate observation lock and
all capture evidence. Inspect the exact owned resources before a later manual
recovery decision; never clear the private quarantine to finish the matrix.

The current run does not qualify a ring getter, simultaneous hardware sampling,
hardware/QPC conversion, packet timestamps, UTC or synchronization accuracy.
Those require their own data-access and independent-reference evidence.

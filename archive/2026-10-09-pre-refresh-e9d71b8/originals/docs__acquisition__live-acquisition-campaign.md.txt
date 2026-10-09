# Guarded Qualcomm acquisition campaign

This runbook describes how a guarded campaign collects reports, rejects ambiguous results and cleans up its own tracing resources. The first completed campaign passed its collection checks; a later repeat was quarantined. The procedure preserves those limits and does not qualify accurate clock conversion or authorize another private run.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** The private campaign remains quarantined. The new QUTS client ownership finding does not establish firmware drain, report association or a new live acquisition. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

Admission means permission for one checked request. Quarantine blocks further requests after an uncertain result. ETW is Windows event tracing; ETL is its saved file. QPC is Windows' high-resolution host counter, and an IOCTL is a request sent to a driver. See the [glossary](../glossary.md) for related terms.

## Contents

- [Historical execution status](#historical-execution-status)
- [Prerequisites and bounds](#prerequisites-and-bounds)
- [Build and run](#build-and-run)
- [Live observation and admission](#live-observation-and-admission)
- [Cleanup and quarantine](#cleanup-and-quarantine)
- [Qualification limits](#qualification-limits)

**Current limit:** the [later private repeat](private-campaign-2026-10-03-quarantine.md) remains quarantined. The commands below document the guarded procedure; they do not authorize rearm.

Purpose: test bounded report collection on the exact Qualcomm FastConnect 7800 build. This is an opt-in hardware experiment, not a clock runtime.

## Historical execution status

The native observer compiled for ARM64 with `/W4 /WX`; the identity and local
elevated launch scripts passed PowerShell parser checks. The research test suite
passed 58 tests, including the exact-driver fixture and nine new gate/controller
tests. A private-probe preview confirmed the current qualified build without
opening the private device.

The first UAC launch returned Windows' "operation was canceled by the user"
error before the elevated launcher started. A user-authorized retry subsequently
completed: **12/12 captures, 138/138 private requests and both passive observer
checks passed**, with no quarantine. All 14 sessions were confirmed absent after
cleanup. See the [completed campaign results](acquisition-campaign-2026-10-02-results.md)
for measured latency, freshness, workload, cost and qualification limits.

A read-only prelaunch review found a child-admission race, trace ownership after
a fallible diagnostic write, and premature success reporting. Regression tests
reproduced those code paths and the fixes passed. The normal named-mutex handshake,
native observer and successful cleanup paths were exercised by the retry. No
forced timeout or ambiguous firmware delivery occurred; unit tests and this
successful run do not establish pending-I/O drain or arbitrary failure recovery.

## Prerequisites and bounds

- Windows ARM64, administrator context, Python 3.11+ and existing `pefile` dependency.
- Exact qualified driver hash, driver version 1.0.4374.1300, selected interface Up,
  qcwlan Running, stable interface GUID/PnP identity and connected AP.
- Build `artifacts/live_observer.exe` and `artifacts/decode_tsf_etl.exe` using
  native ARM64 MSVC/Windows SDK. The observer includes the existing decoder's
  numeric-only parser rather than implementing a second timing parser.
- No existing `artifacts/qualcomm-campaign-active-or-quarantined.json` marker.
  The controller never removes a prior failure marker or provides an override.
- Two passive observer start/stop checks, then three idle repetitions of each
  approved sequence (12 action-3 reads; 11 mixed action-3/action-4 requests).
  Only after all six idle captures pass are the same six workload captures run.
  Total planned private requests: 138, with one outstanding at a time.
- Minimum post-request spacing remains 250 ms for reads and 500 ms for mixed
  sequences. Real-time delivery, identity checks and admission can make it slower.
- Each trace is capped at 32 MiB with a one-second flush interval and QPC clock.
  Request-process/report deadline is 15 seconds including discovery/admission.
- Workload: one local process hashing a fixed 64 KiB buffer, nominal 10 ms compute
  / 10 ms sleep, stopped after each capture, with a 120-second hard duration limit.
  It generates no network traffic or application-data writes.

No reset, forced association, profile change, FTM, raw-register operation,
automatic TSF reporting or system-clock adjustment is included. Suspend/resume
and roaming are separate experiments, not qualified by this campaign.

## Build and run

From an ARM64 compiler environment, using the same SDK as the existing helpers:

```powershell
cl /nologo /W4 /WX research/acquisition/live_observer.c /Fo:artifacts/live_observer.obj /Fe:artifacts/live_observer.exe /link advapi32.lib wlanapi.lib iphlpapi.lib kernel32.lib
cl /nologo /W4 /WX research/tsf/decode_tsf_etl.c /Fo:artifacts/decode_tsf_etl.obj /Fe:artifacts/decode_tsf_etl.exe /link advapi32.lib kernel32.lib
```

Preview is read-only and opens no private device:

```powershell
python research/acquisition/run_acquisition_campaign.py --if-index <selected-index>
```

From an elevated shell, after confirming the exact target:

```powershell
python research/acquisition/run_acquisition_campaign.py --if-index <selected-index> --execute
```

Exit codes: 0 for completed preview/campaign, 1 for rejected execution, quarantine
or operational failure, 2 for CLI syntax errors. Elevation is not requested by
the reusable Python controller. The local launch helper may present Windows UAC.

## Live observation and admission

The native observer consumes the uniquely named real-time ETW session and registers
WLAN ACM/MSM notifications for the exact interface GUID. It queries current
connection state every 250 ms and checks the associated BSSID. Selected association,
disconnect and operational notifications invalidate the run; signal-quality
notifications alone do not. The controller also compares association across runs.
This does not provide a general Windows power-event subscription.

The private probe performs discovery and driver validation before marking itself
ready. The controller drains observed events, checks the live gate, then grants
one submission. A named mutex serializes grant/revocation with the probe's final
check and overlapped `DeviceIoControl` submission. Each child has a persistent
PID/state record: prepared, ready, permitted, submitted, drained or aborted.

On failure, unsubmitted permission is revoked. An already submitted request is
not forcibly killed; its process retains the buffers needed for cancellation/
completion drain. All failure paths retain the child PID and state when relevant.
The existing driver drain can block indefinitely, so a deadline is a campaign
stop policy, not a guarantee that the driver has completed or stopped RF activity.

One ordered command/report/SoC/delay group must match each admitted request, action,
vdev and host window. Duplicates, unsolicited groups, wrong order, lifecycle changes,
loss, cancellation and deadlines quarantine the campaign. There is no firmware
transaction ID: even accepted groups remain host-window-correlated experimental
observations, not proof of exact sampling or completion.

After trace shutdown, the offline ETL timing records must exactly equal the live
timing records. The existing evidence exporter then verifies loss, driver, target,
counts, actions, ordering and counter arithmetic. A per-run result stays pending
and unsuccessful until all post-capture validation passes.

## Cleanup and quarantine

Trace ownership is recorded before starting the unique session, so a failed
diagnostic write or uncertain start outcome still triggers an exact-session stop
attempt. Observer, workload and adapter endpoint checks run during cleanup.
Any uncertainty leaves the marker in place; restarting a process or trace is
never treated as proof that old firmware reports drained.

If the controller was externally interrupted, inspect the marker and the relevant
`session.json`. Stop only that session with `logman stop <SessionName> -ets`.
Inspect `submission-*.json` and `pending-probe.json` before deciding whether any
child is still draining. Do not kill a pending private-I/O process or remove the
marker merely to retry. Rearm requires an explicit reviewed recovery decision
and fresh qualification; this controller does not automate it.

Local output lives under `artifacts/QualcommCampaign-*`: live numeric records,
private association/identity snapshots, ETL, per-child submission records, raw
request results, normalized evidence, CPU/wall metrics and final status. Association
identifiers and all raw artifacts remain excluded from public Git.

CPU metrics cover the controller, observer and private-probe processes; probe
metrics exclude their PowerShell discovery children, and all exclude kernel/
logman overhead. Workload CPU and wall time are measured separately. These are
partial collection costs, not whole-machine impact or application-read latency.

## Qualification limits

Passive observer stop/start validates only successful collector lifecycle in the
tested conditions. Stale-data rejection currently has separate deterministic
lifecycle tests; a production collector/consumer expiry API is not implemented.
No capability is promoted automatically. A downstream record must distinguish
tested raw delivery, experimental host relationship, standard cross timestamps
and arbitrary packet timestamps. Independent-reference accuracy remains unqualified.

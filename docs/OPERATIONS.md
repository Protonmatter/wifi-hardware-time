# Operations

## Preconditions

Use a test system and exact interface targeting. Python tools target Python 3.11+. Only the static PE/protocol tools require `pefile`; it is the sole declared dependency. Native probes require Windows SDK headers/libraries and a compiler for the target architecture.

No tool installs a driver, changes a WLAN profile, changes a system clock, enables monitor mode, or sends FTM/ranging requests. The private TSF command requests a firmware action and may interact with internal timing state. It is not a production-qualified timing service.

## Offline checks

```powershell
python -m compileall -q tools tests
python -m unittest discover -s tests -v
```

To include the optional exact-binary fixture test, set `WIFI_TIME_DRIVER_FIXTURE` to a local SYS path, run the tests, then remove that environment variable. The fixture is read as data and never loaded. Keep it outside Git.

## Standard capability query

```powershell
Get-NetAdapter | Select-Object Name, ifIndex, InterfaceDescription, Status
python tools/probe_timestamp_caps.py --if-index 7
```

Choose the correct index. Output records API return codes and only interprets capability fields after successful calls. Exit 0 means queries completed; unsupported/error capability results are represented in JSON. This tool does not enable timestamping.

## Qualcomm private probe

First run without `--execute`:

```powershell
python tools/qualcomm_probe.py --if-index 7 --command get_hostdbglvl
```

The discovery helper resolves the active `qcwlan` service file and selected interface. The probe requires Up/Running state, expected filename/version, exact SHA-256, ARM64 architecture, and matching binary records. It does not accept an arbitrary driver fixture for live requests.

To perform one host-only query after reviewing the preview:

```powershell
python tools/qualcomm_probe.py --if-index 7 --command get_hostdbglvl --execute
```

The other host-only query is `get_hostdbgout`. The one-shot TSF command is `tsf_read_value`; its fixed positive argument selects firmware READ_VALUE action 3. Do not treat a successful request with an empty result as a TSF measurement.

Optional `--output` writes JSON to an existing local directory. Use ignored `local/` or `artifacts/`. Runtime discovery includes a MAC address internally; public probe output omits it. Do not publish raw discovery output or unsanitized logs.

The private handle is opened with read access and closed after the request. An overlapped request waits two seconds, then requests cancellation. It drains completion before releasing buffers. **If a defective driver never completes cancellation, that drain can wait indefinitely.** The two-second request wait is not a guaranteed process wall-time limit. Cancellation/disconnect behavior remains unqualified.

Exit 0 means preview completed or the request succeeded and the device handle closed. Exit 1/nonzero means a failed operation, invalid environment, or rejected qualification. There is no automatic retry, adapter reset, or remediation. For getters and one-shot READ_VALUE, no persistent setting rollback is expected; unexpected behavior should be investigated without automatic resets.

## Native probes

From an MSVC/Windows SDK developer PowerShell configured for the target architecture, compile into ignored `artifacts/`:

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
cl /nologo /W4 /WX tools/native_caps.c /Fo:artifacts/native_caps.obj /Fe:artifacts/native_caps.exe /link iphlpapi.lib kernel32.lib
if ($LASTEXITCODE -ne 0) { throw 'Native capability build failed' }
cl /nologo /W4 /WX tools/cached_beacon.c /Fo:artifacts/cached_beacon.obj /Fe:artifacts/cached_beacon.exe /link wlanapi.lib ole32.lib kernel32.lib
if ($LASTEXITCODE -ne 0) { throw 'Cached beacon build failed' }
cl /nologo /W4 /WX tools/decode_tsf_etl.c /Fo:artifacts/decode_tsf_etl.obj /Fe:artifacts/decode_tsf_etl.exe /link advapi32.lib kernel32.lib
if ($LASTEXITCODE -ne 0) { throw 'ETL decoder build failed' }
```

`native_caps` takes an interface index. `cached_beacon` takes an interface GUID and queries the existing cache only; it never calls WlanScan. The latter omits SSID/BSSID identifiers from its JSON, bounds-checks information elements, and reports FTM responder advertisement separately from execution.

## Trace and reference prerequisites

Firmware delivery/ordering qualification requires an appropriately privileged trace and correlation between request and report. No elevation is attempted by the public tools. The identified Qualcomm TraceClassic event keyword is `0x2000000000000000`; static event descriptors alone do not prove capture availability.

`tools/Capture-TsfReport.ps1 -InterfaceIndex 7` must be started from an elevated Windows PowerShell. Its default remains one read with a 4 MB trace. It validates the exact active driver through the existing probe before starting ETW. It waits 1.5 seconds after the final request and stops tracing in `finally`. The public wrapper is parser-checked only; its elevated execution remains unvalidated, despite one successful capture by the original local harness. The private probe's cancellation-drain limitation still applies.

## Capture and analyze a TSF series

Select the actual interface index; `7` below is an example. From an elevated shell:

```powershell
./tools/Capture-TsfReport.ps1 -InterfaceIndex 7 -SampleCount 12 -IncludeCapabilityChecks
```

- `SampleCount`: integer 1-12, default 1. Multiple reads use a 32 MB circular trace, separate `request-NNN.json` records, and at least 250 ms between probe processes. Each request revalidates the driver and adapter. The interval includes process/discovery time and is not a precision sampling schedule.
- `IncludeCapabilityChecks`: optional. Requires the compiled `artifacts/native_caps.exe` and `artifacts/cached_beacon.exe`; reads standard supported/active timestamp capabilities, independently repeats the queries through the native SDK probe, and queries cached BSS/device-service information. It does not scan or send FTM. The Python capability tool requests a cross-timestamp only when active capabilities advertise it. Individual API errors are recorded in output and are not evidence of absent capabilities.
- Outputs: a unique ignored `artifacts/WifiTime-...` directory with session metadata, preview, before/after adapter snapshots, request records, ETL, start/stop status, optional capability output, and `capture-error.json` on a caught failure.
- Exit 0: request collection and cleanup completed, with the selected adapter still Up on the original version/identity. It does not prove that all firmware reports arrived. Exit 1: prerequisite, request, cleanup, or final state check failed. Invalid parameters/elevation requirements also fail before collection.
- Rollback: the temporary trace is stopped in `finally`. If externally interrupted, run `logman stop <SessionName> -ets` as administrator using `session.json`. No driver restart, TSF reset, automatic reporting, profile change, or clock adjustment is requested.

After capture, decode and analyze offline without elevation:

```powershell
$run = 'artifacts/WifiTime-<actual-run-id>'
./artifacts/decode_tsf_etl.exe "$run/tsf.etl" |
    Set-Content -LiteralPath "$run/raw-timing.jsonl" -Encoding UTF8
if ($LASTEXITCODE -ne 0) { throw 'ETL decoding failed' }
python tools/analyze_tsf_series.py $run
if ($LASTEXITCODE -ne 0) { throw 'Incomplete or inconsistent series evidence' }
```

The decoder emits numeric-only timing records, trace clock/frequency/loss fields, and event counts. It never prints arbitrary event text, machine names, or diagnostic addresses. Exit codes: 0 for successful decoding, 1 for a trace API failure, 2 for invalid usage. A successful decode can contain no TSF records; analysis determines whether the required evidence exists.

The analyzer requires `session.json`, request files, and `raw-timing.jsonl`. It rejects missing planned samples, extra/missing timing records, mixed adapter/build evidence, overlapping request windows, mismatched vdev IDs, reported trace loss, and QPC frequency mismatches. It emits `analysis-series.json` with latency distributions, counter monotonicity, and raw ticks per host second. Exit 0 means evidence passed these consistency checks; nonzero means analysis failed. Check the exit code before consuming an output left from a previous analysis.

Correlation is limited to one command/report per request window, with no firmware transaction ID. ETW timestamps describe host logging. Counter rates are relative to host event time; counter discontinuities are reported rather than interpreted as calibrated oscillator rates. The output explicitly leaves exact firmware sampling and absolute accuracy unvalidated. Raw ETL and even numeric timing artifacts remain local unless separately reviewed for publication.

## Remaining hardware qualifications

Actual FTM tests require a reviewed submission/result API and a controlled responder. Timing accuracy requires an independent reference such as a qualified PHC or GPS/PPS source. A Windows host timestamp attached to a cached AP beacon is not a substitute for a calibrated local hardware clock.

## Data and publication

Keep vendor binaries, firmware, full disassembly, ETL files, packet captures, MACs/BSSIDs, interface GUIDs, device-instance identifiers, machine paths, and credentials out of commits. `.gitignore` is a convenience, not a confidentiality boundary: inspect the staged diff before publication. No distribution license has been selected for this initial repository.

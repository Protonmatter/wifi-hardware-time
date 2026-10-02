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

From a Windows SDK developer command prompt, compile `tools/native_caps.c` with `iphlpapi.lib` and `kernel32.lib`. Compile `tools/cached_beacon.c` with `wlanapi.lib`, `ole32.lib`, and `kernel32.lib`. Put outputs under ignored `artifacts/`.

`native_caps` takes an interface index. `cached_beacon` takes an interface GUID and queries the existing cache only; it never calls WlanScan. The latter omits SSID/BSSID identifiers from its JSON, bounds-checks information elements, and reports FTM responder advertisement separately from execution.

## Trace and reference prerequisites

Firmware delivery/ordering qualification requires an appropriately privileged trace and correlation between request and report. No elevation is attempted by the public tools. The identified Qualcomm TraceClassic event keyword is `0x2000000000000000`; static event descriptors alone do not prove capture availability.

`tools/Capture-TsfReport.ps1 -InterfaceIndex 7` must be started by the user from an elevated shell. It validates the target in preview mode, starts a unique temporary trace capped at 4 MB, sends one TSF read, waits 1.5 seconds, and stops tracing in `finally`. Its outputs go to ignored `artifacts/`. The public wrapper is parser-checked only; elevated capture remains unvalidated. If externally interrupted, use the session name in its `session.json` with `logman stop <SessionName> -ets`. The private probe's cancellation-drain limitation still applies.

Actual FTM tests require a reviewed submission/result API and a controlled responder. Timing accuracy requires an independent reference such as a qualified PHC or GPS/PPS source. A Windows host timestamp attached to a cached AP beacon is not a substitute for a calibrated local hardware clock.

## Data and publication

Keep vendor binaries, firmware, full disassembly, ETL files, packet captures, MACs/BSSIDs, interface GUIDs, device-instance identifiers, machine paths, and credentials out of commits. `.gitignore` is a convenience, not a confidentiality boundary: inspect the staged diff before publication. No distribution license has been selected for this initial repository.

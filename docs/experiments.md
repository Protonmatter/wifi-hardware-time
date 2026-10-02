# Exact-build Qualcomm latch and FTM experiments

These tools reproduce bounded research workflows. They are not stable public Windows APIs or production timing services. Source is under `experiments/qualcomm`; output belongs under ignored `artifacts/`.

## Preconditions and scope

Use a test system, Windows PowerShell 5.1 or later, Python 3.11+, the existing requirements, and an explicitly selected interface. The shared probe requires the selected adapter Up and its driver service Running, and pins ARM64 driver `qcwlanhmt8380.sys` version 1.0.4374.1300 to SHA-256:

`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`

Action 4 changes firmware capture state. Executed FTM sends ranging requests to the current associated AP. No experiment enables location permissions, resets TSF, enables automatic reporting, installs/restarts a driver, edits profiles, changes system clocks, or reads/writes arbitrary registers.

## Latch comparison

Preview action 4 without opening the private device:

```powershell
python tools/qualcomm_probe.py --if-index 7 --command tsf_read_value --tsf-action 4
```

The default action remains 3 / READ_VALUE. An explicit `--execute` sends the selected action. Only actions 3 and 4 are accepted, and action 4 is rejected for host getters. The exact action-selection instructions are checked in addition to the full driver hash.

To collect the fixed comparison sequence, run from an elevated shell:

```powershell
./experiments/qualcomm/Capture-LatchExperiment.ps1 -InterfaceIndex 7
```

Replace 7 with the intended interface index. The sequence is `3,3,4,3,3,4,3,3,4,3,3`, separated by at least 500 ms plus probe execution time. It caps the trace at 32 MB, revalidates each request, writes `artifacts/WifiLatch-...`, and stops tracing in `finally`.

Decode using the [native build instructions](OPERATIONS.md#native-probes), then analyze offline:

```powershell
$run = 'artifacts/WifiLatch-<actual-run-id>'
./artifacts/decode_tsf_etl.exe "$run/tsf.etl" |
    Set-Content -LiteralPath "$run/raw-timing.jsonl" -Encoding UTF8
if ($LASTEXITCODE -ne 0) { throw 'Decode failed' }
python experiments/qualcomm/analyze_latch.py $run
if ($LASTEXITCODE -ne 0) { throw 'Latch evidence is incomplete or inconsistent' }
```

The analyzer requires the complete fixed sequence, matching driver/interface identity, nonoverlapping successful requests, matching clocks, one report group per window, no reported trace loss, and correct low-word arithmetic. It writes `latch-analysis.json`. Refresh/cache observations are separate from simultaneity and accuracy, which remain explicitly false.

## FTM request and callback

The local investigation recovered `WlanInternalRequestFTM` and its consumer in `locationframework.dll`. The callback has a 104-byte target record; the request uses a 12-byte target. The FTM wrapper additionally requires these exact System32 files:

| File | SHA-256 |
|---|---|
| wlanapi.dll | 925f1c50e1c86d625aeb87e39a307e067a3e6f54eedbd8a598d64423203c234b |
| locationframework.dll | 1ab04f90fdd1b0b920e4cf0f50bdde41b2824804f4006eed7a532d83bfd108e0 |

The inspected wlanapi version is 10.0.26100.9278. Matching the WLAN driver alone does not qualify a different Windows DLL build.

In an MSVC developer PowerShell configured for native ARM64 with Windows SDK headers/libraries:

```powershell
New-Item -ItemType Directory -Force artifacts | Out-Null
cl /nologo /W4 /WX experiments/qualcomm/ftm_once.c /Fo:artifacts/ftm_once.obj /Fe:artifacts/ftm_once.exe /link wlanapi.lib iphlpapi.lib kernel32.lib
if ($LASTEXITCODE -ne 0) { throw 'FTM probe build failed' }
```

Use the wrapper, which enforces the DLL and driver hashes; do not use the native helper as an independently qualified API. From an elevated shell, first preview (no trace or FTM transmission):

```powershell
./experiments/qualcomm/Capture-FtmOnce.ps1 -InterfaceIndex 7
```

Then explicitly execute one request, or a bounded series:

```powershell
./experiments/qualcomm/Capture-FtmOnce.ps1 -InterfaceIndex 7 -Execute
./experiments/qualcomm/Capture-FtmOnce.ps1 -InterfaceIndex 7 -SampleCount 5 -Execute
```

`SampleCount` accepts 1-5, default 1. The native helper selects exactly one current associated cached BSS with an FTM responder advertisement; it does not call WlanScan. Each invocation reselects the current AP, so a series must not be interpreted as same-target if a roam occurred; compare the local response BSSIDs before combining samples. The wrapper revalidates the selected driver/interface before each request.

The helper waits five seconds, requests cancellation on timeout, and waits another two seconds for the callback. The cancellation and API/handle-close calls themselves have no proven wall-time bound. Callback resources remain alive until process exit. Separate local probes observed client-side canceled callbacks, but immediate firmware cessation and general cancellation recovery remain unqualified; see the [validation ledger](validation.md).

A nonzero API/callback/target status, missing result, zero measurement count, or response BSSID mismatch causes failure and stops the series. A live follow-up found that the driver can report success with zero measurements and RTT -1; matching status/BSSID alone is insufficient. The native helper and offline decoder now both reject that empty result while retaining signed RTT estimates when measurements exist. The native helper also requires explicit `--execute` and rejects non-ARM64 builds. Its raw 104-byte response includes a BSSID and must remain local.

The wrapper writes `artifacts/WifiFtm-...`: session/hash metadata, driver preview, request results, raw response files, trace start/stop status, final adapter snapshot, and a caught-error record when applicable. Trace size is capped at 8 MB. Decode a response offline:

```powershell
python experiments/qualcomm/decode_ftm_response.py artifacts/WifiFtm-<run-id>/response-local.bin
```

For a series, use `response-001.bin` through the actual last response. Each decode writes a distinct adjacent JSON file; `--output` overrides its path. The decoder omits BSSID/location data, retains signed RTT, and does not interpret measurement fields on failed target status. It rejects a successful status with zero measurements. RTT values and variance fields do not establish accuracy.

## Exit codes, cleanup, and limits

Both capture wrappers return 0 for completed preview/collection and 1 for failure. Invalid arguments/elevation requirements fail before live work. Python analyzers return 0 for internally consistent evidence and nonzero on failure; check exit codes before consuming any old output file. Native helper usage returns 2; failed prerequisites/results return 1.

Capture cleanup stops only the uniquely named trace. If externally interrupted, run `logman stop <SessionName> -ets` as administrator using `session.json`. There is no automatic adapter restart or reset. The inherited private IOCTL cancellation-drain limitation also applies to latch capture; see [operations](OPERATIONS.md).

## Observed results

- The public action-3 capture wrapper at `c960dcc` collected 12 matching reports over 14.39 seconds. TSF advanced, the reported SoC field stayed constant, and host-observed completion/logging order varied.
- A local 11-request action-3/action-4 experiment observed all three captures refresh the SoC field; subsequent reads reused the last captured value. This establishes cache/refresh behavior for that run, not simultaneous counter latching.
- Six same-target FTM requests produced firmware RTT responses, successful WDI completions, and successful callback results. An independent RF sniffer was not used.
- The initial reported RTT was 2.359 ns; five more were 3.694, 3.498, 3.042, -1.353, and 1.723 ns. Conditional on a rough AP distance estimate of about 1.83-1.98 m, the expected propagation RTT would be about 12.2-13.2 ns. These values do not pass that rough sanity check. No correction was fitted, and no independent clock reference or calibrated distance was available.

The signed RTT interpretation follows the installed Windows consumer and [WDI change history](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/wdi-doc-change-history); the documented RTT unit is [picoseconds](https://learn.microsoft.com/en-us/windows-hardware/drivers/netcx/wdi-tlv-rtt). A value represented in picoseconds is not evidence of picosecond accuracy.

The published `e7da355` wrappers have now been rerun elevated. The latch sequence reproduced its cache/refresh behavior. FTM status/BSSID checks passed for five callbacks, but the decoder found one zero-measurement result that those checks had incorrectly accepted. After adding the native measurement-count guard, another live run accepted three nonempty results and rejected the fourth, empty result, stopping the planned series and cleaning up its trace. Client-side cancellation was observed in two additional local probes, but immediate firmware/RF cessation and general recovery remain unqualified. One subsequent targeted adapter restart automatically reconnected the same saved profile; post-restart capture and a nonempty FTM result succeeded. No samples covered the restart gap. Exact firmware sampling/completion, simultaneous latching, independent-reference accuracy, safe register access, arbitrary packet timestamps, hardware power-cycle behavior, roaming, and behavior across driver updates remain unqualified. Raw evidence is not published.

# Passive observation and memory-log retrieval validation

One passive observation completed without clock reports or cleanup failures. Offline inspection also linked memory-log saving to device lifecycle paths and found a scan near earlier unmatched reports. Neither finding established a safe live log getter or accurate clock conversion, and the private campaign quarantine remained unchanged.

TSF is the Wi-Fi timing counter; SoC denotes the reported system-on-chip counter. A ring is a circular memory buffer that overwrites old entries. A getter is an interface for reading it. RVA means an address offset within the inspected driver image. See the [glossary](../glossary.md) for related terms.

## Contents

- [1. Completed live passive observation](#1-completed-live-passive-observation)
- [2. Memory-log retrieval: external consumers narrowed](#2-memory-log-retrieval-external-consumers-narrowed)
- [3. Stronger attribution lead: scanning overlaps the unmatched reports](#3-stronger-attribution-lead-scanning-overlaps-the-unmatched-reports)
- [4. Requested qualification status](#4-requested-qualification-status)
- [Reproduction and operational limits](#reproduction-and-operational-limits)

Later evidence: [controlled scans](scan-tsf-results-2026-10-03.md) reproduced the report pattern; [ring/RX boundary inspection](../memory-ring/timing-boundary-investigation-2026-10-03.md) narrowed diagnostic consumers. This dated report retains the scope of its original passive run.

The requested follow-up separates four questions: live collection, ring access,
report attribution, and clock accuracy. One elevated passive observation completed.
No private device was opened, no private request or scan request was submitted,
and the private campaign quarantine was not cleared.

Research starting revision: `a4d98a4ea388fee29339dcdce5699a2f5596ad2c` plus the
accompanying passive-runner and context-export changes. Exact source/binary hashes
are retained in the private launch manifest. All driver RVAs below refer to the
same qualified ARM64 SYS hash recorded in the
[memory-log investigation](../memory-ring/unmatched-tsf-and-memory-log.md).

## 1. Completed live passive observation

The elevated wrapper launched the maintained `run_passive_observation.py` with
an exact-source manifest, a 30-second wait limit and the previously qualified
native binaries. An unarmed `ReportGate` stops observation on unsolicited timing;
it cannot authorize a private request. The existing private quarantine stays in
place, and a separate exclusive passive lock prevents overlapping runner starts.
Each invocation requires a fresh capture subdirectory and launch receipt.

| Check | Observed result |
|---|---|
| Observation wait | 30 seconds; total controller interval including cleanup 31.061223 seconds |
| Private requests / explicit scan requests | 0 / 0 |
| TSF command/report/timer/delay records | 0 / 0 / 0 / 0 |
| Native controller-health records | 111, all successful queries and all three loss counters zero |
| Connection records | 111; connected with unchanged observed association |
| Final ETL records | 21,579 total; 21,577 selected-provider records; zero timing matches |
| ETL header loss | Zero events and buffers lost |
| Offline decoder | ProcessTrace 0; CloseTrace 0; live/offline timing records equal |
| Observer shutdown | Exit 0; tail drained; normal stop; no stop signal or forced termination |
| Trace absence check | Exact session query returned "Data Collector Set was not found", exit -2144337918 |
| Elevated wrapper | Exit 0; later PID check found no wrapper process |
| Final interface | Up; driver 1.0.4374.1300; same device identity and qualified driver hash |
| Private quarantine | Unchanged; passive lock removed after successful validation |

This is one successful passive execution of the repaired cleanup path. It does
not exercise live quarantine-on-report or stop-signal failure; those branches
retain offline regression coverage. Silence in one bounded window does not
establish firmware drain, automatic-reporting state or absence of other producers.

Local evidence directory: `artifacts/PassiveValidation-ee4404db9314`.

- Launch manifest SHA-256: `c91aa9c9578e2298ccef5a9528d6cb61e85300c7d148c1bc2449e71e0a238029`.
- Final ETL SHA-256: `37b37a287a319903659239e81382bf5bd615cc8315395e76eaa3e1bb40388fd8`.
- Result SHA-256: `9e6cee42335e8013385714f995d34c61550b403ff7eaff13e3db14cf79b79a4c`.
- Unchanged private quarantine SHA-256: `69303899d4614d707cd9d3c6b915922acd4e0e53404b505340df5c2eb1216610`.

These hashes identify local evidence; they do not authenticate third-party copies.
Raw logs, identity snapshots and binary artifacts remain outside public Git.

After the successful live run, an independent review reproduced a launcher-only
stderr defect: Windows PowerShell 5.1 could turn native stderr into a terminating
error and replace the child's exit code with 1. The maintained wrapper now uses
explicit process stdout/stderr redirection and reads the actual exit code.
`tests/Test-PassiveLauncher.ps1` tests stderr with exits 0, 1 and 2 without elevation,
tracing or adapter operations. This correction is offline-tested, not a second
live experiment. The original successful run had no stderr error and is unaffected.

The original executed wrapper is retained as a [historical text snapshot](../reproductions/2026-10-03-passive-launch/Invoke-PassiveObservation.ps1.txt),
recovered from the saved edit and verified against the acquisition manifest hash
`5875b8782861b166373d5f317e86e4c962d206c04be5fc1ff9e8144be1251c48`.
All other acquisition manifest pins remain unchanged. The old manifest correctly
rejects the updated wrapper; a later run requires a fresh manifest and directory.

## 2. Memory-log retrieval: external consumers narrowed

The two direct callers of `host_mem_log_dump` (`0x230a50`) lie inside:

| Routine | Function RVA | Call to file consumer |
|---|---:|---:|
| `MHISaveDumpFile` | `0x22e2a0` | `0x22e584` |
| `MHISaveMemLogFile` | `0x22e6b0` | `0x22e89c` |

Direct calls to `MHISaveMemLogFile` were resolved to:

- `WlanPciDrvEvtDeviceContextCleanup`, function `0x436fa0`, call `0x437034`.
- `WlanPciDrvEvtDeviceSelfManagedIoFlush`, function `0x4371f0`, call `0x43727c`.

These are device-lifecycle paths. They include additional operations before and
after the log save; they are not a private userspace ring-read request. The
general `MHISaveDumpFile` path also has other callers, whose complete external
reachability and side effects are not yet qualified. No claim of an exhaustive
call graph is made.

`MHISaveMemLogFile` constructs a directory using the on-disk `\SystemRoot\Temp`
string at `0x2a4f00`, then a timestamped `wlanhost...bin` filename using the format
at `0x2e8688`. A documented userspace filesystem enumeration of Windows Temp
succeeded and found zero `*wlan*` entries. Therefore no existing dump was available
to read or time. No device cleanup, flush, dump trigger, reset, or kernel memory
reader was invoked to manufacture one.

The concurrent-copy question remains unresolved at the caller boundary. The
previously inspected writer reserves space before copying; the copy routine
samples that reservation position. A permitted routine-level interleaving is:

1. Writer reserves a record and advances the position.
2. Copier reads that position and copies bytes not yet fully updated.
3. Writer finishes copying the record.

This is a static counterexample to assuming that the position alone denotes
committed records. It is not a measured live torn copy: caller synchronization
or writer quiescence could exclude the interleaving and must be established.
The newly identified lifecycle callbacks do not by themselves prove global
writer quiescence or a reusable polling contract.

**Result:** live ring contents, a safe live userspace getter, concurrent-copy
consistency and retrieval performance remain unvalidated. A completed dump file
would at most permit offline retrieval of that dump, not prove access to the
current ring or establish a clock sample.

## 3. Stronger attribution lead: scanning overlaps the unmatched reports

The existing failed capture was re-examined using 20 ms and 1000 ms context
windows. The exporter still has the same 32 MiB ETL, 100,000-event and message-size
bounds; only its permitted time window increased from 20 to 1000 ms.

Relative to the first unmatched report, the decoded context shows:

| Approximate log interval | Event |
|---|---|
| -28.668 to -28.621 ms | Six `WMI_VDEV_SET_IE_CMDID` messages |
| -28.605 ms | `WMI_START_SCAN_CMDID` |
| -28.599 ms | `WMI_RMV_BCN_FILTER_CMDID` |
| -0.004 ms | TSF WMI receive dispatch |
| 0 | First unmatched TSF report, with changed SoC value |
| +3.574 to +3.579 ms | Four scan callbacks logging STARTED / NONE |
| +511.403 ms | Second unmatched TSF report, again with changed SoC value |

The intervals here come from decoded event times, not firmware sampling times.
The one-second windows contain 4,926 events. No recognized
`WMI_VDEV_TSF_TSTAMP_ACTION_CMDID` appears in those windows. The command-name
search does not cover an unlogged or differently formatted command path.

The scan command is present in a transport-log message with the anchored shape
`wmi cmd endpoint[...]: buf ..., cmd WMI_START_SCAN_CMDID`. Scan-state callbacks
have the anchored `MP: StaHandleTaskScanEvent` prefix. This distinguishes those
messages from a command-like substring appearing inside an SSID or other payload.

This establishes temporal overlap with a specific scan command and scan-start
processing. It does not identify the initiating process or prove that the scan
caused either TSF event. A controlled quiet/scan/quiet comparison with preserved
request identity and complete trace health would distinguish that hypothesis
better than increasing private TSF request volume. No such scan was issued in
this pass, and no firmware action number is assigned to the extra reports.

## 4. Requested qualification status

| Requested claim | Status after this pass |
|---|---|
| Live collection and normal cleanup after the repair | One bounded passive run passed |
| Live ring contents / safe getter / copy consistency / performance | Not established; no qualified getter or existing dump, caller synchronization unknown |
| Unmatched-report initiator | Not identified; scan command/processing now directly observed nearby |
| Fresh simultaneous sampling | Not established by logs, changed counters, or the passive run |
| Hardware/QPC relationship | No qualified fresh bracket or tuple; regression remains insufficient |
| Calibrated accuracy / sub-millisecond synchronization | Not tested: no second controlled node or independent reference is available |
| Hosted CI for the previously uncommitted changes | Passed at `a4d98a4` on both push and PR events |

Hosted evidence: [PR run](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37106869208)
and [push run](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37106866214).
Those runs cover the offline changes at `a4d98a4`, not this later passive runner
until its own revision is pushed and checked. Hosted CI never qualifies hardware.

No downstream clock capability is promoted by this result. The private campaign
remains quarantined. The lack of an independent reference limits accuracy claims;
it does not prevent further interface and firmware-path research.

## Reproduction and operational limits

Use the maintained `run_passive_observation.py` and
`Invoke-PassiveObservation.ps1`, not an archived historical launcher. A manifest
under ignored artifacts must contain schema `qualcomm-passive-manifest/v1`, an
explicit interface index/GUID, 1..30 seconds, the unchanged private quarantine
hash, and hashes for every `PINNED_PATHS` entry. The runner also enforces the
four previously qualified native binary/source hashes. The actual manifest is
retained locally because it contains endpoint identity.

```powershell
python research/acquisition/run_passive_observation.py --manifest '<private manifest path>' --manifest-sha256 '<sha256>'
# In an elevated Windows PowerShell session, after the preview succeeds:
./research/acquisition/Invoke-PassiveObservation.ps1 -ManifestPath '<private manifest path>' -ManifestSha256 '<sha256>' -PythonPath '<existing Python executable>'

./research/acquisition/Export-TsfContext.ps1 -EtlPath artifacts/QualcommCampaign-0ca1b251e9b0/idle-read-3/tsf.etl -ReportOrdinals 10,11 -ContextMilliseconds 1000 -OutputPath artifacts/scan-context-new.json
python -m unittest discover -s tests -p test_passive_observation.py -v
./tests/Test-PassiveLauncher.ps1
```

The UAC launch used `Start-Process powershell.exe -Verb RunAs -WindowStyle Hidden`
with the maintained wrapper and manifest arguments. The wrapper preserves stdout,
stderr, an exclusive launch receipt and the process result. The runner saves
before/after identity, session, raw timing, full observer tail, cleanup and
assessment receipts. Exit 0 is a healthy passive observation (possibly stopped
on timing); exit 1 is rejection/failure; exit 2 is CLI usage. No result authorizes
private admission or claims firmware drain.

Cleanup stops only the owned ETW session and passive observer. On failure the
separate passive lock is retained for inspection, not automatically removed.
The private quarantine is never modified. Use a fresh directory for any later
run; duplicate invocation must not overwrite prior capture evidence.

Local final checks passed: Python compilation, 124 tests with the owned fixture,
parser validation of 19 PowerShell scripts, the existing FTM/NDIS helper
regressions, and the new native stderr/exit-code regression. Live evidence and
offline launcher correction remain separate validation scopes.

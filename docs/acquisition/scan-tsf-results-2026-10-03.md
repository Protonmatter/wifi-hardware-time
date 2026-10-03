# Scan-associated TSF reports and the completion deadline

Three controlled Wi-Fi scans reproduced extra clock reports without private timing requests. All three failed the declared four-second completion limit; only the last retained enough evidence to show completion around six seconds. The results challenge request ownership assumptions but do not establish fresh simultaneous samples, accurate clock conversion or permission to resume acquisition.

TSF is the Wi-Fi timing counter; SoC denotes the reported system-on-chip counter. QPC is Windows' high-resolution host counter. A scan API bracket measures the host call interval, while a completion notification reports later scan completion. See the [glossary](../glossary.md) for related terms.

## Contents

- [What ran](#what-ran)
- [Measured observations](#measured-observations)
- [Qualification consequence](#qualification-consequence)
- [Evidence and reproduction](#evidence-and-reproduction)
- [Implementation limits](#implementation-limits)

**Result: the report pattern was reproduced in three controlled scan invocations;
all three trials failed the predeclared four-second completion criterion.** The
third run retained a diagnostic tail and observed successful scan completion at
about six seconds. None of the failed trials is promoted as a successful capture
campaign or a qualified clock relationship.

Date: 2026-10-03, America/New_York. Source baseline `3e4fb37` plus the accompanying
working-tree qualification tools. Each execution has an exact-source manifest
and retained source snapshots in its private artifact directory. The selected
observer/decoder binaries remain the previously qualified binaries. The actual
driver remains ARM64 Qualcomm 1.0.4374.1300, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.

## What ran

Three documented `WlanScan` calls total, one per execution. There were no private
QcomWifi requests, adapter resets, register accesses, profile changes or clock
writes. Scanning itself changes transient radio activity and the discovery cache;
it is not described as a state-free query.

The first controller listened for completion through the separate observer's
WLAN client. After rejection and verified cleanup, the second registered on the
initiating WLAN handle. It also missed the deadline. The final revision retained
eight additional seconds of diagnostic observation after a deadline failure and
recorded bounded callback headers. Acceptance remained four seconds, and the
failure flag remained set. The original three-call budget was not increased.

These are three instrument revisions, not three identical passing repetitions.
The common initial quiet and post-scan report intervals are directly comparable;
the later observation windows differ. Source bytes for each revision were saved
and checked against its launch manifest before changing the harness.

## Measured observations

Intervals below are host QPC intervals. Report times are driver-log instants,
not firmware sampling instants. All traces use 10 MHz QPC.

| Run | Recorded quiet-start to scan-call interval | Scan API bracket | Report 1 after API start | Report 2 after API start | Own-client completion |
|---|---:|---:|---:|---:|---|
| A | 9.4453384 s | 4.9761 ms | 34.5265 ms | 529.6035 ms | Not collected on initiating client; none observed on separate client before stop |
| B | 9.0233252 s | 5.3236 ms | 34.3652 ms | 499.5305 ms | None in captured window |
| C | 8.9694962 s | 4.0226 ms | 34.4432 ms | 531.8515 ms | 6.0274774 s, after acceptance deadline |

Every capture contained:

- Zero TSF reports in the recorded quiet baseline.
- One anchored transport-log `WMI_START_SCAN_CMDID` message in the whole trace.
- Two report/SoC/delay groups after the scan call, with two distinct SoC values.
- Zero recognized private TSF action-command records.
- Successful WlanScan return, zero reported trace loss, exact live/offline timing
  parity, successful client/trace/observer cleanup and unchanged observed association.

Health/connection record counts were 59/59, 58/58 and 88/88. Native decoder event
counts were 17,155, 14,555 and 19,388. All decoder ProcessTrace/CloseTrace statuses
were zero. Final adapter identity, qualified driver hash and Up state were retained.

In run C, the driver logs COMPLETED/COMPLETED scan callbacks at approximately
6.0251-6.0253 s. The separate observer receives ACM scan_complete at 6.0268703 s,
and the initiating client receives it at 6.0274774 s. That directly establishes
late completion in this run, rather than merely a missing Python notification.
It also demonstrates that the separate observer can receive completion.
The early captures do not establish their later completion times, so no six-second
completion time is retrospectively assigned to A or B.

Microsoft documents asynchronous WlanScan completion and recommends registering
for ACM notifications and using a four-second wait. This adapter/run did not meet
that experimental bound. This is not a driver-certification or universal latency
conclusion. [WlanScan reference](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/nf-wlanapi-wlanscan).

## Qualification consequence

The operational scan-associated report pattern is now reproducible on this build.
An exclusive private-request producer assumption is not safe: ordinary scan
activity can coexist with TSF report traffic and changed SoC values even when
this harness submits no private TSF request.

This narrows the original unmatched-report investigation substantially. It does
not reconstruct the firmware's internal scheduling or provide a transaction ID
binding each raw report to a particular command. A changed SoC value is still
not proof of freshness or simultaneous TSF/SoC sampling. No hardware/QPC error
bound or time-transfer capability is enabled by these results.

The four-second experiment remains failed. A future longer completion window
must be declared before another run and tested separately. It must not be used
to relabel these records as passing. Repeated scans are also not proposed as a
low-latency application timestamp API.

## Evidence and reproduction

| Run | Local directory | Final ETL SHA-256 |
|---|---|---|
| A | `artifacts/ScanComparison-23a60ef0453f` | `88f3b4739debf7f5436ab164ad23f5b4db104d8f9d2c3a52ef651e6316856472` |
| B | `artifacts/ScanComparison-132079dfd737` | `73f4c4881b76db6ceca4e320c42885fead6859eca67a0a4bdd80744d57482ab3` |
| C | `artifacts/ScanComparison-78e8a0136769` | `491568e41c52dd525cb82cabb23d482932dffdebc7d21ec0416137693421b0b0` |

Each directory retains `manifest.json`, launch/process receipts, `capture/trial-1`
with before/after adapter state, scan request, timing records, full observer tail,
cleanup and result. B/C include initiating-client notification records; C includes
bounded non-payload callback headers. `acquisition-sources/` contains the exact
nonbinary source bytes matched to that run's manifest. Data and historical local
sources remain ignored; the maintained harness and analysis tools are reusable.

```powershell
python research/acquisition/analyze_scan_comparison.py --capture artifacts/ScanComparison-23a60ef0453f/capture/trial-1 artifacts/ScanComparison-132079dfd737/capture/trial-1 artifacts/ScanComparison-78e8a0136769/capture/trial-1 --output artifacts/scan-comparison-postmortem-new.json
./research/acquisition/Export-TsfContext.ps1 -EtlPath '<saved trial>/tsf.etl' -ReportOrdinals 1,2 -ContextMilliseconds 1000 -OutputPath '<fresh private output>.json'
python -m unittest discover -s tests -p test_scan_comparison.py -v
python -m unittest discover -s tests -p test_scan_postmortem.py -v
./tests/Test-ScanContextSummary.ps1
```

The context exporter now reports whole-trace anchored scan-command and callback
summaries in addition to selected raw context. Command-like text inside an SSID
does not match those anchored log formats. Raw context remains private.

The postmortem verifies complete trace parity/health and exposes relative intervals
while retaining `controller_success=false` and `clock_qualified=false`. Missing
completion evidence remains null, not zero. It does not modify either lock.

The private quarantine marker retains SHA-256
`69303899d4614d707cd9d3c6b915922acd4e0e53404b505340df5c2eb1216610`.
The final failed observation lock is also retained. Earlier observation locks
were archived and manually released only after checking exact owned-session
absence, wrapper exit, successful client/observer cleanup and unchanged private
quarantine. No active trace or observer is intended to remain; the final exact
session absence and wrapper-exit checks succeeded.

## Implementation limits

The two native C sources now have explicit LF checkout attributes. Their restored
bytes match both the recorded qualification hashes and committed Git blobs; no
native code or binary was changed to bypass the preflight.

The scan callback is registered on the requesting handle, deregistered before
handle close, and retained in memory until the bounded process exits. Observation
and requesting-client notifications are checked independently for conflicts. The
callback-header cap is 256; timing-record cap is 64 per trial. The controller
stops further calls after a failed trial. Its three-call limit is a trusted-manifest
declaration with preserved prior receipts, not a machine-wide scan quota.

At acquisition and report review, these qualification changes were uncommitted
and had no hosted-CI result. Any later CI result must be checked against its exact
published revision; the merged baselines do not validate this follow-up.

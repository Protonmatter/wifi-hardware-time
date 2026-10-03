# Qualcomm guarded acquisition: completed idle/workload campaign

Campaign `QualcommCampaign-ecfaed68f20e` completed successfully on 2026-10-02
local time, 2026-10-03 00:23:19–00:34:20 UTC. This supersedes the earlier canceled
elevation attempt for execution status. The launcher returned exit 0.

## Scope and outcome

| Phase | Runs | Accepted private requests |
|---|---:|---:|
| Idle READ_VALUE | 3 | 36/36 |
| Idle mixed READ_VALUE/QTIMER_CAPTURE | 3 | 33/33 |
| Local-workload READ_VALUE | 3 | 36/36 |
| Local-workload mixed sequence | 3 | 33/33 |
| Total | 12 | 138/138 |

Two passive observer start/stop checks also passed before the private requests.
All 14 uniquely named ETW sessions were subsequently confirmed absent by exact
session queries. All 138 child submission records reached `drained` without an
abort request; request results reported success and handle closure. Live timing
records exactly matched offline ETL decoding in every capture, with zero
trace-reported lost events/buffers. No invalidating WLAN notification or association
change was observed by the configured observer. No campaign quarantine occurred.

The final adapter remained Up on version 1.0.4374.1300, qcwlan Running. The full
driver hash remained `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
All eight source/binary hashes recorded in the prelaunch readiness receipt were
unchanged during execution. No reset, profile modification, FTM, raw-register
operation or system-clock adjustment was requested.

The standalone `userspace-clock` validator accepted all 12 exported bundles and
138 observations while retaining `conversion_qualified: false` and
`utc_qualified: false`. Raw ETL, adapter/AP identifiers and numeric acquisition
files remain local and ignored. This report is an aggregate summary, not the
raw evidence package or a published immutable qualification revision.

## Measured latency and cadence

Each phase contains 69 observations. Percentiles use nearest rank; the small
sample count and sequential test order do not support a statistical causality
claim about workload effects.

| Metric | Idle median / p95 / max | Workload median / p95 / max |
|---|---|---|
| Userspace request-start to completion observation | 53.5 / 108.0 / 150.7 microseconds | 54.1 / 110.2 / 468.9 microseconds |
| Request-start to driver report log | 270.3 / 700.4 / 869.0 microseconds | 262.8 / 739.5 / 1047.7 microseconds |
| Driver report log to observer-reader receipt | 1649.33 / 1890.53 / 2833.67 milliseconds | 1606.55 / 1838.80 / 2546.37 milliseconds |
| Actual inter-request start interval | 4.045 / 4.272 / 4.940 seconds | 4.027 / 4.188 / 5.242 seconds |

The controller preserved the original sample limits and minimum post-request
spacing (250 ms read, 500 ms mixed), but live admission, discovery and ETW delivery
made actual sampling slower. The campaign is not a same-cadence performance
comparison against the older unguarded wrappers.

All 138 report logs occurred after observed IOCTL completion in this campaign.
Earlier captures contained a different ordering, so this is not a universal
ordering guarantee. Request/report-log intervals are host observations, not exact
firmware sampling or execution times.

**The practical limitation is delivery latency.** The current ETW collection path
delivered four reports more than two seconds after their log timestamp. It must
not sit in an application's fast timestamp-read path. A background observer can
preserve the original report timestamp and explicit observation age; receipt time
must not masquerade as hardware sample time. Delivery delay here includes the
configured real-time trace path and process scheduling; it is not attributed to
the NIC alone.

## Freshness and relative rate

- All 18 action-4 capture requests changed the reported SoC value relative to the
  preceding observation.
- All 108 eligible action-3 adjacent comparisons reused the preceding SoC value.
  The first observation of each run is excluded from this comparison.
- TSF increased within each admitted capture. The endpoint TSF rate relative to
  host report-log QPC ranged from 999952.57 to 999961.70 raw ticks/host second
  at idle, and 999947.71 to 999955.50 under workload.
- These are relative observations, not a calibrated oscillator-frequency or
  timing-accuracy claim. No phase continuity between captures is assumed.

The stale-observation policy was separately exercised with one completed capture
and the current live QPC: the last observation was about 236.23 seconds old and
was rejected by an explicit two-second test policy. It was admissible immediately
after its report time. This verifies the offline lifecycle policy with actual
aged data, not a production expiry API or a consumer-approved freshness SLA.

## Workload and collection cost

The workload was one process hashing a fixed 64 KiB buffer, nominal 10 ms work /
10 ms sleep. Each workload process stopped on controller request before the
120-second bound. Measured CPU usage was 48.96–49.48% of one CPU core during its
active interval. It generated no network traffic.

| Measured process CPU time | Six idle captures | Six workload captures |
|---|---:|---:|
| Controller | 12.703 s | 12.828 s |
| Native observer | 0.703 s | 0.813 s |
| Private-probe processes | 13.828 s | 14.344 s |
| Capture wall time, summed | 319.427 s | 324.558 s |

These are partial collection costs. Probe-created PowerShell discovery children,
kernel work and logman are excluded. They do not quantify total system overhead,
power impact or application timestamp latency.

## Qualification and remaining gates

This campaign establishes repeatable raw-report acquisition and successful
collector lifecycle for this exact build, tested association, two sequences,
cadence and workload. The normal submission handshake and successful shutdown
paths were exercised live. No timeout, ambiguous group or invalidating lifecycle
event naturally occurred; live failure/quarantine and pending-I/O drain behavior
therefore remain covered by code review/tests, not a forced hardware fault test.

After the campaign, the SDK helper still returned 23 for both supported and active
standard timestamp capabilities. Standard cross-timestamp support remains unknown.
No arbitrary hardware packet timestamp interface was established.

Exact firmware sampling/completion instants, simultaneous TSF/SoC latching,
independent-reference accuracy, suspend/resume, forced reassociation/roaming,
reset failure paths and a production consumer/provider runtime remain unqualified.
No downstream clock conversion or OS discipline capability is enabled by this result.

See the [campaign runbook](live-acquisition-campaign.md) for the fixed sequences,
admission protocol, stop criteria and cleanup behavior.

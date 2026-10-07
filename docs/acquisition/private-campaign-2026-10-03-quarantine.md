# Private campaign: stopped on unmatched TSF reports

The private campaign stopped when extra clock reports could not be matched to its requests. Two captures passed, but the third was rejected and the remaining work did not run. Cleanup checks confirmed resource termination; they did not establish report ownership or firmware drain. The quarantine intentionally blocks another campaign.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** The private campaign remains quarantined. The new QUTS client ownership finding does not establish firmware drain, report association or a new live acquisition. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

TSF is the Wi-Fi timing counter; SoC denotes the reported system-on-chip counter. An IOCTL is a driver request. Quarantine means further private requests are blocked until the ambiguity is resolved through reviewed recovery. See the [glossary](../glossary.md) for related terms.

## Contents

- [Outcome](#outcome)
- [Why the gate stopped](#why-the-gate-stopped)
- [Cleanup and evidence limits](#cleanup-and-evidence-limits)
- [Latency in the two completed captures](#latency-in-the-two-completed-captures)
- [Local artifacts and next step](#local-artifacts-and-next-step)

Result: **quarantined; full campaign did not pass**. Run date: 2026-10-03
America/New_York. Starting source revision:
`85cd217d6c413852c3d039643dc297b39ba35bf2`.

The user authorized the existing private campaign after the corrected observer's
[passive qualification](observer-passive-qualification-2026-10-03.md). Source,
gate, controller and selected binary hashes matched that qualification, Wi-Fi was
Up on the exact driver, and no campaign/quarantine marker existed at launch.
The relevant 11 campaign unit tests passed before execution.

The planned matrix was six idle and six local-CPU-workload captures: three
repetitions each of the existing 12-read and 11-operation mixed sequences,
138 total requests, preserving the existing minimum spacing and admission rules.
No FTM, automatic reporting, register access, reset, network workload or clock
write was included. No source or gate change occurred during execution.

## Outcome

| Stage | Outcome |
|---|---|
| Two initial passive preflights | Passed |
| idle-read-1 | Passed, 12 requests and 12 qualified bundle observations |
| idle-read-2 | Passed, 12 requests and 12 qualified bundle observations |
| idle-read-3 | Nine requests admitted, then unmatched report detected; entire capture rejected |
| Remaining idle mixed/workload captures | Not run |
| Total issued/completed private IOCTLs | 33, all action 3, successful with handles closed |
| Qualified complete bundles | 2, containing 24 observations |
| Campaign process exit | 1 |
| Persistent quarantine | Retained; no automatic rearm or retry |

Nine observations admitted before failure in the third capture are **not promoted
as a qualified partial bundle**. A valid IOCTL completion is separate from a valid
firmware report association.

## Why the gate stopped

During the third capture the gate encountered a report while expecting a command
record and raised `unsolicited_duplicate_or_out_of_order_record`. Offline decode
of the finalized ETL found:

- Nine recognized action-3 command records.
- Eleven report records, eleven SoC/global-TSF records and eleven delay records.
- Two extra report/timer/delay groups after the ninth normal group, with no
  matching recognized command in this captured interval.
- Zero header-reported event or buffer loss; successful full ProcessTrace and
  CloseTrace. A broader saved-log text search found no additional action-bearing
  TSF command record outside the numeric decoder's recognized set.

The extra groups have distinct values. Their source is not established: the
evidence does not distinguish another initiator, automatic firmware activity,
an earlier operation, or another report-producing path. Do not assign either
group to the next request or claim firmware drain from this trace.

The next probe, number 10 in that capture, was revoked in pre-submission admission.
Its state is `aborted` with `abort_requested=true`; no request receipt or command
record exists for it. Its later process error occurred while opening the already
closed admission mutex, before the code reaches `CreateFileW` for the private
device. It exited without forced termination and did not submit a tenth IOCTL.

## Cleanup and evidence limits

The campaign's five created sessions (two passive, three active) were each queried
afterward and reported not found, not access denied. No observer, campaign wrapper
or revoked probe process remained. All 33 submitted request receipts report
successful completion and closed handles. Final Wi-Fi state remained Up on
driver 1.0.4374.1300; source/driver validation remained exact-build.

The failed capture's live JSON log stops early after quarantine because cleanup
pumping encounters the already quarantined gate. Consequently the final native
`observer_stopped` record is not retained for that capture. Do not claim its
normal native stop return code from that incomplete log. Independent checks
confirm process/session termination, and the finalized ETL retains all 42 decoded
timing records. A future controller improvement should drain/persist evidence
after rejection without ever reopening admission.

The `pending-probe.json` snapshot correctly records that the revoked child was
still running when quarantine began; subsequent process checks establish it has
exited. Retain both observations rather than overwriting the original snapshot.

## Latency in the two completed captures

| Median | idle-read-1 | idle-read-2 |
|---|---:|---:|
| Host-observed IOCTL bracket | 56.25 us | 53.00 us |
| Request start to driver report log | 248.15 us | 240.65 us |
| Driver report log to Python reader | 1657.78 ms | 1691.98 ms |

These values describe only the two completed idle read captures. The health fix
did not remove the observed long delivery delay in those captures; this is not a
controlled performance comparison or an accuracy measurement. Mixed-action SoC
refresh and the defined CPU-workload phase were not exercised in this campaign.

## Local artifacts and next step

- Campaign: `artifacts/QualcommCampaign-0ca1b251e9b0`.
- Launch and readiness receipt: `artifacts/PrivateCampaignLaunch-f82642d1695b`.
- Failed ETL SHA-256: `0b0b3a7b2b5f4b805b8deaccbc7870361422648edc1660b81537b36791ce3dff`.
- Selected observer SHA-256: `afc40361b7037213cf3315a1765205f65bc1e90ebabefb5293796b42e7e3e134`.

Raw traces, report values, association identities and local paths remain ignored.
The persistent `artifacts/qualcomm-campaign-active-or-quarantined.json` marker
intentionally blocks another campaign. Investigate the unmatched-report producer
and preserve complete post-rejection evidence before any explicit rearm decision.
Do not weaken the association gate or clear the marker simply to finish the matrix.

This is useful live evidence that the association guard stops an ambiguous stream;
it is not a successful 138-request repeat or a clock qualification. No commit or
push was performed as part of this execution.

# Findings, validation scripts and execution catalog

This catalog connects the findings to maintained tools, retained historical
sources, and recorded execution. It does not label every retained script as run
or every successful process as a qualified hardware capability.

Current operational state: the [private campaign quarantined](qualification/private-campaign-2026-10-03-quarantine.md)
after 33 action-3 requests. Two complete bundles contain 24 observations. Nine
additional admitted observations belong to the rejected capture. No retry,
automatic rearm, private request or new live trace occurred during this follow-up.

## Maintained entry points and recorded scope

Paths below are relative to the repository root. Follow each tool's documented
permissions, exact-build prerequisites and explicit execution switches.

| Work | Maintained scripts / source | Recorded result and limitation |
|---|---|---|
| Adapter/build discovery and protocol guards | `tools/Get-QualcommAdapter.ps1`, `tools/qualcomm_protocol.py`, `tools/qualcomm_probe.py` | Exact build and command validation; preview differs from explicit private execution |
| TSF series capture and decode | `tools/Capture-TsfReport.ps1`, `tools/decode_tsf_etl.c`, `tools/analyze_tsf_series.py` | Repeated private reads; command completion is not sampling time |
| TSF/SoC latch experiment | `experiments/qualcomm/Capture-LatchExperiment.ps1`, `experiments/qualcomm/analyze_latch.py` | Action-dependent refresh/cache observations; no simultaneous-latch proof |
| FTM request, callback and aggregation | `experiments/qualcomm/ftm_once.c`, `experiments/qualcomm/Capture-FtmOnce.ps1`, `experiments/qualcomm/decode_ftm_response.py`, `experiments/qualcomm/model_ftm_selection.py` | Specialized ranging/callback execution and saved aggregation replay; no absolute four-event export |
| FTM delta extraction | `experiments/qualcomm/Export-FtmDeltaEvents.ps1`, `experiments/qualcomm/FtmDeltaLog.ps1`, `experiments/qualcomm/analyze_ftm_deltas.py` | 51 saved triplets reproduce signed subtraction; malformed target messages reject |
| Guarded campaign | `experiments/qualcomm/run_acquisition_campaign.py`, `experiments/qualcomm/live_observer.c`, `experiments/qualcomm/campaign_gate.py`, `experiments/qualcomm/Get-CampaignIdentity.ps1`, `tools/campaign_admission.py` | Earlier 138-request campaign completed; corrected-observer repeat quarantined as recorded separately |
| Passive observer validation | Existing `capture(..., actions=[], smoke=True)` controller path; retained qualification runner below | Two corrected-observer passes succeeded with zero private requests |
| Standard timestamp/device-service probes | `tools/probe_timestamp_caps.py`, `tools/native_caps.c`, `tools/device_services.c`, `tools/cached_beacon.c` | API outcomes and exact ABI checks; cache and capability errors do not establish hardware absence |
| Refined NDIS experiment | `experiments/qualcomm/Build-NdisExperiment.ps1`, `experiments/qualcomm/ndis_query_probe.c`, `experiments/qualcomm/ndis_trace_health.c`, `experiments/qualcomm/Capture-NdisTimestampStatusV2.ps1`, `experiments/qualcomm/NdisV2Health.ps1`, `experiments/qualcomm/Export-NdisNamedEvents.ps1`, `experiments/qualcomm/ndis_evidence.py`, `experiments/qualcomm/analyze_ndis_run.py` | Three bracketed queries, same-run topology and full health; interface activities do not bind application requests |
| Evidence export/lifecycle | `tools/export_clock_evidence.py`, `tools/validate_research_bundle.py`, `tools/observation_lifecycle.py` | Strict offline admission/fixtures; no automatic clock conversion |
| Clock-model investigation | `experiments/qualcomm/analyze_observation_quality.py`, `experiments/qualcomm/analyze_clock_pairing_hypothesis.py` | Conditional/held-out models; residual and feasibility are not calibrated uncertainty |
| Quarantine postmortem | `experiments/qualcomm/analyze_quarantined_tsf.py`, `experiments/qualcomm/Export-TsfContext.ps1` | New maintained offline tools, actually replayed on the failed capture in this follow-up |
| Cancellation/restart tests | Historical cancellation/reset sources in archive below | Prior bounded experiments only; not current live entry points or general reset/drain qualification |

The [operations guide](OPERATIONS.md), [experiment guide](experiments.md), and
individual qualification reports give command syntax, build/runtime requirements,
source revisions and limits. Native probes require their own build; CI's compile
or help checks are not live execution evidence.

## Retained local harnesses

The [source archive](reproductions/2026-10-03/README.md) contains all 36 authored
`.py`, `.ps1` and `.c` files retained in the inspected local artifact/current-WLAN
evidence directories. Its [manifest](reproductions/2026-10-03/manifest.json) lists
every file, original SHA-256, archived SHA-256, redaction and normalization.
The one third-party reference source is explicitly excluded.

This covers historical private getters, early latch/FTM variants, cancellation
and reconnect helpers, topology inspection, campaign summaries and launchers,
as well as the exact retained passive runner. Some copies predate current safety
or result guards. They are source evidence stored as `.txt`, not executable tools.
Raw driver files, logs, callback bytes, interface/profile snapshots and identities
remain local. Hashes do not authenticate artifacts or prove execution.

In particular, the passive qualification's `qualify_passive.py` and private
campaign's `run-elevated.ps1` are archived separately from their local manifests.
The passive launcher copy has local paths replaced by placeholders. Its original
hash is retained, but it is not a byte-identical executable replacement.

## Commands actually used in this follow-up

The new offline tools were run against the existing failed capture; no new
capture was started. The following is the repeatable command recipe. Use new
output names because outputs are exclusive:

```powershell
$capture = 'artifacts/QualcommCampaign-0ca1b251e9b0/idle-read-3'
./artifacts/decode_tsf_etl.exe "$capture/tsf.etl" | Set-Content "$capture/quarantine-offline-new.jsonl" -Encoding UTF8
python experiments/qualcomm/analyze_quarantined_tsf.py --capture $capture --timing "$capture/quarantine-offline-new.jsonl" --output "$capture/postmortem-new.json"
./experiments/qualcomm/Export-TsfContext.ps1 -EtlPath "$capture/tsf.etl" -ReportOrdinals 10,11 -ContextMilliseconds 2 -OutputPath "$capture/unmatched-context-new.json"
python -m unittest discover -s tests -p test_observer_drain.py -v
python -m unittest discover -s tests -p test_quarantined_tsf.py -v
python -m unittest discover -s tests -p test_validation_archive.py -v
```

The original decode/context/count checks had been executed as interactive shell
and Python cells. The promoted analyzer/exporter reproduce their bounded core
operations and add validation; they are not claimed to be the original source
files. Interactive build, UAC launch, hash and cleanup commands are reconstructed
in the corresponding experiment reports, with original launch receipts local.

Final local checks for this follow-up passed: `python -m compileall -q tools
experiments tests`, all 110 Python unit tests (including the locally owned exact
driver fixture), and parser validation of all 17 maintained PowerShell scripts.
The following offline PowerShell regressions also passed:

```powershell
./tests/Test-FtmDeltaLogParser.ps1
./tests/Test-NdisCaptureHelpers.ps1
./tests/Test-NdisCaptureHelpers.ps1 -CaptureScript ./experiments/qualcomm/Capture-NdisTimestampStatusV2.ps1
./tests/Test-NdisV2Preflight.ps1
./tests/Test-NdisV2Health.ps1
```

These helper tests perform no trace or adapter operation. The fixture path and
raw replay outputs stay local. Hosted checks are reported separately by GitHub
Actions on the corresponding pushed revision.

## Continued findings

The replay confirms nine complete command/report groups and two unassigned
report/timer/delay groups. The two extra reports each have a preceding
`wmi_control_rx` dispatch message for the TSF report event in the saved context.
This supports two separately delivered event groups; it does not identify their
initiator or prove that the two groups belong to any particular request.

The controller cleanup defect was reproduced offline: an already quarantined
gate caused `Observer.close()` to stop consuming the remaining output. The fix
retains the original quarantine, drains records without passing them into
admission, preserves malformed lines as private diagnostic evidence, and writes
`observer-cleanup.json` independently of acquisition qualification. New errors
discovered while closing still fail, but do not discard the rest of the tail.

Seven synthetic cleanup tests cover existing/new quarantine, malformed records,
malformed stop messages, inconsistent stop status, failed stop signaling and
forced observer termination. A failed stop signal retains the first error while
still performing bounded passive-observer shutdown. This code has not been
live-qualified since the fix, and it cannot recover the original in-memory
queue after the old controller exited. No previously missing stop record is
fabricated. Private IOCTL lifetime handling and the persistent quarantine marker
are unchanged.

## Publication and validation boundary

Archive verification tests check hash integrity, LF normalization and non-entrypoint
containment without running the archived scripts. Normal CI tests only maintained
code and synthetic fixtures. Hardware results remain the separately recorded
experiments; a successful replay or CI run does not requalify the rejected capture.

The campaign remains quarantined. A new readiness receipt and explicit rearm
decision are required before another live campaign, because the controller source
has changed and the unmatched-report producer remains unresolved.

## Findings index

- [Proposed hardware-time boundary](api-direction.md)
- [ALFA AWUS036AXML / MT7921AUN](axml.md)
- [Clock evidence contract v1](evidence-contract.md)
- [Exact-build Qualcomm latch and FTM experiments](experiments.md)
- [FTM aggregation and TSF delivery: exact-build follow-up](ftm-result-provenance.md)
- [Operations](OPERATIONS.md)
- [Packet-to-clock timestamp map and uncertainty ledger](packet-to-clock-map.md)
- [Qualcomm FastConnect 7800 Windows research](qualcomm.md)
- [Qualcomm guarded acquisition: completed idle/workload campaign](qualification/acquisition-campaign-2026-10-02-results.md)
- [Stronger timestamp paths and equipment gates](qualification/backend-and-reference-next-steps.md)
- [Qualifying the TSF, FTM and host-clock relationships](qualification/clock-relationship-investigation.md)
- [TSF versus SoC: what the reported increments can identify](qualification/counter-rate-identifiability.md)
- [FTM buffer, notification and TSF routing: exact-build static follow-up](qualification/ftm-notification-routing.md)
- [Access to pre-aggregation FTM records: offline follow-up](qualification/ftm-raw-access-followup.md)
- [Conservative observation lifecycle](qualification/lifecycle-matrix.md)
- [Guarded Qualcomm acquisition campaign](qualification/live-acquisition-campaign.md)
- [Refined NDIS experiment and capability qualification](qualification/ndis-refined-experiment.md)
- [NDIS rejection-origin analysis](qualification/ndis-rejection-origin-analysis.md)
- [Bounded live NDIS status capture](qualification/ndis-status-capture-2026-10-03.md)
- [Observing timestamp OID status through existing NDIS events](qualification/ndis-status-observation-path.md)
- [Corrected observer: passive live qualification](qualification/observer-passive-qualification-2026-10-03.md)
- [Private acquisition latency: measured stages and the next bounded experiment](qualification/private-acquisition-latency.md)
- [Private campaign: stopped on unmatched TSF reports](qualification/private-campaign-2026-10-03-quarantine.md)
- [Private timing acquisition: practical research direction](qualification/private-timing-acquisition-plan.md)
- [Private TSF returns, automatic reporting and TX-completion timing](qualification/private-tsf-fast-paths.md)
- [Offline observation quality: first downstream work package](qualification/qualcomm-observation-matrix.md)
- [Research delivery: evidence contract, lifecycle and predictive checks](qualification/research-delivery-2026-10-02.md)
- [Windows timestamp path follow-up](qualification/windows-timestamp-path-followup.md)
- [Sources and provenance](sources.md)
- [Research-to-Userspace-Clock Implementation Plan](superpowers/plans/2026-10-02-research-to-userspace-clock.md)
- [Validation ledger](validation.md)

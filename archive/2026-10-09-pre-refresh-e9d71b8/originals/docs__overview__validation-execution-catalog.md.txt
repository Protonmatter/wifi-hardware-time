# Findings, validation scripts and execution catalog

Use this catalog to connect a research finding with the tool that produced or analyzed it. It distinguishes maintained commands from historical source snapshots and records what actually ran. A retained script, successful process or passing software test is not automatically evidence of a qualified hardware timing capability.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Current findings now include complete vendor package inventories, QUTS client ownership and a correction ledger. Historical acquisitions retain their original scope and limits. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

**Key terms:** An entry point is a command intended to be run. A snapshot preserves an older source version. Provenance records the source, inputs and conditions behind a result. See the [glossary](../glossary.md).

## Contents

- [Maintained entry points and recorded scope](#maintained-entry-points-and-recorded-scope)
- [Retained local harnesses](#retained-local-harnesses)
- [Commands actually used in this follow-up](#commands-actually-used-in-this-follow-up)
- [Continued findings](#continued-findings)
- [Publication and validation boundary](#publication-and-validation-boundary)
- [Findings index](#findings-index)

This catalog connects the findings to maintained tools, retained historical
sources, and recorded execution. It does not label every retained script as run
or every successful process as a qualified hardware capability.

Current operational state: the [private campaign quarantined](../acquisition/private-campaign-2026-10-03-quarantine.md)
after 33 action-3 requests. Two complete bundles contain 24 observations. Nine
additional admitted observations belong to the rejected capture. Later passive
and scan observations did not rearm private acquisition. The latest timing-boundary
follow-up used on-disk inspection and synthetic models only; lifecycle work is
preparation only. See the [current ledger](gap-closure-ledger.md).

## Maintained entry points and recorded scope

Paths below are relative to the repository root. Follow each tool's documented
permissions, exact-build prerequisites and explicit execution switches.

| Work | Maintained scripts / source | Recorded result and limitation |
|---|---|---|
| Vendor package and installed-file snapshots | `research/adapters/Invoke-QualcommStaticInspection.ps1`, `package_tools/`, `inspect_qik_inventory.py` | Preview/apply/unchanged receipts, supported static decoding, read-only MSI/type-library metadata; no vendor execution or device access. See [runbook](../adapters/static-inspection-runbook.md) |
| Knowledge and workflow maintenance | `research/evidence/Update-ResearchKnowledge.ps1`, `build_knowledge_index.py`, `sync_workflow_diagrams.py` | Authored-source indexing and canonical diagram synchronization; source matches are not a call graph. See [reference index](../knowledge/reference-index.md) |
| Adapter/build discovery and protocol guards | `research/adapters/Get-QualcommAdapter.ps1`, `research/tsf/qualcomm_protocol.py`, `research/tsf/qualcomm_probe.py` | Exact build and command validation; preview differs from explicit private execution |
| TSF series capture and decode | `research/tsf/Capture-TsfReport.ps1`, `research/tsf/decode_tsf_etl.c`, `research/tsf/analyze_tsf_series.py` | Repeated private reads; command completion is not sampling time |
| Owned diagnostic TSF replay | `research/tsf/read_tsf_evidence.py`, `research/evidence/hardware_observation.py` | Replayed 138 retained observations; detached records and clock-input rejection, no new acquisition. See [runbook](../tsf/tsf-evidence-reader.md) |
| Autonomous peer TSF decoding | `research/tsf/decode_management_tsf.py` | Authored beacon/probe frames only; independent clock/event fields, no local RX timestamp or live capture. See [runbook](../tsf/autonomous-management-tsf.md) |
| Management-frame RX handoff | `research/adapters/inspect_management_rx.py` | Exact-file schema and handoff inspection; local timestamp positions not consumed by the selected handler. [Report](../adapters/qualcomm-management-rx-handoff.md) |
| TSF/SoC latch experiment | `research/tsf/Capture-LatchExperiment.ps1`, `research/tsf/analyze_latch.py` | Action-dependent refresh/cache observations; no simultaneous-latch proof |
| FTM request, callback and aggregation | `research/ftm/ftm_once.c`, `research/ftm/Capture-FtmOnce.ps1`, `research/ftm/decode_ftm_response.py`, `research/ftm/model_ftm_selection.py` | Specialized ranging/callback execution and saved aggregation replay; no absolute four-event export |
| FTM delta extraction | `research/ftm/Export-FtmDeltaEvents.ps1`, `research/ftm/FtmDeltaLog.ps1`, `research/ftm/analyze_ftm_deltas.py` | 51 saved triplets reproduce signed subtraction; malformed target messages reject |
| FTM event ingress and lifetime | `research/ftm/inspect_ftm_ingress.py` | Executed offline: exact event schema, registration/cleanup and host-time history import; no owned application timestamp export. See [report](../ftm/ftm-ingress-to-owned-response.md) |
| Guarded campaign | `research/acquisition/run_acquisition_campaign.py`, `research/acquisition/live_observer.c`, `research/acquisition/campaign_gate.py`, `research/acquisition/Get-CampaignIdentity.ps1`, `research/acquisition/campaign_admission.py` | Earlier 138-request campaign completed; corrected-observer repeat quarantined as recorded separately |
| Passive observer validation | Existing `capture(..., actions=[], smoke=True)` controller path; retained qualification runner below | Two corrected-observer passes succeeded with zero private requests |
| Standard timestamp/device-service probes | `research/windows_timestamps/probe_timestamp_caps.py`, `research/windows_timestamps/native_caps.c`, `research/adapters/device_services.c`, `research/adapters/cached_beacon.c` | API outcomes and exact ABI checks; cache and capability errors do not establish hardware absence |
| Refined NDIS experiment | `research/windows_timestamps/Build-NdisExperiment.ps1`, `research/windows_timestamps/ndis_query_probe.c`, `research/windows_timestamps/ndis_trace_health.c`, `research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1`, `research/windows_timestamps/NdisV2Health.ps1`, `research/windows_timestamps/Export-NdisNamedEvents.ps1`, `research/windows_timestamps/ndis_evidence.py`, `research/windows_timestamps/analyze_ndis_run.py` | Three bracketed queries, same-run topology and full health; interface activities do not bind application requests |
| Evidence export/lifecycle | `research/evidence/export_clock_evidence.py`, `research/evidence/validate_research_bundle.py`, `research/acquisition/observation_lifecycle.py` | Strict offline admission/fixtures; no automatic clock conversion |
| Clock-model investigation | `research/clock_models/analyze_observation_quality.py`, `research/clock_models/analyze_clock_pairing_hypothesis.py` | Conditional/held-out models; residual and feasibility are not calibrated uncertainty |
| Quarantine postmortem | `research/acquisition/analyze_quarantined_tsf.py`, `research/acquisition/Export-TsfContext.ps1` | New maintained offline tools, actually replayed on the failed capture in this follow-up |
| TSF routes and memory-log lead | `research/tsf/inspect_tsf_routes.py` | Exact-driver direct-branch/import inventory; no complete call-graph or live retrieval claim |
| TSF response metadata and association | `research/tsf/inspect_tsf_report_contract.py` | Exact expected schema and selected handler read offsets; omitted fields have candidate reference labels only. [Quarantine disposition](../tsf/tsf-association-and-quarantine-disposition.md) remains retain |
| Private return-path candidates | `research/adapters/inspect_private_exports.py` | Executed offline against the exact owned driver: range hashes, RX-statistics dispatch and fixed test payload; no live export qualification. See [report and commands](../adapters/qualcomm-private-output-routes.md) |
| Passive quarantine follow-up | `research/acquisition/run_passive_observation.py`, `research/acquisition/Invoke-PassiveObservation.ps1` | One elevated 30-second window passed with zero requests/timing events and clean shutdown; no firmware-drain or ring-retrieval claim |
| Scan-source comparison | `research/acquisition/run_scan_comparison.py`, `research/acquisition/analyze_scan_comparison.py`, explicit launcher `-ScanComparison` | Three scans reproduced two-report pattern; all fail the four-second completion profile; final diagnostic tail identified late completion |
| Cancellation/restart tests | Historical cancellation/reset sources in archive below | Prior bounded experiments only; not current live entry points or general reset/drain qualification |

The [operations guide](OPERATIONS.md), [experiment guide](../acquisition/experiments.md), and
individual qualification reports give command syntax, build/runtime requirements,
source revisions and limits. Native probes require their own build; CI's compile
or help checks are not live execution evidence.

## Retained local harnesses

The [source archive](../reproductions/2026-10-03/README.md) contains all 36 authored
`.py`, `.ps1` and `.c` files retained in the inspected local artifact/current-WLAN
evidence directories. Its [manifest](../reproductions/2026-10-03/manifest.json) lists
every file, original SHA-256, archived SHA-256, redaction and normalization.
The one third-party reference source is explicitly excluded.

The later passive observation also retains its [exact acquisition wrapper](../reproductions/2026-10-03-passive-launch/manifest.json)
separately, because the maintained wrapper received an offline stderr/exit-code
correction after that successful run. This is an additional snapshot beyond the
original 36-file archive.

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
python research/acquisition/analyze_quarantined_tsf.py --capture $capture --timing "$capture/quarantine-offline-new.jsonl" --output "$capture/postmortem-new.json"
./research/acquisition/Export-TsfContext.ps1 -EtlPath "$capture/tsf.etl" -ReportOrdinals 10,11 -ContextMilliseconds 2 -OutputPath "$capture/unmatched-context-new.json"
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
./tests/Test-NdisCaptureHelpers.ps1 -CaptureScript ./research/windows_timestamps/Capture-NdisTimestampStatusV2.ps1
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

The newest maintained offline entry points are
`research/memory_ring/inspect_timing_boundaries.py` (exact-build field/call inventory)
and `research/memory_ring/model_ring_publication.py` (fixed synthetic publication
counterexample). Both were executed; neither reads live device memory. Their
tests are `tests/test_timing_boundaries.py` and `tests/test_ring_publication_model.py`.

- [Timing return paths, ring publication and RX descriptor fields](../memory-ring/timing-boundary-investigation-2026-10-03.md)
- [Prepared lifecycle and timing qualification cases](../acquisition/lifecycle-qualification-preparation.md)
- [Controlled scan comparison plan](../acquisition/scan-comparison-plan.md)
- [Controlled scan/TSF results](../acquisition/scan-tsf-results-2026-10-03.md)
- [Qualification gap closure ledger](gap-closure-ledger.md)
- [Live passive check, memory-log consumers and scan attribution lead](../acquisition/passive-and-retrieval-validation-2026-10-03.md)
- [Unmatched TSF counter behavior and the host-memory log path](../memory-ring/unmatched-tsf-and-memory-log.md)
- [Proposed hardware-time boundary](../evidence/api-direction.md)
- [ALFA AWUS036AXML / MT7921AUN](../adapters/axml.md)
- [Clock evidence contract v1](../evidence/evidence-contract.md)
- [Exact-build Qualcomm latch and FTM experiments](../acquisition/experiments.md)
- [FTM aggregation and TSF delivery: exact-build follow-up](../ftm/ftm-result-provenance.md)
- [Operations](OPERATIONS.md)
- [Packet-to-clock timestamp map and uncertainty ledger](../clock-models/packet-to-clock-map.md)
- [Qualcomm FastConnect 7800 Windows research](../adapters/qualcomm.md)
- [Qualcomm guarded acquisition: completed idle/workload campaign](../acquisition/acquisition-campaign-2026-10-02-results.md)
- [Stronger timestamp paths and equipment gates](../adapters/backend-and-reference-next-steps.md)
- [Qualifying the TSF, FTM and host-clock relationships](../clock-models/clock-relationship-investigation.md)
- [TSF versus SoC: what the reported increments can identify](../clock-models/counter-rate-identifiability.md)
- [FTM buffer, notification and TSF routing: exact-build static follow-up](../ftm/ftm-notification-routing.md)
- [Access to pre-aggregation FTM records: offline follow-up](../ftm/ftm-raw-access-followup.md)
- [Conservative observation lifecycle](../acquisition/lifecycle-matrix.md)
- [Guarded Qualcomm acquisition campaign](../acquisition/live-acquisition-campaign.md)
- [Refined NDIS experiment and capability qualification](../windows-timestamps/ndis-refined-experiment.md)
- [NDIS rejection-origin analysis](../windows-timestamps/ndis-rejection-origin-analysis.md)
- [Bounded live NDIS status capture](../windows-timestamps/ndis-status-capture-2026-10-03.md)
- [Observing timestamp OID status through existing NDIS events](../windows-timestamps/ndis-status-observation-path.md)
- [Corrected observer: passive live qualification](../acquisition/observer-passive-qualification-2026-10-03.md)
- [Private acquisition latency: measured stages and the next bounded experiment](../acquisition/private-acquisition-latency.md)
- [Private campaign: stopped on unmatched TSF reports](../acquisition/private-campaign-2026-10-03-quarantine.md)
- [Private timing acquisition: practical research direction](../acquisition/private-timing-acquisition-plan.md)
- [Private TSF returns, automatic reporting and TX-completion timing](../tsf/private-tsf-fast-paths.md)
- [Offline observation quality: first downstream work package](../clock-models/qualcomm-observation-matrix.md)
- [Research delivery: evidence contract, lifecycle and predictive checks](../evidence/research-delivery-2026-10-02.md)
- [Windows timestamp path follow-up](../windows-timestamps/windows-timestamp-path-followup.md)
- [Sources and provenance](sources.md)
- [Research-to-Userspace-Clock Implementation Plan](2026-10-02-research-to-userspace-clock.md)
- [Validation ledger](validation.md)

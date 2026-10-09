# PR #3 component review map: 2026-10-06 baseline

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__overview__pr3-component-review-map-2026-10-06.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

This map classifies all 220 files in the published PR baseline and identifies the evidence, tests and risks a reviewer needs for each component. It is a review plan and coverage ledger, not evidence that every changed line has been independently reviewed. The current documentation pass verifies publication metadata, inventory and status consistency; it does not repeat the completed binary investigation or certify production readiness.

**Subsequent review:** the [completed software review and corrections](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/pr3-review-2026-10-06.md)
records source/document coverage, four reproduced and corrected findings, and
344 passing configured tests. It supersedes the pending software-review status
of the assignments below. This page retains the original published inventory;
publication and fresh hosted CI for the corrected files are tracked on PR #3.

## Immutable scope and hosted checks

Read-only GitHub verification on 2026-10-06, America/New_York, found
[PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3) open and not draft,
with no submitted GitHub PR reviews and no review decision. The public repository
default branch is `main`.

| Baseline | Exact value |
|---|---|
| Remote PR base | `0e866ed6b2409231c100af75a6aef97c6bdd2fa3` (`main`) |
| Remote PR head / inspected local HEAD | `aca5b7ca7c96ca8731f15202361c34faf003f350` (`investigate-packet-export`) |
| Exact local base-to-head inventory | 220 changed files; 31,378 additions; 13 deletions |
| Pull-request workflow | [37558308352](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37558308352): `protocol` and `windows-syntax` successful at the stated head |
| Push workflow | [37558305170](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37558305170): `protocol` and `windows-syntax` successful at the stated head |

GitHub check timestamps fall on 2026-10-07 UTC, still 2026-10-06 in New York.
The API run `head_sha` and commit check-run `head_sha` both matched the recorded
head. These checks do not validate the later uncommitted S0/S2 documentation
refresh. The 220-file map deliberately stays tied to the immutable published
range; local additions, including this map and the route decision, are separate.

Reproduce the file inventory without changing the checkout:

```powershell
git diff --name-status 0e866ed6b2409231c100af75a6aef97c6bdd2fa3 aca5b7ca7c96ca8731f15202361c34faf003f350
git diff --numstat 0e866ed6b2409231c100af75a6aef97c6bdd2fa3 aca5b7ca7c96ca8731f15202361c34faf003f350
gh pr view 3 --repo Protonmatter/wifi-hardware-time --json baseRefOid,headRefOid,changedFiles,statusCheckRollup,reviews
```

## Component coverage and baseline review assignments

Every file below has one primary component. Documentation and manifests are in E
even when they describe A-D; the linked evidence remains relevant to those
components. Risk describes failure impact if a component is used, not a newly
reproduced severity finding. Test presence and a historical test pass are not
independent line review.

| Component | Files | Responsibility / risk | Review evidence available at the baseline | Assigned follow-up scope |
|---|---:|---|---|---|
| A. Exact-image inspectors and package inspection | 38 | File bounds, hashes, paths and selected call/branch receipts; low operational risk when read-only, but incorrect attribution can invalidate downstream conclusions | [Refresh review](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/refresh-validation.md) documents addressed independent-review findings in static tooling. [Receive audit](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/receive-shutdown-contract.md) and [QMSL 365](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qmsl-runtime-365.md) document selected exact-build investigations. Current pass reads these reports and maps paths; it does not retrace them | Independent review of accumulated inspector/helper changes at this exact range; compare relevant source predicates to private exact-image receipts, including rejected inputs and scope limits |
| B. Pure decoders, observation and source-record contracts | 10 | Input bounds, exact integer/byte preservation, identity, quarantine and false capability flags; medium risk of misleading observations if validation is wrong | [Source-operation review](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/source-operation-record.md#validation-and-limits) records independent code/document review and focused tests for that earlier slice. Existing decoder/evidence reports are scoped software evidence; current pass inventories them | Review the whole component at this exact head, especially cross-profile acceptance, unknown/loss handling, provenance and malformed input; prior slice review is not approval of every decoder |
| C. Acquisition and cleanup wrappers | 7 | Collectors, observer child processes, trace profiles and registry analysis; high operational impact if invoked with an incorrect target, privileges or cleanup behavior | [Packet observer report](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/packet-capture-and-elevation.md) and [discovery attribution](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-live-gate-and-commonio.md) record bounded historical runs and limitations. Current pass checks documented status only | Review exact targeting, preflight, deadlines, ownership of children/sessions, failure cleanup and log sanitization across current wrappers. No new operational qualification or elevated run occurred |
| D. Native broker, control and trace exporters | 20 | C ownership, concurrency, ABI, output lengths, build wrappers and Python response bridge; medium software memory/lifecycle risk, with separate live-control risk | [Broker review](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/raw-event-response-broker.md#validation-and-remaining-work) records a reproduced/fixed mutable-input race and non-exhaustive scheduler coverage. [Fixed GET](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/device-service-positive-control.md) proves only that operation. Current pass reads evidence and classifies files | Independent review across broker, native consumers, builds and saved-trace parsing at this head; complete cancellation/deadline interleavings and source-lifetime integration remain separate. User-mode results do not prove WDF or firmware rundown |
| E. Documentation, index, provenance and workflow | 145 | Evidence claims, navigation, generated index, script hashes and CI/publication exclusions; low runtime impact but material auditability risk if stale | Current S0/S2 pass reconciles current status, exact PR base/head and route gates; [earlier refresh review](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/refresh-validation.md) and [document disposition](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/document-review.md) retain prior scope. Automated links/index checks validate structure only | Full factual and publication review of remaining accumulated documents, catalog and workflow changes; inspect version-specific claims against original evidence. No complete 220-file content/security audit is asserted |

## Test and fixture map

These are existing tests/commands for a reviewer. This documentation pass runs
the focused E checks, not a new full native/private-fixture campaign. The
published [workflow](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/.github/workflows/offline-checks.yml) runs Python
discovery on Linux, authored index/diagram checks and separate Windows parser,
native build and helper checks. It does not supply private vendor images or live
hardware. A skipped fixture test is not a passing fixture qualification.

| Component | Existing tests / commands | Fixtures and scope limits |
|---|---|---|
| A | `test_static_inspection.py`, `test_qik_inventory.py`, `test_action4_completion.py`, `test_event_export_candidates.py`, `test_ftm_ingress.py`, `test_ihv_queries.py`, `test_management_rx_path.py`, `test_mlo_cache.py`, `test_packetlog_return.py`, `test_private_export_routes.py`, `test_tsf_ingress.py`, `test_tsf_report_contract.py`, `test_windows_bss_time.py`, `test_wlanlib_dispatch.py` | Authored rejection data plus optional exact driver/Windows fixtures; Ghidra selected-output and hash/no-overwrite checks remain private receipts. Historical QMSL 365 suite reports 340 tests, zero skips; that pass is not rerun here |
| B | `test_decode_tsf_report.py`, `test_hardware_observation.py`, `test_management_tsf.py`, `test_read_tsf_evidence.py`, `test_source_record.py` | Authored bytes and temporary bundles check unknown semantics, malformed input, origin and identities. No real producer qualification follows |
| C | `test_quts_registry_analysis.py`, `tests/Test-WifiPathHelpers.ps1`; relevant existing campaign/passive/cleanup tests also run in full discovery/workflow | Authored trace/child status controls; historical captures are private. Parser/helper passes do not execute or attest a live collector |
| D | `test_device_service_control.py`, `test_native_export_contract.py`, `test_raw_event_broker.py`, `test_trace_bytes.py`; `Build-RawEventBroker.ps1`, `Test-TimestampExport.ps1`, `Build-TsfTraceBytes.ps1`, `Test-DeviceServiceControl.ps1` | Installed compiler/Windows SDK required for relevant native tests; broker/return tests use authored fixtures and threads. Control build/self-test is distinct from a live device call; saved ETL parsing is distinct from acquisition |
| E | `python -m unittest discover -s tests -p test_documentation_navigation.py -v`; corresponding `test_knowledge_index.py`, `test_workflow_diagrams.py`, `test_research_layout.py`; `python research/evidence/build_knowledge_index.py --check`; `python research/evidence/sync_workflow_diagrams.py --check`; `git diff --check` | Authored-source paths and temporary fixtures only. Index tokens are navigation aids, not a runtime call graph; diagram synchronization does not prove arrow semantics |

For a full offline rerun use the repository's existing
`python -m compileall -q research tests` and
`python -m unittest discover -s tests -v`, configuring owned
fixtures and the native compiler as documented. Report passed/skipped tests and
the exact tested tree separately from the historical results cited here.

## Publication and capability boundaries

The map contains authored paths and public Git identities only. Raw vendor
binaries, disassembly, captures, endpoint identifiers and private retrieval
locations remain outside public Git. Existing exclusion tests and index source
filtering are useful controls; this map is not a completed secrets/license audit
of the accumulated PR. No commit, push, merge or external review comment is part
of this documentation change.

The [route decision](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/hardware-route-decision-2026-10-06.md) is no-go
for current Qualcomm live integration. The selected QMSL software path and prior
bounded live controls do not establish a complete event, calibrated clock,
firmware drain or safe kernel producer. Deferred IHV work and quarantine remain
unchanged. The coordinator subsequently reports reviewed S3 implementation/15 focused
tests and 64 downstream tests passed, S8's 12-run local host profile
passed, and S9's nine-file local patch preserved/verified without publication.
These later results and the [WPP installation assessment](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/wpp-external-2311-file-assessment.md)
are outside the immutable published PR range above and do not imply full PR
review, a consumer SLA or hardware accuracy.

## Complete published file inventory

`A`/`M` in the change column mean added/modified in the pinned PR range. Component
letters refer to the coverage table above. Every row is inventoried, not signed
off by this inventory alone. Subsequent coverage and remaining evidence limits
are recorded in the [final software review](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/pr3-review-2026-10-06.md).
Counts and additions/deletions were reconciled with the live PR metadata.

| Change | Component | File | Added | Deleted |
|---|---|---|---:|---:|
| M | E | `.gitattributes` | 4 | 0 |
| M | E | `.github/workflows/offline-checks.yml` | 35 | 0 |
| M | E | `README.md` | 11 | 0 |
| A | E | `catalog/scripts.json` | 50 | 0 |
| M | E | `docs/README.md` | 4 | 0 |
| M | E | `docs/acquisition/README.md` | 6 | 0 |
| M | E | `docs/acquisition/acquisition-campaign-2026-10-02-results.md` | 4 | 0 |
| M | E | `docs/acquisition/experiments.md` | 4 | 0 |
| M | E | `docs/acquisition/lifecycle-matrix.md` | 4 | 0 |
| M | E | `docs/acquisition/lifecycle-qualification-preparation.md` | 4 | 0 |
| M | E | `docs/acquisition/live-acquisition-campaign.md` | 4 | 0 |
| M | E | `docs/acquisition/observer-passive-qualification-2026-10-03.md` | 4 | 0 |
| A | E | `docs/acquisition/packet-capture-and-elevation.md` | 179 | 0 |
| M | E | `docs/acquisition/passive-and-retrieval-validation-2026-10-03.md` | 4 | 0 |
| M | E | `docs/acquisition/private-acquisition-latency.md` | 4 | 0 |
| M | E | `docs/acquisition/private-campaign-2026-10-03-quarantine.md` | 4 | 0 |
| M | E | `docs/acquisition/private-timing-acquisition-plan.md` | 4 | 0 |
| M | E | `docs/acquisition/scan-comparison-plan.md` | 4 | 0 |
| M | E | `docs/acquisition/scan-tsf-results-2026-10-03.md` | 4 | 0 |
| A | E | `docs/acquisition/timing-qualification-validation-2026-10-04.md` | 173 | 0 |
| M | E | `docs/adapters/README.md` | 24 | 0 |
| M | E | `docs/adapters/axml.md` | 4 | 0 |
| M | E | `docs/adapters/backend-and-reference-next-steps.md` | 4 | 0 |
| A | E | `docs/adapters/diagrams/vendor-return-paths.mmd` | 18 | 0 |
| A | E | `docs/adapters/ghidra-workspace.md` | 209 | 0 |
| A | E | `docs/adapters/ihv-query-producer-map.md` | 184 | 0 |
| A | E | `docs/adapters/qmsl-diagnostic-queue.md` | 245 | 0 |
| A | E | `docs/adapters/qmsl-runtime-365.md` | 129 | 0 |
| A | E | `docs/adapters/qualcomm-archive-transport-findings.md` | 390 | 0 |
| A | E | `docs/adapters/qualcomm-bss-serialization.md` | 199 | 0 |
| A | E | `docs/adapters/qualcomm-management-rx-handoff.md` | 207 | 0 |
| A | E | `docs/adapters/qualcomm-management-timing-producer.md` | 238 | 0 |
| A | E | `docs/adapters/qualcomm-minimal-transport-contract.md` | 64 | 0 |
| A | E | `docs/adapters/qualcomm-private-output-routes.md` | 237 | 0 |
| A | E | `docs/adapters/qualcomm-rx-export-boundary.md` | 143 | 0 |
| A | E | `docs/adapters/qualcomm-software-center-timing-leads.md` | 208 | 0 |
| M | E | `docs/adapters/qualcomm.md` | 4 | 0 |
| A | E | `docs/adapters/quts-callback-framing-and-wlanlib.md` | 302 | 0 |
| A | E | `docs/adapters/quts-discovery-gate.md` | 272 | 0 |
| A | E | `docs/adapters/quts-endpoint-writer-and-receive.md` | 328 | 0 |
| A | E | `docs/adapters/quts-live-gate-and-commonio.md` | 275 | 0 |
| A | E | `docs/adapters/quts-mhi-route-validation.md` | 222 | 0 |
| A | E | `docs/adapters/static-inspection-runbook.md` | 136 | 0 |
| A | E | `docs/adapters/windows-bss-host-time.md` | 122 | 0 |
| A | E | `docs/adapters/wlanlib-dispatch-and-completion.md` | 371 | 0 |
| M | E | `docs/clock-models/README.md` | 4 | 0 |
| M | E | `docs/clock-models/clock-relationship-investigation.md` | 6 | 0 |
| M | E | `docs/clock-models/counter-rate-identifiability.md` | 4 | 0 |
| A | E | `docs/clock-models/diagrams/ftm-reduction.mmd` | 11 | 0 |
| M | E | `docs/clock-models/diagrams/packets-timestamp-path.mmd` | 4 | 1 |
| M | E | `docs/clock-models/diagrams/uncertainty-timestamp-path.mmd` | 4 | 1 |
| M | E | `docs/clock-models/packet-to-clock-map.md` | 24 | 5 |
| M | E | `docs/clock-models/qualcomm-observation-matrix.md` | 4 | 0 |
| M | E | `docs/evidence/README.md` | 13 | 0 |
| M | E | `docs/evidence/api-direction.md` | 4 | 0 |
| A | E | `docs/evidence/complete-event-hardware-handoff.md` | 206 | 0 |
| A | E | `docs/evidence/device-service-positive-control.md` | 206 | 0 |
| M | E | `docs/evidence/diagrams/adoption-timestamp-path.mmd` | 5 | 1 |
| A | E | `docs/evidence/driver-event-return-integration.md` | 276 | 0 |
| M | E | `docs/evidence/evidence-contract.md` | 4 | 0 |
| A | E | `docs/evidence/owned-event-extension.md` | 165 | 0 |
| A | E | `docs/evidence/owned-timestamp-export-prototype.md` | 192 | 0 |
| A | E | `docs/evidence/qualification-audit-2026-10-04.md` | 152 | 0 |
| A | E | `docs/evidence/quts-enumeration-2026-10-04.md` | 145 | 0 |
| A | E | `docs/evidence/raw-event-response-broker.md` | 265 | 0 |
| A | E | `docs/evidence/raw-timestamp-export-gate.md` | 114 | 0 |
| M | E | `docs/evidence/research-delivery-2026-10-02.md` | 4 | 0 |
| A | E | `docs/evidence/source-operation-record.md` | 227 | 0 |
| M | E | `docs/ftm/README.md` | 9 | 1 |
| M | E | `docs/ftm/diagrams/ftm-timestamp-path.mmd` | 3 | 1 |
| A | E | `docs/ftm/diagrams/notification-routing.mmd` | 11 | 0 |
| A | E | `docs/ftm/ftm-buffer-ownership-and-identity.md` | 129 | 0 |
| A | E | `docs/ftm/ftm-ingress-to-owned-response.md` | 194 | 0 |
| M | E | `docs/ftm/ftm-notification-routing.md` | 6 | 0 |
| M | E | `docs/ftm/ftm-raw-access-followup.md` | 4 | 0 |
| M | E | `docs/ftm/ftm-result-provenance.md` | 4 | 0 |
| M | E | `docs/glossary.md` | 13 | 0 |
| A | E | `docs/knowledge/assumptions-and-corrections.md` | 130 | 0 |
| A | E | `docs/knowledge/current-findings.md` | 262 | 0 |
| A | E | `docs/knowledge/diagram-manifest.json` | 126 | 0 |
| A | E | `docs/knowledge/document-review.md` | 98 | 0 |
| A | E | `docs/knowledge/interface-directory.md` | 137 | 0 |
| A | E | `docs/knowledge/reference-index.md` | 330 | 0 |
| A | E | `docs/knowledge/refresh-validation.md` | 83 | 0 |
| A | E | `docs/knowledge/research-index.json` | 8662 | 0 |
| A | E | `docs/knowledge/workflow-diagrams.md` | 262 | 0 |
| M | E | `docs/memory-ring/README.md` | 7 | 0 |
| A | E | `docs/memory-ring/diagrams/report-vs-ring.mmd` | 9 | 0 |
| A | E | `docs/memory-ring/mlo-cache-and-symbol-search.md` | 242 | 0 |
| A | E | `docs/memory-ring/packetlog-producer-trace.md` | 274 | 0 |
| A | E | `docs/memory-ring/packetlog-return-path.md` | 253 | 0 |
| M | E | `docs/memory-ring/timing-boundary-investigation-2026-10-03.md` | 4 | 0 |
| M | E | `docs/memory-ring/unmatched-tsf-and-memory-log.md` | 6 | 0 |
| M | E | `docs/overview/2026-10-02-research-to-userspace-clock.md` | 4 | 0 |
| A | E | `docs/overview/2026-10-03-first-hardware-clock-plan.md` | 245 | 0 |
| M | E | `docs/overview/OPERATIONS.md` | 4 | 0 |
| M | E | `docs/overview/README.md` | 5 | 0 |
| A | E | `docs/overview/complete-event-2026-10-05/context-map.md` | 38 | 0 |
| A | E | `docs/overview/complete-event-2026-10-05/decision-log.md` | 37 | 0 |
| A | E | `docs/overview/complete-event-2026-10-05/devex-review.md` | 29 | 0 |
| A | E | `docs/overview/complete-event-2026-10-05/engineering-plan.md` | 95 | 0 |
| A | E | `docs/overview/complete-event-2026-10-05/problem-and-scope.md` | 30 | 0 |
| A | E | `docs/overview/complete-event-2026-10-05/route-research.md` | 104 | 0 |
| A | E | `docs/overview/complete-event-2026-10-05/test-matrix.md` | 35 | 0 |
| M | E | `docs/overview/gap-closure-ledger.md` | 88 | 1 |
| M | E | `docs/overview/repository-layout.md` | 4 | 0 |
| M | E | `docs/overview/sources.md` | 4 | 0 |
| M | E | `docs/overview/validation-execution-catalog.md` | 12 | 0 |
| M | E | `docs/overview/validation.md` | 4 | 0 |
| M | E | `docs/reproductions/2026-10-03/README.md` | 4 | 0 |
| M | E | `docs/tsf/README.md` | 19 | 1 |
| A | E | `docs/tsf/action4-completion-and-report-contract.md` | 240 | 0 |
| A | E | `docs/tsf/autonomous-management-tsf.md` | 111 | 0 |
| M | E | `docs/tsf/diagrams/qualcomm-timestamp-path.mmd` | 4 | 1 |
| A | E | `docs/tsf/dma-backing-contract.md` | 167 | 0 |
| A | E | `docs/tsf/firmware-trace-return-candidates.md` | 292 | 0 |
| A | E | `docs/tsf/hif-receive-buffer-producer.md` | 302 | 0 |
| M | E | `docs/tsf/private-tsf-fast-paths.md` | 4 | 0 |
| A | E | `docs/tsf/receive-shutdown-contract.md` | 143 | 0 |
| A | E | `docs/tsf/saved-trace-byte-audit.md` | 142 | 0 |
| A | E | `docs/tsf/tsf-association-and-quarantine-disposition.md` | 197 | 0 |
| A | E | `docs/tsf/tsf-event-ingress-and-owned-copy.md` | 364 | 0 |
| A | E | `docs/tsf/tsf-evidence-reader.md` | 103 | 0 |
| M | E | `docs/windows-timestamps/README.md` | 4 | 0 |
| M | E | `docs/windows-timestamps/ndis-refined-experiment.md` | 4 | 0 |
| M | E | `docs/windows-timestamps/ndis-rejection-origin-analysis.md` | 4 | 0 |
| M | E | `docs/windows-timestamps/ndis-status-capture-2026-10-03.md` | 4 | 0 |
| M | E | `docs/windows-timestamps/ndis-status-observation-path.md` | 4 | 0 |
| M | E | `docs/windows-timestamps/windows-timestamp-path-followup.md` | 4 | 0 |
| M | E | `research/README.md` | 4 | 0 |
| A | C | `research/acquisition/Observe-QutsRegistry.ps1` | 147 | 0 |
| A | C | `research/acquisition/Observe-WifiDataPath.ps1` | 166 | 0 |
| M | E | `research/acquisition/README.md` | 8 | 0 |
| A | C | `research/acquisition/analyze_quts_registry.py` | 241 | 0 |
| A | D | `research/acquisition/export_registry_trace.c` | 90 | 0 |
| A | C | `research/acquisition/quts-registry.wprp` | 21 | 0 |
| A | C | `research/acquisition/wifi-path.wprp` | 19 | 0 |
| A | D | `research/adapters/Invoke-DeviceServiceControl.ps1` | 148 | 0 |
| A | A | `research/adapters/Invoke-QualcommStaticInspection.ps1` | 149 | 0 |
| M | E | `research/adapters/README.md` | 17 | 0 |
| A | D | `research/adapters/device_service_control.c` | 104 | 0 |
| A | A | `research/adapters/ghidra/AnnotateQualcommTiming.java` | 189 | 0 |
| A | A | `research/adapters/ghidra/TraceAtlasQuts.java` | 34 | 0 |
| A | A | `research/adapters/ghidra/TraceQmslQueue.java` | 126 | 0 |
| A | A | `research/adapters/ghidra/TraceQualcommPacketlog.java` | 114 | 0 |
| A | A | `research/adapters/ghidra/TraceQutsDiscovery.java` | 161 | 0 |
| A | A | `research/adapters/inspect_ihv_queries.py` | 137 | 0 |
| A | A | `research/adapters/inspect_management_rx.py` | 189 | 0 |
| A | A | `research/adapters/inspect_private_exports.py` | 163 | 0 |
| A | A | `research/adapters/inspect_qik_inventory.py` | 168 | 0 |
| A | A | `research/adapters/inspect_windows_bss_time.py` | 113 | 0 |
| A | A | `research/adapters/inspect_wlanlib_dispatch.py` | 168 | 0 |
| A | A | `research/adapters/package_tools/Expand-QccBlocks.ps1` | 84 | 0 |
| A | A | `research/adapters/package_tools/Read-MsiTables.ps1` | 48 | 0 |
| A | A | `research/adapters/package_tools/Read-TypeLibrary.ps1` | 35 | 0 |
| A | A | `research/adapters/package_tools/expand_qpst.py` | 101 | 0 |
| A | A | `research/adapters/package_tools/inspect_files.py` | 50 | 0 |
| M | E | `research/clock_models/README.md` | 4 | 0 |
| M | E | `research/evidence/README.md` | 5 | 0 |
| A | E | `research/evidence/Update-ResearchKnowledge.ps1` | 23 | 0 |
| A | E | `research/evidence/build_knowledge_index.py` | 190 | 0 |
| A | B | `research/evidence/hardware_observation.py` | 65 | 0 |
| A | E | `research/evidence/sync_workflow_diagrams.py` | 61 | 0 |
| A | D | `research/export_contract/Build-RawEventBroker.ps1` | 84 | 0 |
| A | E | `research/export_contract/README.md` | 49 | 0 |
| A | D | `research/export_contract/Test-TimestampExport.ps1` | 40 | 0 |
| A | D | `research/export_contract/raw_event_broker.c` | 297 | 0 |
| A | D | `research/export_contract/raw_event_broker.h` | 83 | 0 |
| A | D | `research/export_contract/read_raw_response.py` | 72 | 0 |
| A | B | `research/export_contract/source_record.py` | 275 | 0 |
| A | D | `research/export_contract/timestamp_export.c` | 310 | 0 |
| A | D | `research/export_contract/timestamp_export.h` | 98 | 0 |
| M | E | `research/ftm/README.md` | 5 | 0 |
| A | A | `research/ftm/inspect_ftm_ingress.py` | 135 | 0 |
| M | E | `research/memory_ring/README.md` | 6 | 0 |
| A | A | `research/memory_ring/inspect_mlo_cache.py` | 144 | 0 |
| A | A | `research/memory_ring/inspect_packetlog_return.py` | 150 | 0 |
| A | D | `research/tsf/Build-TsfTraceBytes.ps1` | 39 | 0 |
| M | E | `research/tsf/README.md` | 15 | 0 |
| A | D | `research/tsf/audit_trace_bytes.py` | 188 | 0 |
| A | B | `research/tsf/decode_management_tsf.py` | 110 | 0 |
| A | B | `research/tsf/decode_tsf_report.py` | 248 | 0 |
| A | D | `research/tsf/export_tsf_trace_bytes.c` | 100 | 0 |
| A | A | `research/tsf/inspect_action4_completion.py` | 94 | 0 |
| A | A | `research/tsf/inspect_event_export_candidates.py` | 252 | 0 |
| A | A | `research/tsf/inspect_tsf_ingress.py` | 340 | 0 |
| A | A | `research/tsf/inspect_tsf_report_contract.py` | 92 | 0 |
| A | B | `research/tsf/read_tsf_evidence.py` | 91 | 0 |
| M | E | `research/windows_timestamps/README.md` | 4 | 0 |
| A | E | `skills/qualcomm-timing-research/SKILL.md` | 68 | 0 |
| A | D | `tests/Test-DeviceServiceControl.ps1` | 35 | 0 |
| A | C | `tests/Test-WifiPathHelpers.ps1` | 46 | 0 |
| A | D | `tests/native_raw_event_broker.c` | 259 | 0 |
| A | D | `tests/native_timestamp_export.c` | 270 | 0 |
| A | A | `tests/test_action4_completion.py` | 55 | 0 |
| A | B | `tests/test_decode_tsf_report.py` | 319 | 0 |
| A | D | `tests/test_device_service_control.py` | 52 | 0 |
| A | A | `tests/test_event_export_candidates.py` | 92 | 0 |
| A | A | `tests/test_ftm_ingress.py` | 53 | 0 |
| A | B | `tests/test_hardware_observation.py` | 87 | 0 |
| A | A | `tests/test_ihv_queries.py` | 75 | 0 |
| A | E | `tests/test_knowledge_index.py` | 73 | 0 |
| A | A | `tests/test_management_rx_path.py` | 122 | 0 |
| A | B | `tests/test_management_tsf.py` | 107 | 0 |
| A | A | `tests/test_mlo_cache.py` | 93 | 0 |
| A | D | `tests/test_native_export_contract.py` | 44 | 0 |
| A | A | `tests/test_packetlog_return.py` | 87 | 0 |
| A | A | `tests/test_private_export_routes.py` | 94 | 0 |
| A | A | `tests/test_qik_inventory.py` | 82 | 0 |
| A | C | `tests/test_quts_registry_analysis.py` | 183 | 0 |
| A | D | `tests/test_raw_event_broker.py` | 221 | 0 |
| A | B | `tests/test_read_tsf_evidence.py` | 55 | 0 |
| A | B | `tests/test_source_record.py` | 197 | 0 |
| A | A | `tests/test_static_inspection.py` | 162 | 0 |
| A | D | `tests/test_trace_bytes.py` | 127 | 0 |
| A | A | `tests/test_tsf_ingress.py` | 206 | 0 |
| A | A | `tests/test_tsf_report_contract.py` | 40 | 0 |
| A | A | `tests/test_windows_bss_time.py` | 79 | 0 |
| A | A | `tests/test_wlanlib_dispatch.py` | 96 | 0 |
| A | E | `tests/test_workflow_diagrams.py` | 40 | 0 |

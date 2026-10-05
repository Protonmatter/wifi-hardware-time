# Wi-Fi counter access: tools

These tools inspect, request and decode the Wi-Fi timing counter, called TSF. They distinguish a successful request from the later firmware report and retain action-dependent cache behavior. Private acquisition remains quarantined; offline analysis and preview are separate from explicit hardware execution and do not qualify sampling accuracy.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** The TSF sampling and response-association contract remains open. New diagnostic return interfaces do not automatically qualify a fresh TSF getter. See [current findings](../../docs/knowledge/current-findings.md).
<!-- /current-context -->

## Files

- [inspect_tsf_ingress.py](inspect_tsf_ingress.py): exact-build event registration, transport length, normalization and cleanup evidence; [runbook](../../docs/tsf/tsf-event-ingress-and-owned-copy.md). Decoder modes `event-wire` and `htc-wire` retain the WMI event or its complete supplied transport envelope.
- The same inspector now covers the [HIF receive producer](../../docs/tsf/hif-receive-buffer-producer.md): active callback installation, pooled-buffer reset, CE operation tables and completion handoff. Live export remains unqualified.
- [inspect_action4_completion.py](inspect_action4_completion.py) and [decode_tsf_report.py](decode_tsf_report.py): exact-build submission inspection and owned diagnostic TLV decoding; [runbook and qualification limits](../../docs/tsf/action4-completion-and-report-contract.md).
- [decode_management_tsf.py](decode_management_tsf.py): decode peer-advertised TSF from saved ordinary beacon/probe frames; [scope and runbook](../../docs/tsf/autonomous-management-tsf.md).
- [inspect_tsf_report_contract.py](inspect_tsf_report_contract.py): offline exact-build schema and handler field-coverage inventory; no live report decoding or device requests.
- [read_tsf_evidence.py](read_tsf_evidence.py): read saved TSF bundles; see the [API and runbook](../../docs/tsf/tsf-evidence-reader.md). No live device access.
| File | Role |
|---|---|
| [analyze_latch.py](analyze_latch.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [analyze_tsf_series.py](analyze_tsf_series.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [Capture-LatchExperiment.ps1](Capture-LatchExperiment.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [Capture-TsfReport.ps1](Capture-TsfReport.ps1) | Bounded experiment controller/launcher; explicit execution and prerequisites apply. |
| [decode_tsf_etl.c](decode_tsf_etl.c) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [inspect_tsf_routes.py](inspect_tsf_routes.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [qualcomm_probe.py](qualcomm_probe.py) | Probe or native helper; consult its header and the matching research report before use. |
| [qualcomm_protocol.py](qualcomm_protocol.py) | Shared validation, admission or result rules; not a standalone hardware command. |

## Read before running

- [Findings and procedures](../../docs/tsf/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

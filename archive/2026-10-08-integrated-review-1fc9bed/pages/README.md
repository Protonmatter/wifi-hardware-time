# Wi-Fi Hardware Time

> **Archive — not current operating instructions.** Historical documentation at [1fc9bed58df4](https://github.com/Protonmatter/wifi-hardware-time/commit/1fc9bed58df4abd6fc28ae883670d05adff47cd0). Relative links are rebased for reading. [Exact original bytes](../originals/README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

This project asks whether Wi-Fi hardware can provide trustworthy timestamps for applications and synchronized clocks. We have recovered useful diagnostic data, but have not demonstrated calibrated synchronization. The research is organized by the question each experiment answers, with its scripts, evidence limits and diagrams linked together.

<!-- current-context:2026-10-08 -->
**Current context (2026-10-08):** Persistent action-4 sampling completed a five-minute idle live smoke with 139 successful requests and clean shutdown. Offline screening accepted 138 samples; corrected arrival-aware replay reports conditional integer-estimate uncertainty below 1 ms for 92.863% of its declared interval, and all 297 event-grid points settled below a 1-ms half-width after a median 2.341-second wait. These are conditional station-TSF/QPC results, not calibrated AP/UTC accuracy. Read the [review corrections and retained-data comparison](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/pr-reconciliation-2026-10-08.md), [original tested findings](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/persistent-tsf-smoke-2026-10-08.md), [mathematics](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/tsf-mathematics.md) and [next research and implementation gates](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/persistent-tsf-next-steps.md). The separate complete-original-event export route remains unqualified.
<!-- /current-context -->

## Contents

- [Start here](#start-here)
- [Research areas](#research-areas)
- [What works and what remains open](#what-works-and-what-remains-open)
- [Run offline checks](#run-offline-checks)
- [Repository and publication boundaries](#repository-and-publication-boundaries)

## Start here

- Current interpretation: [latest findings](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/current-findings.md) and [assumptions corrected by evidence](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/assumptions-and-corrections.md).
- Persistent sampler: [contract and tests](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/persistent-tsf-sampler.md), [live smoke results](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/persistent-tsf-smoke-2026-10-08.md), [math reference](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/tsf-mathematics.md), [roadmap](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/persistent-tsf-next-steps.md) and [seven Archify views](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/archify-tsf/README.md).
- Next integration: [complete-event implementation plan](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/complete-event-2026-10-05/engineering-plan.md), including primary-source route research and the executed receive-lifetime audit.
- Find a call or string: [reference index](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/reference-index.md) and [interface directory](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/interface-directory.md).
- Repeat static research: [inspection runbook](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/static-inspection-runbook.md), [script catalog](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/catalog/scripts.json) and [research skill](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/skills/qualcomm-timing-research/SKILL.md).
- View every current workflow: [diagram gallery](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/knowledge/workflow-diagrams.md).
- New to the subject: [reading guide](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/README.md) and [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/glossary.md).
- Want the outcome: [qualification ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/gap-closure-ledger.md). *Qualification* means evidence supports a particular claim under stated conditions.
- Reviewing the accumulated change: [PR #3 software review and corrections](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/pr3-review-2026-10-06.md), with scope, reproduced findings and publication limits.
- Want the workflow: [packet-to-clock diagrams](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/packet-to-clock-map.md).
- Want to reproduce work: [operations](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/OPERATIONS.md) and [script/execution catalog](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/validation-execution-catalog.md).
- Using older commands: [file-location guide](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/overview/repository-layout.md). Paths changed; old live-launch manifests must not be reused.

## Research areas

| Question | Read the findings | Find the scripts |
|---|---|---|
| Which adapters and driver builds can we inspect? | [Adapters](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/adapters/README.md) | [Discovery](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/adapters/README.md) |
| Can we read the Wi-Fi timing counter reliably? | [TSF counter access](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/tsf/README.md) | [TSF tools](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/tsf/README.md) |
| What do Wi-Fi ranging results actually contain? | [FTM ranging](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/ftm/README.md) | [FTM tools](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/ftm/README.md) |
| What do the standard Windows timestamp APIs expose? | [Windows timestamp APIs](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/windows-timestamps/README.md) | [Windows tools](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/windows_timestamps/README.md) |
| Can we recognize missing, late or misleading reports? | [Acquisition and lifecycle](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/acquisition/README.md) | [Collectors and checks](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/acquisition/README.md) |
| Can we safely retrieve the driver's in-memory log? | [Memory-ring access](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/memory-ring/README.md) | [Static inspection and models](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/memory_ring/README.md) |
| Can hardware counter values be related to host time? | [Clock models](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/clock-models/README.md) | [Analysis tools](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/clock_models/README.md) |
| What evidence may an application safely consume? | [Evidence handoff](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/README.md) | [Export and validation](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/research/evidence/README.md) |

TSF is the Wi-Fi timing counter. FTM is a ranging procedure that measures round-trip timing. An API is an interface software uses to request data or an operation. These are separate parts of the clock problem, not interchangeable timestamp sources.

## What works and what remains open

- **Observed:** exact-build Qualcomm driver reports expose TSF and another counter. Selected requests refresh or reuse that second counter.
- **Live persistent smoke:** one owned session completed 139 pending-to-success requests, with no cancellation, trace loss or unfinished operation. Achieved request gaps were 2.005 seconds median and 4.009 seconds maximum with report wait retained. This is one idle smoke run, not a long-run/load qualification.
- **Live transport control:** one [device-service GET](https://github.com/Protonmatter/wifi-hardware-time/blob/1fc9bed58df4abd6fc28ae883670d05adff47cd0/docs/evidence/device-service-positive-control.md) returned eight fixed test bytes through the installed driver. The firmware-timing producer remains unconnected.
- **Observed with limits:** FTM ranging operations return aggregate results. These do not expose all absolute event times needed to estimate clock offset.
- **Historical strict campaign quarantined:** its unmatched-report disposition remains unchanged. The later bound-campaign profile separately records foreign reports for offline screening; it does not clear that quarantine or prove firmware drain. Three earlier scans failed the original four-second completion profile.
- **Static findings only:** RX descriptor timestamp fields and in-memory diagnostic-log consumers are located. Static inspection reads source/binary files; it does not demonstrate a working live export.
- **New static ownership evidence:** the installed QUTS client allocates diagnostic payload bytes into application storage. QXDM supplies WLAN schema leads and a byte-array API. Their connection to the exact Wi-Fi timing producer remains open.
- **Not qualified:** fresh simultaneous sampling, calibrated hardware-to-host accuracy, arbitrary RX/TX timestamps, AP/UTC accuracy and multi-device sub-millisecond synchronization.
- **Preparation only:** new reset, suspend and roaming cases. No new disruptive run is authorized by these documents.

The inspected hardware includes Qualcomm FastConnect 7800 and ALFA AWUS036AXML / MediaTek MT7921AUN. Findings apply to their stated builds; a product name alone is not sufficient provenance.

## Run offline checks

Python 3.11+ is the baseline. These checks do not open a wireless device:

```powershell
python -m pip install -r requirements.txt
python -m compileall -q research tests
python -m unittest discover -s tests -v
```

The optional `WIFI_TIME_DRIVER_FIXTURE` variable points to a locally owned, exact-build SYS driver file. Those tests inspect the file as data; they do not load it. Without the file, its tests skip. Live commands have additional requirements in the operations guide.

## Repository and publication boundaries

- This repository owns research, experiment tools and qualification evidence.
- [userspace-clock](https://github.com/Protonmatter/userspace-clock) owns the application API. Its experimental host-only clock is separate from the unqualified Wi-Fi provider.
- `docs/<topic>/diagrams/` contains editable Mermaid diagram sources. Topic pages explain arrows and evidence status; color is not the only status cue.
- `docs/reproductions/` contains historical source snapshots stored as text. They are not current executable tools.
- Driver binaries, firmware, raw traces, disassembly, endpoint identifiers and local captures remain outside public Git.
- No distribution license has been selected. Third-party sources retain their own terms.

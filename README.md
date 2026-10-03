# Wi-Fi Hardware Time

This project asks whether Wi-Fi hardware can provide trustworthy timestamps for applications and synchronized clocks. We have recovered useful diagnostic data, but have not demonstrated calibrated synchronization. The research is organized by the question each experiment answers, with its scripts, evidence limits and diagrams linked together.

## Contents

- [Start here](#start-here)
- [Research areas](#research-areas)
- [What works and what remains open](#what-works-and-what-remains-open)
- [Run offline checks](#run-offline-checks)
- [Repository and publication boundaries](#repository-and-publication-boundaries)

## Start here

- New to the subject: [reading guide](docs/README.md) and [glossary](docs/glossary.md).
- Want the outcome: [qualification ledger](docs/overview/gap-closure-ledger.md). *Qualification* means evidence supports a particular claim under stated conditions.
- Want the workflow: [packet-to-clock diagrams](docs/clock-models/packet-to-clock-map.md).
- Want to reproduce work: [operations](docs/overview/OPERATIONS.md) and [script/execution catalog](docs/overview/validation-execution-catalog.md).
- Using older commands: [file-location guide](docs/overview/repository-layout.md). Paths changed; old live-launch manifests must not be reused.

## Research areas

| Question | Read the findings | Find the scripts |
|---|---|---|
| Which adapters and driver builds can we inspect? | [Adapters](docs/adapters/README.md) | [Discovery](research/adapters/README.md) |
| Can we read the Wi-Fi timing counter reliably? | [TSF counter access](docs/tsf/README.md) | [TSF tools](research/tsf/README.md) |
| What do Wi-Fi ranging results actually contain? | [FTM ranging](docs/ftm/README.md) | [FTM tools](research/ftm/README.md) |
| What do the standard Windows timestamp APIs expose? | [Windows timestamp APIs](docs/windows-timestamps/README.md) | [Windows tools](research/windows_timestamps/README.md) |
| Can we recognize missing, late or misleading reports? | [Acquisition and lifecycle](docs/acquisition/README.md) | [Collectors and checks](research/acquisition/README.md) |
| Can we safely retrieve the driver's in-memory log? | [Memory-ring access](docs/memory-ring/README.md) | [Static inspection and models](research/memory_ring/README.md) |
| Can hardware counter values be related to host time? | [Clock models](docs/clock-models/README.md) | [Analysis tools](research/clock_models/README.md) |
| What evidence may an application safely consume? | [Evidence handoff](docs/evidence/README.md) | [Export and validation](research/evidence/README.md) |

TSF is the Wi-Fi timing counter. FTM is a ranging procedure that measures round-trip timing. An API is an interface software uses to request data or an operation. These are separate parts of the clock problem, not interchangeable timestamp sources.

## What works and what remains open

- **Observed:** exact-build Qualcomm driver reports expose TSF and another counter. Selected requests refresh or reuse that second counter.
- **Observed with limits:** FTM ranging operations return aggregate results. These do not expose all absolute event times needed to estimate clock offset.
- **Acquisition stopped:** a private campaign encountered unmatched reports and remains quarantined, meaning further admission is blocked. Three later scans reproduced extra report traffic but failed the original four-second completion profile.
- **Static findings only:** RX descriptor timestamp fields and in-memory diagnostic-log consumers are located. Static inspection reads source/binary files; it does not demonstrate a working live export.
- **Not qualified:** fresh simultaneous sampling, hardware-to-host conversion, arbitrary RX/TX timestamps, calibrated accuracy and sub-millisecond synchronization.
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

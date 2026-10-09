# A guide to the research

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Start with the question you need answered, then follow its evidence to the relevant experiment. The project has useful Wi-Fi timing observations but no qualified synchronized hardware clock. This guide separates what was observed, what was inferred, what remains unknown and which tools belong to each question.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Current findings now include complete vendor package inventories, QUTS client ownership and a correction ledger. Historical acquisitions retain their original scope and limits. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Choose a reading path](#choose-a-reading-path)
- [Research map](#research-map)
- [How to read evidence and diagrams](#how-to-read-evidence-and-diagrams)
- [Find older files](#find-older-files)

## Choose a reading path

- **Continue the persistent TSF work:** [live smoke findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/persistent-tsf-smoke-2026-10-08.md) → [mathematics](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/tsf-mathematics.md) → [next research/implementation/tests](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/persistent-tsf-next-steps.md). Explore the [Archify diagram specifications](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/archify-tsf/README.md).
- **Understand the result:** [current gaps](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/gap-closure-ledger.md) → [validation ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/validation.md).
- **Understand the concepts:** [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) → [packet-to-clock map](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/packet-to-clock-map.md).
- **Reproduce a check:** topic findings → [script catalog](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/validation-execution-catalog.md) → [operations](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md). Check whether the command is offline, read-only discovery or an active experiment.
- **Build an application:** [evidence handoff](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/README.md) → [API direction](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/api-direction.md). The maintained implementation belongs in the separate `userspace-clock` repository.

## Research map

| Area | Question answered | Main limit |
|---|---|---|
| [Adapters](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/README.md) | What hardware and driver paths are available? | Source inspection alone does not qualify physical hardware |
| [TSF](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/README.md) | Can we retrieve the Wi-Fi counter? | Returned values do not establish when they were sampled |
| [FTM](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/ftm/README.md) | What does ranging reveal? | Aggregate round-trip time does not establish clock offset |
| [Windows timestamp APIs](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/windows-timestamps/README.md) | Where do documented queries succeed or fail? | A failed query is not proof of hardware absence |
| [Acquisition](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/README.md) | Are observations complete, attributable and fresh? | Quiet periods and process restarts do not prove firmware drain |
| [Memory ring](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/README.md) | Can an in-memory diagnostic log be read safely? | Reservation position is not a record-completion marker |
| [Clock models](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/README.md) | Can counter values be mapped to another clock? | A good fit is not calibrated accuracy |
| [Evidence handoff](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/README.md) | What may downstream software accept? | Valid data structure is not a qualified clock |

## How to read evidence and diagrams

- **Observed/live:** a bounded operation ran on the stated hardware. Read its sample count, failures and conditions.
- **Static:** code or a binary file was inspected. The path may exist without having been exercised.
- **Model/synthetic:** constructed data tests a software rule or logical claim. It is not a hardware measurement.
- **Unqualified/unknown:** the required evidence is missing. Treat an unknown error as unknown, not zero.
- **Quarantined:** ambiguity or a failure blocks further admission until a separately reviewed recovery decision.
- **Solid arrow:** the described data/control flow within that diagram's stated scope. It does not by itself mean live qualification.
- **Dashed arrow:** a candidate, missing or future relationship. Each diagram also states its local legend.
- **Diamond:** a decision or acceptance check. Labels identify outcomes even without color.

## Find older files

[Repository layout and migration map](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/repository-layout.md) lists every
moved path. Historical links pinned to a Git commit still refer to the files at
that revision. Use current topic paths for current commands; do not rewrite old
capture manifests to make them appear current. Historical snapshots remain in
[reproductions](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/reproductions/2026-10-03/README.md).

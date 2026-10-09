# A guide to the research

Start with the question you need answered, then follow its evidence to the relevant experiment. The project has useful Wi-Fi timing observations but no qualified synchronized hardware clock. This guide separates what was observed, what was inferred, what remains unknown and which tools belong to each question.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Maintained reading guide. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](research-history/README.md) · [Timeline](research-history/timeline.md) · [Previous version](../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__README.md).
<!-- /research-history -->

## Follow the research over time

Start with [goals and current position](research-history/README.md), then follow the [chronology](research-history/timeline.md), [results and failed attempts](research-history/results-and-validation.md), [hypotheses and corrections](research-history/hypotheses-and-lessons.md) and [next steps](research-history/next-steps.md). The [complete catalogue](research-history/source-map.md) accounts for every pre-refresh Markdown file; the [dated archive](../archive/README.md) preserves the older versions. [Publication status](research-history/publication-status.md) records merged work, open PRs and the public/private boundary.

## Contents

- [Choose a reading path](#choose-a-reading-path)
- [Research map](#research-map)
- [How to read evidence and diagrams](#how-to-read-evidence-and-diagrams)
- [Find older files](#find-older-files)

## Choose a reading path

- **Continue the persistent TSF work:** [live smoke findings](acquisition/persistent-tsf-smoke-2026-10-08.md) → [mathematics](clock-models/tsf-mathematics.md) → [next research/implementation/tests](overview/persistent-tsf-next-steps.md). Explore the [Archify diagram specifications](overview/archify-tsf/README.md).
- **Understand the result:** [current gaps](overview/gap-closure-ledger.md) → [validation ledger](overview/validation.md).
- **Understand the concepts:** [glossary](glossary.md) → [packet-to-clock map](clock-models/packet-to-clock-map.md).
- **Reproduce a check:** topic findings → [script catalog](overview/validation-execution-catalog.md) → [operations](overview/OPERATIONS.md). Check whether the command is offline, read-only discovery or an active experiment.
- **Build an application:** [evidence handoff](evidence/README.md) → [API direction](evidence/api-direction.md). The maintained implementation belongs in the separate `userspace-clock` repository.

## Research map

| Area | Question answered | Main limit |
|---|---|---|
| [Adapters](adapters/README.md) | What hardware and driver paths are available? | Source inspection alone does not qualify physical hardware |
| [TSF](tsf/README.md) | Can we retrieve the Wi-Fi counter? | Returned values do not establish when they were sampled |
| [FTM](ftm/README.md) | What does ranging reveal? | Aggregate round-trip time does not establish clock offset |
| [Windows timestamp APIs](windows-timestamps/README.md) | Where do documented queries succeed or fail? | A failed query is not proof of hardware absence |
| [Acquisition](acquisition/README.md) | Are observations complete, attributable and fresh? | Quiet periods and process restarts do not prove firmware drain |
| [Memory ring](memory-ring/README.md) | Can an in-memory diagnostic log be read safely? | Reservation position is not a record-completion marker |
| [Clock models](clock-models/README.md) | Can counter values be mapped to another clock? | A good fit is not calibrated accuracy |
| [Evidence handoff](evidence/README.md) | What may downstream software accept? | Valid data structure is not a qualified clock |

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

[Repository layout and migration map](overview/repository-layout.md) lists every
moved path. Historical links pinned to a Git commit still refer to the files at
that revision. Use current topic paths for current commands; do not rewrite old
capture manifests to make them appear current. Historical snapshots remain in
[reproductions](reproductions/2026-10-03/README.md).

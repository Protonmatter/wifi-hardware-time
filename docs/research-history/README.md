# Wi-Fi timing research: goals, progress and evidence

We can collect diagnostic TSF observations on the tested Qualcomm Windows system and replay them into useful conditional time intervals. We have not established calibrated access-point time, an uninterrupted sub-millisecond live clock, complete original firmware-event export, or multi-device synchronization. This guide explains how we reached that position, including the successful work and the ideas that failed.

**Review baseline:** 2026-10-09, America/New_York; merged research source `e9d71b84365122ff2640e240b20fc1dbb834388a`. Dates in the timeline use that timezone; experiment timestamps explicitly marked UTC retain their original meaning. The documentation publication base additionally includes corrected atlas merge `da4f55e`. Published-source scope and PR state are identified in the [publication record](publication-status.md). Private unpublished findings are maintained separately.

## Read the story

| Reader's question | Start here |
|---|---|
| What were we trying to achieve, and where are we now? | This page, then [current findings](../knowledge/current-findings.md) |
| What happened, in what order, and why did the direction change? | [Research timeline](timeline.md) |
| Which results actually passed, failed, or remain conditional? | [Results and validation](results-and-validation.md) |
| Which hypotheses held up, broke, or were simply wrong? | [Hypotheses and lessons](hypotheses-and-lessons.md), then the [detailed correction ledger](../knowledge/assumptions-and-corrections.md) |
| What belongs in public documentation? | [Publication boundary](publication-boundary.md) and [publication status](publication-status.md) |
| What should be done next, and what would count as success? | [Next steps and acceptance evidence](next-steps.md) |
| Where is a particular report, tool guide, or old version? | [Complete documentation catalogue](source-map.md) and [dated archive](../../archive/README.md) |
| How was this documentation review checked? | [Review scope and validation](documentation-review-2026-10-09.md) |

## Goals and their current disposition

The broad question was whether Wi-Fi hardware could provide trustworthy timestamps for applications and synchronized clocks. The selected practical target became the Qualcomm FastConnect 7800 on Windows: relate the station's TSF to a specified QPC instant, eventually establish its relationship to the associated AP's TSF, and expose uncertainty honestly to applications. Linux/MediaTek and WiFi PTP informed alternatives; they did not replace the selected platform. UTC and system-clock discipline are later, separate objectives.

| Goal | What has been achieved | What prevents declaring it complete |
|---|---|---|
| Find and identify usable timing sources | Exact-build Windows/Linux paths, private request/report behavior, FTM aggregates, standard-API failures and vendor transport candidates are documented | A symbol, counter or endpoint name does not establish a supported complete timing API |
| Collect attributable diagnostic observations | Guarded campaigns, retained failed attempts, offline screening and one persistent-session live smoke | Full firmware identity, causal online admission and live failure/recovery qualification remain open |
| Relate station TSF to host QPC | Exact rate-envelope and separately labelled affine models; replay on retained idle/load/smoke data | Capture-in-window, rate and continuity assumptions are not independent physical measurements |
| Make application event timestamps useful | Causal states and two-phase provisional/settled research implementations; corrected replay policies | A maintained consumer must receive causally admitted live samples; current results use offline screening |
| Obtain complete original events | Static copy/lifetime analysis, synthetic owned exporters, response broker and an eight-byte live transport control | The complete firmware timing producer is not connected to a qualified application return |
| Establish AP or shared time below 1 ms | Coarse beacon consistency and an explicit validation plan | Station/AP error and combined multi-node error budgets need independent measurement |
| Preserve reproducibility | Source/input hashes, versioned results, exact-build tools, offline checks and private evidence separation | Public readers cannot reproduce measurements without access to private captures |

## The two research tracks must remain distinct

**Diagnostic TSF and conditional clocks:** asynchronous driver reports provide reduced numeric observations. Screened host windows support conditional station-TSF/QPC models. The persistent sampler demonstrated normal operation for one five-minute idle run. This is real progress, even though physical accuracy remains unqualified.

**Complete original-event export:** the work traces original firmware bytes, ownership, publication, return paths and lifecycle. QUTS/QMSL copies and the authored broker establish valuable software mechanisms. The fixed-byte driver return establishes a particular transport. None yet supplies an attributable complete firmware timing event. The [2026-10-06 no-go](../evidence/hardware-route-decision-2026-10-06.md) applies to this track; it does not erase later diagnostic TSF results.

## How to interpret a claim

Read every result as **source/build + operation + evidence level + accepted conditions + unresolved limits**. Static findings, synthetic tests, saved-data replay, a live operation, hosted CI and independent timing validation answer different questions. A passing software test can establish rejection or ownership behavior without establishing radio-clock accuracy.

The [current numerical table](results-and-validation.md#current-corrected-results) uses the versioned post-merge comparison. Older reports keep their original capture/source context, with current links above them. A failed profile stays failed when later diagnostics explain it; a changed model gets a new version; an unknown capability stays unknown. Historical commands are not new authorization to collect, reset, roam, change logging or modify clocks.

## Repository responsibilities

This repository owns research, probes, evidence contracts and qualification. The linked [userspace-clock repository](https://github.com/Protonmatter/userspace-clock) owns maintained application providers. Proprietary packages, raw ETLs, disassembly and endpoint identifiers remain outside this public repository. The private evidence repository's earlier snapshot is a preservation result, not a timing qualification; this review did not repeat that private release audit.

For an implementation starting point, follow [next steps](next-steps.md). For the full audit trail, start at the [timeline](timeline.md) and use the commit and experiment links rather than treating an old plan as the latest status.

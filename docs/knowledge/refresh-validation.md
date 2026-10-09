# Research refresh validation

This refresh publishes the latest findings, corrected assumptions, repeatable offline tools and workflow diagrams together. Validation checks software behavior and evidence boundaries, including failures found by independent review. No hardware capability is enabled. Hosted checks belong to the exact PR head; dated investigation results remain separate historical evidence.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__knowledge__refresh-validation.md).
<!-- /research-history -->

## Contents

- [What changed](#what-changed)
- [Review findings resolved](#review-findings-resolved)
- [Validation scope](#validation-scope)
- [Publication and remaining gates](#publication-and-remaining-gates)

## What changed

- Preserved the archive findings and their distinction between component, package
  and current installed versions.
- Added [current findings](current-findings.md), [corrected assumptions](assumptions-and-corrections.md),
  a curated [interface directory](interface-directory.md) and a generated
  [reference index](reference-index.md).
- Refreshed 86 existing Markdown pages with current-context navigation while
  retaining dated results. See the [document disposition record](document-review.md).
- Updated nine canonical workflow diagrams and all 19 embeds, with legends and
  explicit missing connections. See the [gallery](workflow-diagrams.md).
- Added preview/apply/unchanged static inspection, bounded extraction workers,
  evidence receipts, index regeneration, a script catalog and a reusable skill.

## Review findings resolved

Independent code review reproduced issues despite the initial passing tests.
The implemented corrections and focused regressions cover:

| Finding | Correction and validation |
|---|---|
| Index could include ignored nested `evidence` folders | Only exact authored roots are exceptions; nested and mixed-case private directories are excluded |
| Windows junctions could expose external files | Reparse checks cover roots, ancestors, discovered entries and README; independent junction fixtures reject |
| Junction aliases could hide input/output nesting | Input ancestry is checked before output creation; regression verifies no writes |
| UTF-16 bypassed the XML declaration check | Supported metadata is explicitly UTF-8; alternate/NUL-bearing encodings reject before parsing |
| Optional MSI handling swallowed row-limit failures | `_Tables` establishes actual absence; enumeration and bound failures remain fatal |
| Windows test assumed `pwsh` existed | Optional integration test detects PowerShell availability and skips correctly |
| Mixed-case fixture reused lowercase Windows directories | Distinct parents exercise actual mixed-case directory names |
| Hosted Windows short path names bypassed lexical nesting checks | Both existing path sides are expanded before ancestry comparison; authored 8.3-alias regression rejects before output creation |
| Extended Windows namespace spelled the same tree differently | Unsupported namespace forms reject before mutation; existing path identity uses filesystem metadata handles rather than spelling alone |
| Hosted Linux produced a differently ordered index | Source paths use explicit ordinal POSIX-style ordering and normalized-text hashes across platforms |

The promoted Ghidra entry point also defaults to preview and requires `--apply`
for a new private output directory. Internal package workers are used behind the
public wrapper; they are not separate operational entry points.

## Validation scope

The maintained commands are:

```powershell
python -m compileall -q research tests
python -m unittest discover -s tests -v
python research/evidence/build_knowledge_index.py --check
python research/evidence/sync_workflow_diagrams.py --check
```

Separate local file-only exercises reproduced:

- QXDM QCC extraction and a receipt-verified `Unchanged` repeat.
- QIK payload inventory using the newly extracted blocks.
- QPST extraction and read-only MSI tables.
- Extracted type-library inspection without registration.
- Ghidra preview with no output directory, followed by explicit apply reproducing
  the seven selected QPSTServer 496 references.
- Skill validation and PowerShell parser checks.

These actual vendor files and generated evidence remain under ignored artifacts.
Hosted CI uses authored fixtures, Python 3.11 and separate Windows tests. It does
not obtain vendor packages, run Ghidra, contact hardware or reproduce private
Windows-image qualification. Current counts/results are reported in the PR.

## Publication and remaining gates

The active review is [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3),
with [checks](https://github.com/Protonmatter/wifi-hardware-time/pull/3/checks).
Do not infer merge or default-branch publication from a feature-branch push.

Client-owned diagnostic bytes are statically supported. Exact Wi-Fi producer
association, server publication safety, fresh sampling, QPC conversion, calibrated
accuracy and sub-millisecond synchronization remain open. The private campaign
remains quarantined; disruptive lifecycle tests remain preparation only.

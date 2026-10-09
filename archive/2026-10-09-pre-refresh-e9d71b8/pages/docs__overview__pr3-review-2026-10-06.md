# PR #3 final software review and corrections

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__overview__pr3-review-2026-10-06.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

The accumulated research change has received component-based source review and
offline integration validation. Four reproduced defects were corrected: one P1
in subprocess supervision and three P2 issues in registry attribution, exporter
output status and empty static exports. No unresolved P0/P1/P2 finding remains
in the reviewed software scope. Publication, hosted CI for the corrected revision
and merge are tracked separately on [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3);
live hardware qualification is unchanged.

## Scope and evidence identities

The review compared remote main `0e866ed6b2409231c100af75a6aef97c6bdd2fa3`
with published PR head `aca5b7ca7c96ca8731f15202361c34faf003f350`, including
the twelve then-local status/route/WPP documentation changes. The published
range contains 220 files; the [component map](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/pr3-component-review-map-2026-10-06.md)
retains that exact inventory rather than silently changing its baseline.

Before corrections, 348 Git-visible authored files were copied into an immutable
review snapshot. Its manifest SHA-256 is
`87d243299f04f75daf5d33497d10bee603d184cde40d567a208dd0fa2b59b62e`.
The original snapshot still contains the reproduced defects. Corrected files,
review reports, test logs and the final candidate manifest are retained separately
in the local review handoff; raw vendor material is excluded from public Git.

Three independent component reviewers received the same pinned snapshot and
neutral scope before findings were reconciled. The coordinator independently
reproduced the subprocess, ordering and output-flush failures, checked the
Ghidra source/log evidence, reviewed corrections and ran integration checks.
This is a local engineering review, not a submitted GitHub approval.

| Component | Review coverage | Explicit limit |
|---|---|---|
| A: inspectors and package tools | All 38 assigned source/test files read; 37 related document pages reviewed with recorded full/section coverage; exact-image and input rejection tests | Historical proprietary binary semantics and every package extraction were not exhaustively retraced |
| B/D: decoders, records, broker, native/control/export tools | All 30 assigned source/test files read; 15 contract documents checked; real ARM64 native threading, ownership, parser and output-failure tests | No exhaustive scheduler exploration or proof of a live producer |
| C: acquisition wrappers and correlation | All seven assigned files, 18 changed documents and 11 related files checked; authored child tests and saved receipt/JSONL analysis | No new collector, WPR, packet capture or vendor operation |
| E: documentation, metadata and workflow | Changed-content/status review, historical-claim boundaries, workflow/catalog checks, index regeneration, link/layout checks and all nine canonical diagrams rendered | Generated index entries are checked through their generator and deterministic output; historical hardware claims are not remeasurements |

Coverage records distinguish complete source review, changed-context review,
section review, generated-file verification and historical evidence. All 220
published paths are accounted for. The later local documents and correction
files have separate coverage; the map does not claim every historical statement
or vendor instruction was independently re-proven.

## Reproduced findings and corrections

| ID / severity | File and symbol | Problem and impact | Correction and validation |
|---|---|---|---|
| C1 / P1 | [Observe-QutsRegistry.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/Observe-QutsRegistry.ps1), `Invoke-BoundedWpr` | Windows PowerShell 5.1 lost short-lived child exit status; successful profile checks could reject and stop/cancel could not confirm status. The kill path also used an unbounded wait | Own `Diagnostics.Process`, preserve output and status, and bound exit/stream cleanup. Authored zero/nonzero/timeout cases pass in Windows PowerShell 5.1 and PowerShell 7 |
| C2 / P2 | [analyze_quts_registry.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/analyze_quts_registry.py), `analyze` | Reordering equal-QPC KCB delete/create records changed later query qualification | Poison the ambiguous generation independently of order; require later distinct deletion/new-generation evidence. Permutation, recovery and independent-key regressions pass |
| BD1 / P2 | [export_tsf_trace_bytes.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/export_tsf_trace_bytes.c) and [export_registry_trace.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/acquisition/export_registry_trace.c), `wmain` | Buffered output could fail after the exporter had selected exit 0 | Explicitly flush before success. Real stdio/broken-pipe tests compile the actual exporters with only ETW reader calls stubbed; good output succeeds and failed output returns 1 |
| A1 / P2 | [TraceQualcommPacketlog.java](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/ghidra/TraceQualcommPacketlog.java), `run` | An in-image seed resolving no functions emitted a success marker and zero-failure receipt | Reject an empty selection before creating output. Exact-image Ghidra read-only runs reject seed `1`, export one complete function for `18ae30`, and preserve an existing output on rejection |

The initial regressions failed on the frozen candidate before correction.
The coordinator also corrected stale publication wording and a route paragraph
that still recommended the already-completed shutdown audit. Historical test
counts and experiment results retain their original scope.

The registry observer's catalog digest now pins the corrected CRLF source:
`3293e2afcabb5b7b88f7db7552ab4fa9736be8bbc09a9da4b50e982c8529454f`.
The Java helper's corrected digest is
`80433fcdb3bd7649abfa4781868a14df9c9718e373b6e60db9ac527a936b3438`.
The existing packet-log instruction truncation field remains explicit; a
successful function selection is not a claim that every instruction or indirect
call has been resolved.

## Integrated validation

The configured Python 3.14.3 ARM64 suite passed **344 tests with zero skips**.
The installed MSVC ARM64 compiler and freshly rehashed Qualcomm, WiFiCx and
WlanMSM fixtures were supplied; those images were read as data, never loaded.
Python compilation passed. Ten existing/new offline helper invocations passed
under Windows PowerShell 5.1, and all **34 PowerShell files** parsed.
The new QUTS helper also passed in PowerShell 7.

The corrected registry analyzer retained the original saved attempt-06 result:
12 target queries, 12 matching stacks, 20 positive controls, no qualification
limits, and false hardware-sampling/firmware-delivery gates. This was reanalysis
of existing JSONL, not a new capture. Nine canonical Mermaid diagrams rendered
using the already installed Mermaid CLI and Chrome, with no dependency download.

Repeat the Python and document checks with:

```powershell
python -m compileall -q research tests
python -m unittest discover -s tests -v
python research/evidence/build_knowledge_index.py --check
python research/evidence/sync_workflow_diagrams.py --check
powershell.exe -NoProfile -NonInteractive -File tests/Test-QutsRegistryHelpers.ps1
git diff --check
```

Native/image tests require the existing documented compiler and exact-image
environment variables; omitted fixtures produce skips. The workflow now includes
the QUTS child regression and a Windows x64 developer-shell run of
`test_trace_export_output.py`. The local handoff distinguishes native ARM64,
additional x64 compatibility checks and hosted CI outcomes.

The additional x64 build/execution initially passed the exporter assertions but
failed while deleting a temporary executable. A second run reproduced that
cleanup-only denial; an instrumented retry succeeded after 0.1019 seconds.
The test now retries only `PermissionError` during its owned temporary-directory
cleanup, for at most ten 100 ms delays, then raises an actionable failure.
Corrected ARM64 and x64 runs passed. A deliberately held file still failed
cleanup after the bound, and other exceptions were not suppressed. The failing
logs remain retained; no cause was attributed to a specific Windows component.

The publication scan found no proprietary binary/capture files or matches for
the checked credential/private-user-path patterns. Two locally administered MAC
strings, and their generated-index entries, were traced to authored synthetic
management-frame tests. This bounded screen is not a guarantee against every
possible secret format.

## Merge boundary and remaining limits

PR #3 remains the research/evidence change. The downstream replay/host acceptance
implementation belongs in its own `userspace-clock` PR; the spectral patch remains
separately preserved. The [hardware-route decision](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/hardware-route-decision-2026-10-06.md)
and private campaign quarantine remain unchanged.

At review completion, the corrected candidate was local and uncommitted.
Published CI at `aca5b7c` predates these corrections. The PR records subsequent
publication and merge state; fresh hosted checks must match the corrected head
before merge. A clean merge state or earlier green run cannot approve later bytes.

PSScriptAnalyzer is unavailable. Full live WPR start/stop/cancel, vendor loading,
firmware drain, complete timing-event export, hardware-to-QPC correlation and
calibrated synchronization were not tested. Neither local review nor a future
merge makes those hardware capabilities available.

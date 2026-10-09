# Documentation review scope and validation, 2026-10-09

This review reconstructs the research account from the current merged repository, Git/PR history and published result files. It updates the documentation and preserves earlier versions. It is not a new hardware campaign or a comprehensive code/security audit.

[Research guide](README.md) · [Complete source catalogue](source-map.md) · [Archive](../../archive/README.md) · [Publication snapshot](publication-status.md)

## Source and change scope

The initial review baseline is public main `e9d71b84365122ff2640e240b20fc1dbb834388a`. All 145 tracked Markdown files are accounted for in the catalogue and preserved in its complete snapshot. A separate four-file supplement preserves the changed/added Markdown at the actual publication parent `da4f55e`; the combined archive restores its 146-file Markdown tree exactly. Key evidence was traced through acquisition/qualification reports, findings and assumption ledgers, source-pinned results, reviews and live GitHub state. Static references retain their exact-build scope; dated reports retain original observations. The catalogue does not claim every binary path or experiment was independently reproduced.

The isolated branch `docs/research-history-2026-10-09` is based on the subsequent atlas merge `da4f55e`. Relative to that base, changes are Markdown, documentation archive manifests, the generated knowledge index, exact-byte archive Git attributes, full-history CI checkout, archive regression tests and a pure documentation reading-copy renderer. Acquisition/driver/clock-model source, catalog pins, diagram sources/previews, measurement JSON, capture data and the research skill remain unchanged. The originating dirty checkout is preserved.

New pages cover goals, chronology, successes, failed attempts, hypotheses, unsupported claims, open work, source mapping and publication state. Current causal/settlement explanations now use corrected policies; earlier versions are archived rather than erased. Older plan and status pages link to the current account. The original reproduction corpus remains unchanged.

## Review findings addressed

| Priority | Documentation problem | Consequence | Change and validation |
|---|---|---|---|
| P1 | Current readers encountered old pending-PR/local-only status beside later merged research | Confused source/publication state and next steps | Dated exact-main/PR snapshot; current findings, ledger and roadmap reconciled; remote state read directly |
| P1 | Historical causal/settled descriptions could be read as current universal or immediate guarantees | Overstated coverage/event scope and hid policy changes | Current pages distinguish grid results, reader availability, offline admission and physical limits; numerical table checked against versioned JSON |
| P2 | Goals, failures and hypothesis corrections were distributed across many reports | Readers could repeat disproved shortcuts or miss useful positive results | Linked chronology, outcome/hypothesis ledgers and concrete acceptance gates, with supporting report links |
| P1 | Private unpublished findings were present in the initial local documentation draft | Public publication would cross the requested repository boundary | Transferred to the private evidence repository before public commit; public copies, summaries, hashes and index references removed |
| P2 | Prior documentation had no complete dated in-repository archive for this refresh | Difficult to compare how conclusions changed | Exact-byte and readable copies, SHA-256 manifests and milestone indexes; archive/coverage checks |

These are documentation/navigation findings, not newly demonstrated firmware defects. The substantive acquisition/model corrections belong to their original review reports and commits.

## Validation performed

Environment: Windows, Python 3.14.3. Commands ran from the isolated repository root unless marked as a review-only audit. No dependencies were installed and no hardware acquisition was requested by these checks.

| Check / command | Observed result |
|---|---|
| `python -m compileall -q research tests` | Passed |
| `python -m unittest discover -s tests -v` | Latest readable-copy/parent follow-up: 580 discovered, **543 passed, 37 skipped**, zero failures/errors; 57.807 s. Earlier milestone pass: 577 discovered, 540 passed and 37 skipped; initial integrated documentation pass: 562 discovered, 525 passed and 37 skipped |
| `python -m unittest discover -s tests -p test_documentation_archive.py -v` | 20 passed: independent reading-copy transformation, full publication-parent restoration, pinned milestones/revisions/scopes, canonical copy paths, Git-blob identity, complete inventory, missing/extra-file and unsafe-path/alias rejection, hashes and newline preservation |
| `python -m unittest discover -s tests -p test_documentation_navigation.py -v` | 4 passed, including file links, opening synopsis, fences and canonical overview diagrams |
| `python -m unittest discover -s tests -p test_knowledge_index.py -v` | 6 passed |
| `python -m unittest discover -s tests -p test_tsf_headlines.py -v` | 3 passed |
| `./research/evidence/Update-ResearchKnowledge.ps1 -Apply` | Regenerated the two existing index files; immediate repeat returned `Unchanged` |
| `python research/evidence/build_knowledge_index.py --check` | Passed; 369 authored sources indexed; archive contents remain outside the current-source index |
| `python research/evidence/sync_tsf_headlines.py --check` | No changed blocks; current generated numerical summaries still match their versioned source |
| `python research/evidence/sync_workflow_diagrams.py --check` | No changed diagram embeds |
| `python research/evidence/publish_archify_previews.py --check` | Seven existing diagram previews verified; none regenerated |
| `python research/evidence/apply_studio_export_policy.py --html docs/overview/archify-studio/index.html` | `Unchanged`; the merged atlas exporter and all atlas artifacts are untouched by this documentation PR |
| Archive/navigation/numerical verification | Seven public snapshots / 160 records; every original and readable copy independently verified against Git/derived output; complete 145-file initial baseline and 146-file publication-parent restoration verified; local navigation and 11 numerical summary rows checked |
| Archive target check against local Git trees | 1,046 unique commit-pinned file/directory targets resolved after the parent supplement; 322 Markdown pages and 4,815 local links passed path/anchor checks. Earlier folder-URL corrections are preserved; deterministic rendering now verifies those reading copies independently |
| Original-data and change-scope comparison | Existing result JSON and the original six archive snapshots remain unchanged; additional changes are the four-file parent supplement, pure documentation renderer, exact-byte attributes, full-history CI and archive regressions |
| `git diff --check` | Passed |
| `git merge-base --is-ancestor ebae8cc 02459e7` and `git merge-base --is-ancestor c620f47 02459e7` | Both exited 0; historical causal/settlement heads are contained in the persistent baseline |
| `git ls-remote origin refs/heads/main refs/heads/docs/interactive-archify-atlas` | Reconfirmed `e9d71b8` main and `1364017` atlas branch at final source-state check |

The 37 skips comprise 32 checks requiring privately owned exact-build image/driver fixtures and five requiring an available/configured native compiler or MSVC developer environment. They are not reported as passes. The full offline suite ran again after integrating the corrected atlas merge and archive-preservation tests. Focused documentation/index/headline checks and the read-only audit were repeated after final validation prose edits. Repeating unaffected hardware/software experiments was not necessary for those final prose changes.

An independent read-only privacy/archive review compared the candidate with the excluded private reports and the complete published baseline. It found no remaining copies, distinctive result summaries or private capture digests. All 156 public archive records matched ancestor public Git blobs. The review identified and verified correction of outdated archive instructions that had allowed uncommitted snapshots; current instructions and tests require committed public sources. This was a bounded comparison, not an exhaustive secrets audit of unrelated repositories.

## PR #11 archive verification follow-up

The initial two archive CI tests verified manifest consistency and Git newline policy. Review identified two gaps: changing an original and its manifest hash together could pass, and removing a complete-snapshot document together with its manifest row/files could pass. The one-time source/inventory audit above had checked the real repository, but those invariants were not yet enforced in CI.

Four adversarial checks first reproduced the missing rejection behavior. The corrected verifier compares each original with `git show source_revision:source_path`, obtains the complete Markdown inventory with `git ls-tree`, requires the complete snapshot to exist, and rejects extra files inside snapshots or elsewhere in the archive. A nonexistent source commit fails with a full-history diagnostic. Six mutation cases plus the two repository checks now cover these conditions without modifying the retained archive.

Independent review also identified a path-escape risk in the new temporary-fixture builder. It now validates every source/destination as a contained portable relative path before creating directories or copying files. A ninth focused test covers twelve traversal/absolute-path cases and asserts that no directory, copy or file write occurs before rejection. Mutation writes and deletes use the same containment check.

Both existing CI jobs fetch full Git history so the checks can inspect the recorded revisions in fresh hosted checkouts. Validation itself stays offline. The [archive verification instructions](../../archive/README.md#verify-committed-sources-and-completeness) explain the local prerequisite. No report contents, original bytes, result JSON or private-public boundary changed in this follow-up.

A separate local-only shallow Git reproduction rejected unavailable source history, then passed the complete 145-file blob/inventory check after an unshallow fetch from the local repository. This did not contact an external service or alter the retained archive.

## PR #11 milestone identity and copy-path follow-up

Three later comments exposed additional contract gaps: an entire selective milestone could disappear with its catalogue row, original/readable copies could share a file, and a snapshot could be regenerated from another valid revision while retaining the old directory label. Six negative cases reproduced these gaps before correction, including replacement of the complete snapshot from a different commit with the same 145-path inventory.

The archive verifier now independently pins all six snapshot directory names to full source commits. Selective milestone file sets are pinned as well; the complete snapshot still derives its full Markdown inventory from its pinned Git tree. The catalogue must contain exactly one entry for every expected snapshot. Canonical `originals/` and `pages/` paths preserve separate copies for each source; case-insensitive uniqueness and resolved-path checks reject reuse, namespace swaps and aliases. Temporary fixtures use real snapshot names and the same path-safety checks.

These corrections change archive verification and documentation only. The original six snapshot directories, their manifests, original copies and readable copies remain unchanged. Adding future snapshots requires a reviewed registry entry, so manifest or catalogue edits alone cannot silently remove or replace preserved history.

## PR #11 readable-copy and publication-parent follow-up

The follow-up review identified that recomputing a readable-copy digest could hide a removed warning or bad link, and that the initial snapshot did not include the versions changed or added by the atlas merge. Both corrupt-readable scenarios and the missing 146th parent document were reproduced before correction.

Readable copies now must equal the deterministic output of `render_documentation_archive.py` applied to independently retrieved Git source bytes and that revision's file/directory inventory. This validates the notice and inline-link transformation independently of manifest hashes, including multiline labels and linked images. All existing 156 readable copies match that transformation without changes.

The new `2026-10-09-publication-parent-da4f55e` supplement adds the exact parent versions of `README.md`, the generated reference index, the diagram gallery, and the atlas guide. Its four records bring the public archive to seven snapshots and 160 document versions. Overlaying it on the complete initial snapshot reconstructs every one of the publication parent's 146 Markdown files byte-for-byte; a dedicated test compares that result with Git. Rollback instructions now use `da4f55e` so merged atlas additions are retained.

The review-only audit also detected three unre-based multiline links in two archive reading copies. Those derived copies and their manifest hashes were repaired; exact originals were untouched. The subsequent full archive/link/anchor audit passed. This helper belongs to the review workspace, not the repository's supported research CLI.

Archive byte integrity can be rechecked independently from the repository root using the standard-library Python below. It reads files and Git objects only:

```python
import hashlib
import json
import subprocess
from pathlib import Path

for manifest in sorted(Path("archive").glob("*/manifest.json")):
    for row in json.loads(manifest.read_text(encoding="utf-8"))["files"]:
        original = (manifest.parent / row["original_path"]).read_bytes()
        reading = (manifest.parent / row["reading_path"]).read_bytes()
        assert len(original) == row["original_bytes"]
        assert hashlib.sha256(original).hexdigest() == row["original_sha256"]
        assert hashlib.sha256(reading).hexdigest() == row["reading_sha256"]
        if row["source_commit"]:
            expected = subprocess.check_output(
                ["git", "show", f'{row["source_commit"]}:{row["source_path"]}']
            )
            assert original == expected
```

This snippet requires the original commits to be present locally; a shallow clone may need their history. The public archive contains committed-source snapshots only.

## Not revalidated by this task

No new adapter/private request, WLAN scan, trace collection, vendor executable, Ghidra pass, reset, suspend, roam or system-clock operation ran. Retained private captures were not copied or replayed. The public result JSON supports document reconciliation, not independent reproduction of inaccessible measurements. Private unpublished reports are excluded from this public review account.

No downstream repository suite, private evidence release restore or consumer calibration was rerun. Existing hosted CI is cited only for its exact original main/PR head. This documentation change is submitted separately from the atlas fix; hosted results must be read from its own exact-head PR checks. No external dependencies were installed.

## Remaining risks and rollback

AP/source semantics, physical capture timing, firmware drain, online admission and persistent long-run/failure qualification remain open. The [next-step matrix](next-steps.md) states what closes them. Publication status can drift after this dated review. The corrected atlas PR #10 is merged; its navigation and generated index were reconciled before documentation publication.

Archive reading copies intentionally rebase links to immutable GitHub sources; exact-original `.md.txt` bytes preserve original relative-link context. Historical non-Markdown attachments are linked, not duplicated, so offline browsing of every old attachment is not provided. Private evidence stays private.

Rollback is limited to the paths introduced or modified by this PR: use the actual publication parent `da4f55e48a368f59ed68ee4427013a83b5c06070`, restore its modified tracked files, and remove only this PR's added documentation/archive/renderer/test files after reviewing the path list. Do not restore the earlier `e9d71b8` state over the atlas additions, reset unrelated checkouts, or change acquisition state. The complete initial snapshot plus parent supplement provides the Markdown recovery copies; other files remain recoverable from Git.

# Dated documentation archive

This archive preserves how the research was described at earlier stages. Use the current research guide for present conclusions and operating constraints. Historical text can contain superseded hypotheses, old paths, old review status and commands whose prerequisites no longer hold.

[Current research guide](../docs/research-history/README.md) · [Timeline](../docs/research-history/timeline.md) · [Complete documentation catalogue](../docs/research-history/source-map.md)

## Snapshots in date order

Dates below use America/New_York. The commit suffix identifies the source tree, not a live experiment's acquisition time. The October 9 pre-refresh capture comes from a commit made October 8 at 23:07:32 local time.

| Date / stage | Scope | Snapshot |
|---|---|---|
| 2026-10-01: initial publication | Root README | [5a42286](2026-10-01-initial-5a42286/README.md) |
| 2026-10-03: quarantine and controlled scans | Root README before topic reorganization | [fdcc22f](2026-10-03-quarantine-and-scan-fdcc22f/README.md) |
| 2026-10-06: complete-event investigation merged | README, current findings and qualification ledger | [d1055a1](2026-10-06-complete-event-d1055a1/README.md) |
| 2026-10-08: persistent sampler baseline | Same three entry points before integrated review | [02459e7](2026-10-08-persistent-baseline-02459e7/README.md) |
| 2026-10-08: integrated review | Same three entry points after first reconciliation | [1fc9bed](2026-10-08-integrated-review-1fc9bed/README.md) |
| 2026-10-09: initial review baseline | **All 145 tracked Markdown files** from main `e9d71b8` | [Complete initial snapshot](2026-10-09-pre-refresh-e9d71b8/README.md) |
| 2026-10-09: actual publication parent | Three changed Markdown files and one added atlas guide from `da4f55e`; overlays the initial snapshot to restore all **146 parent Markdown files** | [Publication-parent supplement](2026-10-09-publication-parent-da4f55e/README.md) |

## Preservation and reading rules

Each public snapshot contains a manifest with source path, published source commit, exact-original SHA-256 and byte length, and a separate hash for the reading copy. `originals/*.md.txt` preserves exact source bytes with Git newline conversion disabled. `pages/*.md` adds an archive notice and rebases relative links to immutable GitHub sources. No old conclusion is silently rewritten. The reading-copy hash will differ by design.

Historical linked binaries, measurements, diagrams and code are not duplicated here. Their committed targets remain available through the pinned source links. Private captures are not made public. Private unpublished reports and their originals are excluded from this public archive.

The complete initial snapshot plus the publication-parent supplement restores every Markdown file from the actual parent `da4f55e`, including the merged atlas additions. Overlay the supplement's four source paths on the initial 145-file inventory: three replace earlier versions and the atlas guide adds the 146th file. Tests compare all resulting bytes directly with the parent Git tree. Result JSON and historical capture files remain in their original locations and are not overwritten. Existing [October 3 reproductions](../docs/reproductions/2026-10-03/README.md) retain their own original scope.

## Verify committed sources and completeness

Run `python -m unittest discover -s tests -p test_documentation_archive.py -v` from the repository root. The checks compare every original directly with its recorded Git blob, derive every readable copy independently using [the deterministic renderer](../research/evidence/render_documentation_archive.py), and compare each result with its file and manifest hash. The renderer preserves source wording, adds the archive warning and rebases inline Markdown destinations against the pinned file/directory inventory, including multiline labels and linked images. It performs no I/O or network calls. Recomputing a manifest hash cannot admit corrupted original bytes, a missing warning or an incorrectly rebased link.

The tests also compare the complete initial snapshot with its full Git Markdown inventory and verify the 146-file publication-parent overlay byte-for-byte. Missing records, missing registered snapshots and unmanifested files anywhere in the archive fail validation.

The verifier's `EXPECTED_SNAPSHOTS` registry independently pins all seven directory names, full source commits and selected file scopes. The catalogue must list that exact set once each. Removing a milestone and its catalogue row together, or substituting another valid source revision with the same file inventory, fails validation.

Each source path has two canonical, case-insensitively unique storage paths: `originals/<source-path-with-slashes-replaced-by-double-underscores>.txt` and `pages/<source-path-with-slashes-replaced-by-double-underscores>`. The paths cannot alias each other, reuse another row's copy, swap namespaces or resolve through a link to another location. Original and reading-copy hashes remain separate.

These checks require the recorded commits locally. Both CI checkout steps use `fetch-depth: 0`. For an existing shallow clone, run `git fetch --unshallow origin` before the tests; for another incomplete-history checkout, obtain the recorded revisions from this public repository before validation. The tests themselves make no network calls, do not skip unavailable history, and do not execute archived content.

## Adding the next version

The public archive accepts committed public-source snapshots only. Before changing a maintained conclusion, snapshot its superseded published Markdown and record the exact source revision, byte hash and original path. Use `YYYY-MM-DD-description-shortsha`, add a row here in date order, link the new current page, and validate preservation and navigation. Retain uncommitted or private reports in the private evidence repository until a separate publication review approves them; do not place them in this public archive. Git remains the full history; milestone snapshots are deliberately selective between complete refreshes.

When adding a public snapshot, add its full commit and intended source-file scope to `EXPECTED_SNAPSHOTS` in the archive tests as part of the same reviewed change. Preserve existing registry entries and source identities. A new complete snapshot derives its Markdown inventory from its pinned Git tree; a selective milestone explicitly lists the documents it preserves. Snapshot removal or replacement requires an explicit scope change, not regeneration of manifests or catalogue rows alone.

For rollback of PR #11, use the actual publication parent `da4f55e48a368f59ed68ee4427013a83b5c06070`, not the earlier review baseline `e9d71b8`. Review `git diff --name-status da4f55e..HEAD`, restore only modified tracked files from that parent, and remove only the PR's introduced files after review, including its archive/test/renderer additions. This retains the merged atlas. The Markdown-only recovery source is the initial snapshot overlaid by the parent supplement; non-Markdown configuration/index files come from Git. No adapter, trace, service, acquisition state or system clock changes are involved. Do not broadly reset a checkout containing unrelated work.

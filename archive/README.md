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
| 2026-10-09: before this refresh | **All 145 tracked Markdown files** from main `e9d71b8` | [Complete snapshot](2026-10-09-pre-refresh-e9d71b8/README.md) |

## Preservation and reading rules

Each public snapshot contains a manifest with source path, published source commit, exact-original SHA-256 and byte length, and a separate hash for the reading copy. `originals/*.md.txt` preserves exact source bytes with Git newline conversion disabled. `pages/*.md` adds an archive notice and rebases relative links to immutable GitHub sources. No old conclusion is silently rewritten. The reading-copy hash will differ by design.

Historical linked binaries, measurements, diagrams and code are not duplicated here. Their committed targets remain available through the pinned source links. Private captures are not made public. Private unpublished reports and their originals are excluded from this public archive.

The complete snapshot permits restoring any pre-refresh Markdown file from exact bytes. Later result JSON and historical capture files remain in their original locations and are not overwritten. Existing [October 3 reproductions](../docs/reproductions/2026-10-03/README.md) retain their own original scope; this archive does not replace them.

## Verify committed sources and completeness

Run `python -m unittest discover -s tests -p test_documentation_archive.py -v` from the repository root. The checks compare every original directly with its recorded Git blob, verify reading-copy hashes and exact byte preservation, and compare the complete snapshot's source paths with all Markdown files in its recorded Git tree. Missing records, a removed complete snapshot and unmanifested files anywhere in the archive fail validation. Recomputing a manifest hash cannot make changed original bytes match their source commit.

The verifier's `EXPECTED_SNAPSHOTS` registry independently pins all six directory names, full source commits and the selected files in each milestone. The catalogue must list that exact set once each. Removing a milestone and its catalogue row together, or substituting another valid source revision with the same file inventory, fails validation.

Each source path has two canonical, case-insensitively unique storage paths: `originals/<source-path-with-slashes-replaced-by-double-underscores>.txt` and `pages/<source-path-with-slashes-replaced-by-double-underscores>`. The paths cannot alias each other, reuse another row's copy, swap namespaces or resolve through a link to another location. Original and reading-copy hashes remain separate.

These checks require the recorded commits locally. Both CI checkout steps use `fetch-depth: 0`. For an existing shallow clone, run `git fetch --unshallow origin` before the tests; for another incomplete-history checkout, obtain the recorded revisions from this public repository before validation. The tests themselves make no network calls, do not skip unavailable history, and do not execute archived content.

## Adding the next version

The public archive accepts committed public-source snapshots only. Before changing a maintained conclusion, snapshot its superseded published Markdown and record the exact source revision, byte hash and original path. Use `YYYY-MM-DD-description-shortsha`, add a row here in date order, link the new current page, and validate preservation and navigation. Retain uncommitted or private reports in the private evidence repository until a separate publication review approves them; do not place them in this public archive. Git remains the full history; milestone snapshots are deliberately selective between complete refreshes.

When adding a public snapshot, add its full commit and intended source-file scope to `EXPECTED_SNAPSHOTS` in the archive tests as part of the same reviewed change. Preserve existing registry entries and source identities. A new complete snapshot derives its Markdown inventory from its pinned Git tree; a selective milestone explicitly lists the documents it preserves. Snapshot removal or replacement requires an explicit scope change, not regeneration of manifests or catalogue rows alone.

For rollback of this refresh, restore only the changed tracked documentation and generated index from baseline `e9d71b8`, then remove only this refresh's new documentation/archive files after review. That changes no adapter, trace, service, acquisition state or system clock. Do not use a broad worktree reset on a checkout containing unrelated work.

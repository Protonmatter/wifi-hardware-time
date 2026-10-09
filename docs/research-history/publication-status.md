# Repository and publication snapshot, 2026-10-09

This page records the GitHub state read during the documentation review, separately from experiment and software-qualification claims. It is a dated snapshot, not a continuously updated status feed. Recheck the remote before publication or integration.

[Guide](README.md) · [Timeline](timeline.md) · [Review validation](documentation-review-2026-10-09.md)

## Verified research repository

The GitHub connector and authenticated GitHub CLI identified [Protonmatter/wifi-hardware-time](https://github.com/Protonmatter/wifi-hardware-time) as **public**, with default branch `main`. The initial review fetch and remote-ref query agreed on `e9d71b84365122ff2640e240b20fc1dbb834388a`. Its commit timestamp is 2026-10-08 23:07:32−04:00, or 2026-10-09 03:07:32 UTC. The subsequent corrected atlas merge advanced main to `da4f55e48a368f59ed68ee4427013a83b5c06070`, which is this documentation PR's publication base.

The exact-main [Offline checks run 37877823571](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37877823571) was completed successfully. That hosted result covers the existing merged source, not this uncommitted documentation refresh and not live radio hardware.

## Pull-request history

| PR | State observed | Contribution / interpretation |
|---|---|---|
| [#1](https://github.com/Protonmatter/wifi-hardware-time/pull/1) | Merged | Guarded acquisition, repeatability and versioned evidence |
| [#2](https://github.com/Protonmatter/wifi-hardware-time/pull/2) | Merged | Research library organization and readable workflows |
| [#3](https://github.com/Protonmatter/wifi-hardware-time/pull/3) | Merged | Producer/ownership/vendor investigation and software review |
| [#4](https://github.com/Protonmatter/wifi-hardware-time/pull/4) | Merged | Conditional TSF/QPC bound campaign; historical head `64da8f2` |
| [#5](https://github.com/Protonmatter/wifi-hardware-time/pull/5) | Closed, not independently merged | Causal provider component, incorporated into the integrated stack |
| [#6](https://github.com/Protonmatter/wifi-hardware-time/pull/6) | Closed, not independently merged | Settled timestamp component, incorporated into the integrated stack |
| [#7](https://github.com/Protonmatter/wifi-hardware-time/pull/7) | Merged | Persistent sampler plus reviewed clock-model integration; head `1fc9bed` |
| [#8](https://github.com/Protonmatter/wifi-hardware-time/pull/8) | Merged | Evidence retention, recovery, replay continuity, quantization and versioned summaries; head `d8e9427` |
| [#9](https://github.com/Protonmatter/wifi-hardware-time/pull/9) | Merged | Directly readable diagram artifacts and preview verification; head `afc395b` |
| [#10](https://github.com/Protonmatter/wifi-hardware-time/pull/10) | Merged on October 9 at 01:21:21 EDT | Corrected head `71ccc1d4e3b0a98839b8bddbb089a1687527a332`; merge `da4f55e48a368f59ed68ee4427013a83b5c06070` |

The local Git graph contains historical #5/#6 heads within the persistent baseline; the [integrated review](../overview/pr-reconciliation-2026-10-08.md) explains their reconciliation. Closed component PRs should not be described as missing features merely because their standalone merge timestamp is empty.

PR #10 was corrected and independently reviewed before merge. All ten static previews and future SVG exports now remove inactive control semantics and graph hover/focus affordances, while the interactive HTML remains interactive. Exact-head [push checks](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37887900698) and [PR checks](https://github.com/Protonmatter/wifi-hardware-time/actions/runs/37887904365) passed both `protocol` and `windows-syntax`. Its README/gallery navigation and generated-index contributions are reconciled into this branch.

## Work outside that merged baseline

Private unpublished research findings, source snapshots and detailed interpretations are maintained in the separate private evidence repository. They are not included in this public documentation or archive. Existing source checkouts remain intact.

The documentation branch `docs/research-history-2026-10-09` is based on atlas merge `da4f55e` in an isolated worktree and is submitted as a separate documentation PR. The branch contains public documentation, committed-source archives, newline preservation and archive regression checks; private unpublished findings are excluded. Earlier snapshot statements such as “PR #3 is open,” “integration candidate,” or “not published” remain historical in original reports; the table above supersedes them for this research repository at the stated observation date.

The evidence repository was reverified as private before the separate private documentation publication. This task did not download or revalidate its existing release assets. Downstream host API, diagnostic provider, consumer parity and spectral results quoted by historical research reports retain their original source and validation dates. Their present repository/publication state is not inferred from this repository's main branch.

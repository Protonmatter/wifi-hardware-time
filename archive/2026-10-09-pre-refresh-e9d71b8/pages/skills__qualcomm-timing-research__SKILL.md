---

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/skills__qualcomm-timing-research__SKILL.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).
name: qualcomm-timing-research
description: Continue exact-build Qualcomm Wi-Fi timing and offline vendor-transport research, trace TSF/FTM/RX producers into owned responses, and maintain the evidence handoff to userspace-clock.
---

# Qualcomm timing research

Use this skill for the wifi-hardware-time research repository. Find the checkout
by its Git remote; do not assume a fixed local path or that the active driver,
installed vendor packages or PR state still match an earlier snapshot.

## Start with current evidence

Read `docs/knowledge/current-findings.md`, `assumptions-and-corrections.md` and
`interface-directory.md` under the same knowledge directory. Search the authored
reference index with `python research/evidence/build_knowledge_index.py --find TERM`.
Read the original linked evidence before making a capability claim.

## Research distinctions that change decisions

- Qualify raw observation, host relationship, node synchronization and system
  discipline separately. A successful getter does not enable all capabilities.
- Command completion, diagnostic logging, QUTS reception and hardware sampling
  are different events. A regression residual is not calibrated uncertainty.
- TSF clock/link identity is separate from frame or request/exchange identity.
  Beacon TSF is a peer advertisement; a service transaction ID is not necessarily
  the firmware's token. Preserve units, widths, validity, loss and epoch.
- Copy payloads while their producer's lifetime permits access. A wrapper copy
  does not own pointees. The packet-log cursor can precede payload publication.
- QPST QUTS interfaces coordinate connections. QXDM timestamp accessors can
  fall back to host time. QUTS has distinct DIAG/interpolated, QDSS and host times.
  Inspect schema-specific missing-value rules rather than treating zero as universal.
- The QUTS client has a statically located owned-byte return pattern. The exact
  Wi-Fi-producer connection is still open. Preserve this positive software result
  without presenting it as live acquisition or calibrated accuracy.
- QMSL `FTM_*` means factory test mode unless a particular ranging method proves
  otherwise. Import libraries and component names do not supply runtime implementations.
- Recheck current assembly references: the 2026-10-04 WLAN snapshot is 2.0.79.1 /
  QMSL FastConnect 6.1.360.1; prior snapshots differ. Exact hashes belong in evidence.

## Repeatable work

Use `research/adapters/Invoke-QualcommStaticInspection.ps1` for preview-first
offline snapshots. Read `docs/adapters/static-inspection-runbook.md` for parameters,
hash gates, no-overwrite behavior, private outputs and validation. Never execute a
vendor installer or send firmware commands merely to inspect a package.

Update meaningful findings and corrections, then regenerate the index through
`research/evidence/Update-ResearchKnowledge.ps1 -Apply`. Keep canonical `.mmd`
sources and every embed synchronized. Parse/render diagrams rather than relying
only on source equality. Run the repository's existing tests and focused negative
tests; preserve distinctions between local tests, hosted CI and live qualification.

## Scope and publication

The private campaign remains quarantined unless new reviewed evidence changes
its disposition. Collector or service restart is not proof of firmware drain.
The latest lifecycle authorization is preparation only; do not infer permission
to reset, suspend, reassociate or roam from a documentation task.

Keep proprietary binaries, raw traces, disassembly, endpoint identifiers and
decoding material out of public Git. Publish authored tools, hashes and supported
claims. Research scripts stay upstream; maintained providers belong downstream.
Commit, push, PR updates and merge require the user's actual session authorization;
this skill grants none. Update the existing relevant PR rather than duplicating it.

Refresh saved memory only when the user explicitly requests it, and record dated
findings and unresolved dependencies rather than turning observations into rules.

# Complete-event integration: context map

The application-side byte broker works for fixtures and replay, but the installed Qualcomm driver has no demonstrated complete timing-event return connected to it. The current research can refine the producer's lifetime and acquisition contract. A live exporter additionally needs a supported integration point or an instrumented driver; more consumer code cannot supply that access.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../../research-history/README.md) · [Timeline](../../research-history/timeline.md) · [Previous version](../../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__overview__complete-event-2026-10-05__context-map.md).
<!-- /research-history -->

## Scope and owners

- Repository: `wifi-hardware-time`, branch `investigate-packet-export`; existing
  local changes must be preserved. No commit, push or merge is included.
- Exact ARM64 driver: `qcwlanhmt8380.sys`, INF version `1.0.4374.1300`, SHA-256
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Research owns evidence, acquisition experiments and replay tools.
  `userspace-clock` owns maintained application providers and capability gates.
- Existing broker: `research/export_contract/raw_event_broker.*` plus
  `source_record.py`; user-mode only, fixture/replay provenance.
- Existing static inspector: `research/tsf/inspect_tsf_ingress.py`.
- Existing tests: Python unittest, exact-image fixtures, native ARM64 tests,
  documentation navigation and index/diagram checks.

## Confirmed boundaries

- WMI event `0x5005` is registered to `0x216b00`; the proposed original-event
  copy precedes header mutation in `0x168ce0`.
- Earlier HIF copy points retain transport metadata but require source geometry,
  cache visibility and lifetime proof.
- DMA common-buffer allocation/free are named and traced; live coherency and
  callback-versus-teardown ordering are not qualified.
- The live eight-byte control returns a fixed test literal, not firmware data.
- QUTS has owned client bytes, but no live protocol attributed to this NIC.
- No controlled second node or independent timing reference has been supplied.

## Constraints

The nested IHV control avenue remains deferred. Private acquisition remains
quarantined; reset, suspend and roaming are preparation only. Raw binaries,
traces, disassembly and local device identifiers stay under ignored artifacts.

Continue with [research](route-research.md), [scope](problem-and-scope.md) and
the [engineering plan](engineering-plan.md).

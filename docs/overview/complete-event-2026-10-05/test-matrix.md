# Complete-event integration: validation gates

Each test establishes a specific claim. Exact-image checks validate the repeatable static investigation; native replay tests validate software ownership. A real producer integration needs its own live source, publication and lifecycle evidence before downstream software can accept hardware records. Accuracy is a later, independent measurement.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../../research-history/README.md) · [Timeline](../../research-history/timeline.md) · [Previous version](../../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__overview__complete-event-2026-10-05__test-matrix.md).
<!-- /research-history -->

| Scenario | Level / setup | Expected result and gate |
|---|---|---|
| Unknown or modified driver image | Offline inspector | Reject before offset interpretation; no success receipt |
| Missing/existing output | CLI | Deterministic failure; do not overwrite an existing receipt |
| Selected disable and release calls | Exact owned image | Check instructions/targets and retain hashes; unresolved calls remain explicit |
| Stop versus join | Static + later controlled live test | A cleared callback or disabled interrupt alone cannot qualify all users as finished |
| Firmware association | Live producer | Preserve a demonstrated token/event identity or reject ambiguous association |
| Source overwritten after copy | Native replay, then live producer | Application bytes remain unchanged; software pass alone does not qualify hardware copying |
| Concurrent publication | Native test, then instrumented producer | No partial payload/metadata becomes visible |
| Small output / partial event | Parser and live adapter | Return required length or rejection; no successful truncated record |
| Overflow / unknown source loss | Parser and live adapter | Explicit accounting and quarantine as required; never silently report lossless capture |
| Cancel and close races | Native test, then live adapter | One terminal completion, no freed-buffer access, no missed wakeup |
| Shutdown deadline | Lifecycle test | Failure retains referenced storage; no timeout-driven free |
| Reconnect/reset/suspend/roam | Separately controlled experiments | New continuity decision; software generation alone is not hardware epoch |
| Hardware-to-QPC relation | Fresh sampling experiment | Proven causal/sample bounds, not just callback delivery timestamps |
| Sub-millisecond synchronization | Controlled peers + independent reference | Measured error distribution against a characterized reference |

## Commands for the executable slice

```powershell
python -m compileall -q research tests
python -m unittest discover -s tests -p test_tsf_ingress.py -v
python -m unittest discover -s tests -v
python research/evidence/build_knowledge_index.py --check
python research/evidence/sync_workflow_diagrams.py --check
git diff --check
```

Configure the existing compiler and exact-image fixtures for a zero-skip local
suite. Results and commands for this run belong in the execution record linked
from the [decision log](decision-log.md). Hosted CI is a separate result.

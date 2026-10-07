# Driver memory-ring investigation: tools

These tools inspect the driver file and model a diagnostic ring buffer without reading live kernel memory. They locate candidate return paths and test whether copy rules establish complete records. The current findings do not provide a safe live getter, measured retrieval performance or hardware sampling guarantee.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** The QUTS client is a separate owned-byte return candidate. It does not repair the existing ring publication or temporary-buffer lifetime gaps. See [current findings](../../docs/knowledge/current-findings.md).
<!-- /current-context -->

## Files

| File | Role |
|---|---|
| [inspect_mlo_cache.py](inspect_mlo_cache.py) | Exact-build MLO ranges, bounded constant candidates, lifecycle bindings and native PDB identity; see [findings](../../docs/memory-ring/mlo-cache-and-symbol-search.md). No runtime memory or network access. |
| [inspect_packetlog_return.py](inspect_packetlog_return.py) | Exact-file packet-log return, operations-table, producer and teardown evidence. No device access. See [findings](../../docs/memory-ring/packetlog-return-path.md). |
| [inspect_timing_boundaries.py](inspect_timing_boundaries.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [model_ring_publication.py](model_ring_publication.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](../../docs/memory-ring/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

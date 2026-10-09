# Driver memory-ring investigation: tools

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/research__memory_ring__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These tools inspect the driver file and model a diagnostic ring buffer without reading live kernel memory. They locate candidate return paths and test whether copy rules establish complete records. The current findings do not provide a safe live getter, measured retrieval performance or hardware sampling guarantee.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** The QUTS client is a separate owned-byte return candidate. It does not repair the existing ring publication or temporary-buffer lifetime gaps. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

| File | Role |
|---|---|
| [inspect_mlo_cache.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/memory_ring/inspect_mlo_cache.py) | Exact-build MLO ranges, bounded constant candidates, lifecycle bindings and native PDB identity; see [findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/mlo-cache-and-symbol-search.md). No runtime memory or network access. |
| [inspect_packetlog_return.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/memory_ring/inspect_packetlog_return.py) | Exact-file packet-log return, operations-table, producer and teardown evidence. No device access. See [findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/packetlog-return-path.md). |
| [inspect_timing_boundaries.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/memory_ring/inspect_timing_boundaries.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [model_ring_publication.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/memory_ring/model_ring_publication.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/README.md).
- [Operations and current admission state](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md).
- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) and [migration guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

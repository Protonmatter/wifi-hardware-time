# Driver memory-ring investigation: tools

These tools inspect the driver file and model a diagnostic ring buffer without reading live kernel memory. They locate candidate return paths and test whether copy rules establish complete records. The current findings do not provide a safe live getter, measured retrieval performance or hardware sampling guarantee.

## Files

| File | Role |
|---|---|
| [inspect_timing_boundaries.py](inspect_timing_boundaries.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [model_ring_publication.py](model_ring_publication.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](../../docs/memory-ring/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

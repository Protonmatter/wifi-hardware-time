# Adapter discovery: tools

These tools identify the adapter, inspect its advertised services and read cached management-frame information. They establish which device and driver are being studied, not whether its timestamps are accurate. Use their findings to select the correct backend before attempting a separately qualified acquisition experiment.

## Files

| File | Role |
|---|---|
| [cached_beacon.c](cached_beacon.c) | Probe or native helper; consult its header and the matching research report before use. |
| [device_services.c](device_services.c) | Probe or native helper; consult its header and the matching research report before use. |
| [Get-QualcommAdapter.ps1](Get-QualcommAdapter.ps1) | Read-only adapter/driver identity discovery. |

## Read before running

- [Findings and procedures](../../docs/adapters/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

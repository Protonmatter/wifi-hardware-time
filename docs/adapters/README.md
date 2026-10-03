# Adapter evidence and next experiments

Which adapter can supply usable timing data? The Qualcomm reports describe tested Windows diagnostic paths; the ALFA report identifies Linux source paths and a Windows static candidate. Neither establishes a calibrated clock service. Use these pages to separate observed behavior from the hardware and reference equipment still needed.

TSF (Timing Synchronization Function) is the Wi-Fi timer; a cross timestamp relates a hardware counter to a host counter. Other terms are defined in the [glossary](../glossary.md).

## Reports

| File | Question answered |
|---|---|
| [qualcomm.md](qualcomm.md) | What was reconstructed and tested on the exact Qualcomm FastConnect 7800 Windows build, and what remains quarantined? |
| [axml.md](axml.md) | What timing fields and access paths exist in the inspected ALFA AWUS036AXML packages and mt76 source? |
| [backend-and-reference-next-steps.md](backend-and-reference-next-steps.md) | Which experiment and equipment would resolve each remaining capability or accuracy gap? |

## Research tools

These links locate implementation details; availability of a tool does not authorize or qualify a live operation.

- [Get-QualcommAdapter.ps1](../../research/adapters/Get-QualcommAdapter.ps1): adapter discovery used to select and verify an exact target.
- [device_services.c](../../research/adapters/device_services.c): native service-enumeration and timestamp-query research.
- [cached_beacon.c](../../research/adapters/cached_beacon.c): cached beacon research, distinct from a live clock sample.

Return to the [documentation index](../README.md).

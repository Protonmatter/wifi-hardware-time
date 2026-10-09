# Adapter evidence and next experiments

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__adapters__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Which adapter can supply usable timing data? The Qualcomm reports describe tested Windows diagnostic paths; the ALFA report identifies Linux source paths and a Windows static candidate. Neither establishes a calibrated clock service. Use these pages to separate observed behavior from the hardware and reference equipment still needed.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

TSF (Timing Synchronization Function) is the Wi-Fi timer; a cross timestamp relates a hardware counter to a host counter. Other terms are defined in the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## Reports

| File | Question answered |
|---|---|
| [qmsl-runtime-365.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qmsl-runtime-365.md) | What does the newly installed QMSL 6.1.365.1 provide, how does its worker reach the original-byte callback, and which binding, size and shutdown limits remain? |
| [static-inspection-runbook.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/static-inspection-runbook.md) | How do we repeat package and installed-file inspection with preview, hash gates, no-overwrite receipts and explicit failure handling? |
| [qmsl-diagnostic-queue.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qmsl-diagnostic-queue.md) | What do the supplied QMSL runtime, callback and log getters preserve, and which size, timeout, replay and logging-state limits affect adoption? |
| [qualcomm-archive-transport-findings.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-archive-transport-findings.md) | What do the QPST/QXDM payloads, QUD source and current QUTS client establish about binary return paths and timestamp semantics? |
| [ghidra-workspace.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/ghidra-workspace.md) | How do we inspect the exact ARM64 driver in Ghidra without confusing decompiled code with live execution? |
| [quts-discovery-gate.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-discovery-gate.md) | Why can the native QUTS network discovery path omit this PCI Wi-Fi adapter, and which transport advertisement is missing? |
| [quts-mhi-route-validation.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-mhi-route-validation.md) | What do the MHI patterns actually match, and which live/CI qualification gates remain open? |
| [quts-live-gate-and-commonio.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-live-gate-and-commonio.md) | What did the qualified live query trace establish, and which concrete endpoint-opening code sits beneath CommonIo? |
| [quts-endpoint-writer-and-receive.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-endpoint-writer-and-receive.md) | Where is the endpoint built, how are received bytes copied, and what remains before complete-record and cancellation qualification? |
| [quts-callback-framing-and-wlanlib.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/quts-callback-framing-and-wlanlib.md) | How does the callback reach DIAG framing, and which vendor interface is attributable to the active FastConnect device? |
| [wlanlib-dispatch-and-completion.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/wlanlib-dispatch-and-completion.md) | Which WLANLIB requests return bytes, what owns pending requests, and why does the ART2 event fetch remain unqualified for timing? |
| [qualcomm-management-timing-producer.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-management-timing-producer.md) | Which additional timing fields are declared, when must event data be copied, and does host event history include management RX? |
| [windows-bss-host-time.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/windows-bss-host-time.md) | Where does the Windows BSS host timestamp originate, and can it change without replacing the frame? |
| [qualcomm-bss-serialization.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-bss-serialization.md) | Where are frame bytes, age metadata and vendor context constructed for the Windows BSS list? |
| [qualcomm-management-rx-handoff.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-management-rx-handoff.md) | Does the management-frame path preserve the frame together with candidate local RX TSF metadata? |
| [qualcomm-minimal-transport-contract.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-minimal-transport-contract.md) | Which TSF operations can be implemented now, and why does new live acquisition remain blocked? |
| [qualcomm.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm.md) | What was reconstructed and tested on the exact Qualcomm FastConnect 7800 Windows build, and what remains quarantined? |
| [qualcomm-rx-export-boundary.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-rx-export-boundary.md) | Where does the normal receive path retain, bypass or publish descriptor metadata, and is a complete timestamp export established? |
| [qualcomm-private-output-routes.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-private-output-routes.md) | Which private payloads reach completion, and do statistics, test or interface-service returns carry hardware time? |
| [qualcomm-software-center-timing-leads.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/qualcomm-software-center-timing-leads.md) | What do the installed vendor WLAN tools add, and which RTT buffers and runtime dependencies remain unqualified? |
| [axml.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/axml.md) | What timing fields and access paths exist in the inspected ALFA AWUS036AXML packages and mt76 source? |
| [backend-and-reference-next-steps.md](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/adapters/backend-and-reference-next-steps.md) | Which experiment and equipment would resolve each remaining capability or accuracy gap? |

## Research tools

These links locate implementation details; availability of a tool does not authorize or qualify a live operation.

- [Get-QualcommAdapter.ps1](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/Get-QualcommAdapter.ps1): adapter discovery used to select and verify an exact target.
- [inspect_private_exports.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/inspect_private_exports.py): offline, exact-build receipt for selected private output routes; no device access.
- [device_services.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/device_services.c): native service-enumeration and timestamp-query research.
- [cached_beacon.c](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/cached_beacon.c): cached beacon research, distinct from a live clock sample.

Return to the [documentation index](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/README.md).

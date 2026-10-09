# Qualcomm FastConnect 7800 Windows research

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__adapters__qualcomm.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

What timing data does this Qualcomm adapter expose on Windows? Exact-build experiments recovered diagnostic counter reports and aggregate ranging results, while standard timestamp queries failed. Private acquisition remains quarantined after later completion-deadline failures; these findings do not establish a safe clock service, packet timestamp delivery, or calibrated accuracy.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** Later archive and installed-file inspection located QUTS client-owned byte returns and corrected vendor package/version assumptions; exact adapter-to-producer association remains open. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

TSF (Timing Synchronization Function) is the Wi-Fi timer; FTM (Fine Timing Measurement) is a ranging exchange. ETW is Windows event tracing. An RVA is an address relative to a binary image. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) for IOCTL, SoC and other driver terms.

Current status: private acquisition remains quarantined. The later
[scan comparison](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/scan-tsf-results-2026-10-03.md) reproduced
scan-associated TSF reports without private requests, while failing its original
completion deadline. The [timing-boundary investigation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/memory-ring/timing-boundary-investigation-2026-10-03.md)
locates RX PPDU diagnostic fields and diagnostic/recovery ring consumers; it does
not establish a safe live getter or clock conversion. Use the
[qualification ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/gap-closure-ledger.md) alongside the original
protocol reconstruction below.

## Contents

- [Exact inspected profile](#exact-inspected-profile)
- [Recovered and partly tested path](#recovered-and-partly-tested-path)
- [Observed results](#observed-results)
- [Other paths and limits](#other-paths-and-limits)

## Exact inspected profile

- PCI vendor/device: `17cb:1107`.
- Driver: `qcwlanhmt8380.sys`, ARM64, version `1.0.4374.1300`.
- Reported NDIS: 6.89; WiFiCx: 1.2.
- SHA-256: `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.

The private probe checks this exact hash, architecture, command records, and TSF jump table. Version text alone is insufficient. A different binary requires a new qualification pass.

## Recovered and partly tested path

```text
QcomWifi control device
  -> private IOCTL 0x00220182
  -> named-command parser with MAC selector
  -> host getter or TSF operation wrapper
  -> TSF firmware command 0x5012

firmware report event 0x5005
  -> registered TSF report handler
  -> internal timing/delay processing and diagnostic logging
```

An IOCTL is a control request sent to a driver. The command table has `tsf_auto_report` (selector 229) and `tsf_read_value` (selector 230). These selectors are not top-level IOCTL codes. The shipped probe does not expose automatic reporting, raw registers, or reset.

For the tested legacy request, input is 128 bytes: a 20-byte command-name field, six-byte MAC selector, two padding bytes, and a 100-byte argument block. Integer count is at argument offset 0 and integer values begin at offset 4. The output is another 100-byte argument block. The pure request builder enforces this layout.

Static locations, expressed as RVAs in the exact binary:

| Location | Meaning |
|---|---|
| `0x33df3c`, `0x33df58` | TSF command records |
| `0x124c00` | Private set-command dispatcher |
| `0x1263b4`, `0x1263c8` | TSF branches |
| `0x18e910`, `0x18e9e0` | Registered operation wrappers |
| `0x1955e8` | TSF command builder |
| `0x216b00` | Firmware TSF report handler |
| `0x12e4f0` | WDI IHV request handler |

These RVAs are evidence references, not runtime call targets.

## Observed results

The original local harness successfully opened and closed the control device. A host debug-level query returned integer 2; a host debug-output-mode query returned 0. One TSF read request with argument 1 completed at the IOCTL level but returned no timestamp arguments. Driver acceptance does not prove firmware report delivery.

The wrapper selects firmware action 3 for the fixed positive argument. A public Qualcomm firmware definition labels action 3 `TSF_TSTAMP_READ_VALUE`. The public header is a semantic reference from a different source revision, not proof of firmware parity.

The firmware report handler processes TSF, global-TSF, and SoC timer fields. A subsequent elevated capture with the original local harness observed one READ_VALUE command and one report matching the vdev (virtual wireless interface). The IOCTL returned 100 zero bytes; the TSF and SoC counter values appeared separately in ETW. The raw trace clock was QPC at 10 MHz, and the report log followed observed IOCTL completion by 552.9 microseconds. The observed host request bracket was 57.9 microseconds.

These are host-observed intervals, not firmware sampling instants or timing accuracy. A later live run of the public wrapper observed 12 matching reports over 14.39 seconds. TSF advanced, while the SoC field stayed constant. Eleven report logs followed userspace's completion observation and one preceded it; there is no exposed firmware transaction identifier.

An additional 11-request experiment interleaved three QTIMER_CAPTURE actions (4) with READ_VALUE (3). Each action 4 refreshed the SoC field; subsequent action-3 reads reused it while TSF continued advancing. Action-selection instructions at RVA `0x18ea00` are checked by the shared protocol guard. This establishes refresh/cache behavior in the tested run, not simultaneous hardware latching. See the [experiment guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/experiments.md) and [validation ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/validation.md).

Standard Windows timestamp queries returned error 23 / ERROR_CRC in both Python and native ARM64 callers. Output fields from failed queries were not interpreted. The error does not identify a hardware fault or conclusively establish unsupported timestamping.

## Other paths and limits

- Network monitor mode was reported unsupported by this installed driver.
- Six FTM operations to one associated AP succeeded through the Windows internal request path, firmware responses, and callback results. Their ranging accuracy remains unqualified. This path also pins the exact Windows DLLs; it is not a stable public API.
- `read_reg` routes to an athdiag QMI read, but its safe memory-type/address map remains unqualified. The public tool rejects it.
- Spectral-related names are present; a working spectral data API was not established.
- `get_timer` calls `ExQueryTimerResolution`; it is not a TSF getter.
- No driver, firmware, or raw disassembly is distributed here. Reproducing static findings requires the exact legitimately obtained binary.

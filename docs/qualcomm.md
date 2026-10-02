# Qualcomm FastConnect 7800 Windows research

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

The command table has `tsf_auto_report` (selector 229) and `tsf_read_value` (selector 230). These selectors are not top-level IOCTL codes. The shipped probe does not expose automatic reporting, raw registers, or reset.

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

The firmware report handler processes TSF, global-TSF, and SoC timer fields. No synchronous raw timestamp return or QPC relationship was established. Diagnostic messages use TraceClassic events; the inspected debug-output mode permits ETW output when enabled. An elevated capture was not completed.

Standard Windows timestamp queries returned error 23 / ERROR_CRC in both Python and native ARM64 callers. Output fields from failed queries were not interpreted. The error does not identify a hardware fault or conclusively establish unsupported timestamping.

## Other paths and limits

- Network monitor mode was reported unsupported by this installed driver.
- Local FTM initiator support and the connected AP's responder advertisement were observed; no FTM exchange was performed.
- `read_reg` routes to an athdiag QMI read, but its safe memory-type/address map remains unqualified. The public tool rejects it.
- Spectral-related names are present; a working spectral data API was not established.
- `get_timer` calls `ExQueryTimerResolution`; it is not a TSF getter.
- No driver, firmware, or raw disassembly is distributed here. Reproducing static findings requires the exact legitimately obtained binary.

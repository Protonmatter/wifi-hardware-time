# What the saved TSF trace bytes contain

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__tsf__saved-trace-byte-audit.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Two saved captures contain 88 selected timing-log records. Every selected payload is numeric text followed by one NUL terminator; none has hidden bytes afterward or ETW extended-data items. Inspecting the whole payload therefore does not recover the original firmware event from these records. The new offline tool preserves those bytes and detects trailing, malformed or incomplete data without starting a capture or changing acquisition quarantine.

## Contents

- [Observed result](#observed-result)
- [What this resolves](#what-this-resolves)
- [Reproduce](#reproduce)
- [Validation and limits](#validation-and-limits)
- [Glossary](#glossary)

## Observed result

This audit ran on 2026-10-05 against an earlier latch capture and the first mixed
capture in a saved campaign. It was not a new hardware experiment.

| Property | Saved latch capture | Saved mixed campaign capture |
|---|---:|---:|
| Selected ETW records | 44 | 44 |
| Command / TSF / SoC / delay records | 11 / 11 / 11 / 11 | 11 / 11 / 11 / 11 |
| Selected payload bytes | 2,189 | 2,187 |
| Payload lengths, including terminator | 36–64 bytes | 35–64 bytes |
| Exact numeric text plus one NUL | 44 | 44 |
| Bytes after the first NUL | 0 | 0 |
| Records with extended-data items | 0 | 0 |
| Trace-header events / buffers lost | 0 / 0 | 0 / 0 |

Input SHA-256 values identify evidence without publishing raw traces:

- Latch: `f64b902d1b22c4a2bcec4846c9fd25927d2beda122500e7591db57a067064b23`.
- Campaign: `c3b0c9b6445a3fd8c29abe9e0e2d2bc230ae306d7e50ff5ed16fc053f378a25e`.

Selection is limited to provider `bb6f5b93-635c-47be-816f-e895e77064a8`, event ID
**1**, and the four ASCII text prefixes already used by the numeric TSF decoder.
The `0x5005` firmware selector and ETW event ID 1 are different namespaces.
Zero trace-header loss does not establish zero firmware loss or complete acquisition.

## What this resolves

The old decoder copies `UserDataLength` bytes, then uses `sscanf` to extract
numbers. Parsing can stop at a NUL or after its last conversion, leaving further
bytes uninterpreted. The new exporter preserves the whole selected payload so
the auditor can inspect that remainder.

```text
Original firmware event
        |
        v
Driver selects fields -> formats text -> saved ETW UserData
                                                 |
                         +-----------------------+------------------+
                         v                                          v
                 Older numeric parser                     New byte-level audit
                 extracts numbers                        checks the whole payload
                                                                    |
                                                                    v
                                                    88 records: text + NUL only
```

The left side is supported by the earlier exact-build handler trace at
`0x216b00`; the right side is now checked against saved acquisition bytes. There
is no reverse arrow reconstructing omitted firmware fields. Even a 64-byte ETW
payload is not thereby a 64-byte WMI event: framing and meaning matter.

Expected numeric forms reflect the inspected formatter: global-TSF words and
selected vdev fields can be signed 32-bit decimal, while TSF/SoC words use unsigned
decimal. The audit preserves printed values without assigning clock units or
reconstructing a qualified counter tuple.

This closes the unparsed-tail lead for these selected records. It does **not**
establish that every event, logging mode, provider or driver build lacks binary
event data. The original firmware fields still require a demonstrated producer copy.

## Reproduce

Preconditions: Python 3.11+, installed Visual Studio C tools/Windows SDK, a locally
owned saved ETL and ordinary read access. No elevation or live Wi-Fi is required.

```powershell
powershell.exe -NoProfile -NonInteractive -File research/tsf/Build-TsfTraceBytes.ps1 -Architecture arm64

python research/tsf/audit_trace_bytes.py `
  --exporter artifacts/tsf-trace-bytes-arm64/export_tsf_trace_bytes.exe `
  --etl 'C:\private\saved-tsf.etl' `
  --output artifacts/tsf-byte-audit-new
```

- Use `-Architecture x64` and the matching output path on an x64 host.
- `--etl`: saved file, at most 64 MiB, hashed before and after reading.
- `--exporter`: locally built, trusted exporter; its hash is retained and checked.
- `--output`: **new** private directory; its parent must exist. Existing output
  is rejected. This is not a device path or ETW session name.
- `selected-userdata.jsonl`: complete selected payload hex and ETW metadata.
- `audit.json`: hashes, lengths, numeric fields, trailing-byte counts, trace loss
  and explicit false clock-qualification flags.
- `native-stderr.txt`: read errors. Partial output remains after failures.
- Bounds: 60-second subprocess timeout, two million events, 10,000 selected
  records, 4 MiB selected payload and 16 MiB exported JSONL.
- Exit 0 means the offline audit completed; zero selected records is inconclusive.
  Exit 1 is failure; argument errors use exit 2. Never admit partial output.
- Rollback: no system action. Preserve evidence, then remove only the chosen
  generated directory. Keep raw captures and exported bytes out of public Git.

## Validation and limits

The ARM64 exporter builds with `/W4 /WX`, passes its classifier self-test and was
run against both saved captures. Tests cover binary data after NUL, padding,
signed/unsigned bounds, truncated text, duplicate records/keys, unknown fields,
incomplete native completion, loss and empty selections. The Windows test also
builds the exporter and exercises its non-acquiring entry points.

The configured repository suite passed **332 tests with zero skips**, including
the native compiler and pinned driver/Windows-image tests. An initial focused
run lacked the MSVC environment; the configured run closed that skip. All 44
selected latch records match the archived numeric output in values and ETW
timestamps. Reanalysis with the final auditor produces the same results.

Microsoft defines `UserDataLength` as the byte length of `UserData`; the ETW header
timestamp describes logging time. This audit does not treat it as a hardware
sample. [EVENT_RECORD documentation](https://learn.microsoft.com/en-us/windows/win32/api/evntcons/ns-evntcons-event_record).

Extended-data contents are not exported. Their count is preserved; both tested
selections have count zero. Inputs must remain stable during reading; hashes
detect ordinary changes but are not source attestation. No new capture, register
read, driver patch, provider enablement or clock change occurred. Quarantine
remains unchanged. These results preceded publication; revision-specific hosted
checks are tracked in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3).

The next hardware dependency is an owned original event copied at the
[source boundary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#ownership-and-the-copy-point)
and returned through a demonstrated operation. A hex view of formatted logs does
not add missing fields or establish fresh hardware-to-QPC sampling.

## Glossary

- **ETL:** saved Windows event-trace file.
- **ETW:** Event Tracing for Windows, which delivers these log records.
- **UserData:** payload placed in an ETW event by its provider.
- **NUL:** zero byte often used to terminate a string.
- **WMI event:** here, a Qualcomm firmware message; not Windows Management Instrumentation.
- **QPC:** Windows' high-resolution performance counter, separate from the radio clock.

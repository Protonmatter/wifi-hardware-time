# Qualcomm private outputs: radio statistics and a test payload

Two private return paths were traced in the exact Qualcomm driver file. The receive-statistics getter formats radio measurements and can refresh internal state; the device-service test getter returns fixed sample bytes. Neither inspected path supplies a complete hardware timestamp record. These findings narrow the search without authorizing another live command or establishing timing accuracy.

## Contents

- [Scope and terms](#scope-and-terms)
- [Receive-statistics getter](#receive-statistics-getter)
- [Device-service test getter](#device-service-test-getter)
- [Reproduce the offline evidence](#reproduce-the-offline-evidence)
- [Decision and remaining work](#decision-and-remaining-work)

## Scope and terms

- **Build:** Qualcomm FastConnect 7800 ARM64 driver `1.0.4374.1300`.
- **SHA-256:** `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- **Static inspection:** read the driver as a file; do not execute its functions.
- **RVA:** relative virtual address, an offset within the driver image. These
  offsets identify evidence for this build, not callable public interfaces.
- **Getter:** a command intended to return information. Its name does not prove
  that it avoids internal changes, requests or waits.
- **Payload:** the data carried inside a response envelope.
- **RX:** receive. **MCS:** modulation and coding selection. **GI:** guard interval
  between symbols. **NSS:** number of spatial streams. **RSSI:** signal strength.
- See the [glossary](../glossary.md) for clock and acquisition terminology.

The findings below cover selected handlers and their immediate return paths.
They do not establish the absence of another export elsewhere in the driver.

## Receive-statistics getter

The named-command record at RVA `0x33e038` identifies `get_rx_stats`, selector
250. The getter dispatcher at `0x124440` reaches formatter `0x127e88` through
the call at `0x124908`.

| Stage | What the inspected code does | Consequence |
|---|---|---|
| Output check | Requires the extended output layout marker `0xaa` and at least `0x100` bytes in its declared text capacity | The legacy fixed output layout is not sufficient for this handler |
| Refresh | Calls helper `0x308f0` with mask `0x7f` before formatting | This is not simply a copy of a passive timestamp record |
| Radio fields | Reads context fields and formats bandwidth, MCS, GI, modulation, NSS and two RSSI values; the rate slot is literal `NA` | The inspected format contains radio statistics, not a raw clock value or packet identity |
| Text return | Appends text through `0x124110`; a conditional second-context path can append another result | Returned text has no established packet/exchange or epoch attribution |
| Final helper | Calls `0x308f0` again with mask zero and the low byte of a request argument | Request arguments can select additional helper behavior; this route is not added to the live allowlist |

The refresh helper has concrete state effects:

- Writes selection flags at context offset `+0x9a60` and copies cached signal
  fields into its statistics area.
- Checks host-derived cache-age values before selected refresh operations.
- Can reset an event, call statistics-request helper `0x30220`, and wait through
  `KeWaitForSingleObject` when that helper reports a pending operation.
- Can call another helper at `0x303f8`. A nonzero argument also reaches an
  additional indirect callback. Those downstream operations are not qualified
  here for live invocation.

These facts establish that calling the getter can do more than read existing
bytes. They do not establish every firmware side effect, a live latency bound,
or that every invocation refreshes its values. Internal host cache times are not
hardware sampling timestamps and are not exported by the inspected format.

## Device-service test getter

The handler at RVA `0x12a2a0` labels its opcode-1 path as a test-pipeline GET.
Its payload construction is explicit:

1. Load eight fixed bytes from literal storage at `0x12a4b0`. The bytes are the
   integers 1 through 8 in order.
2. Pass the eight-byte payload to the response serializer at `0x1618c0`.
3. Pass the serialized result to common completion helper `0x13a890`.
4. Free the serializer's temporary output after that helper returns.

The inspected common helper checks caller output capacity and copies a successful
nonempty payload after a 16-byte response header. It then follows framework
completion or context-cleanup branches. This identifies a return mechanism in
the binary; it does not prove that an application can successfully invoke it on
the current adapter.

There is no hardware-counter or FTM-buffer read in the direct GET payload
construction. Even if a future transport test returned these bytes successfully,
that would establish delivery of test data, not a hardware clock source.

## Reproduce the offline evidence

Use the existing Python dependencies and a locally owned copy of this exact SYS
file. Normal read permission is sufficient; elevation is not required by the
inspector. It reads at most 16 MiB plus one rejection byte and never loads the
driver or opens a device handle.

```powershell
$env:WIFI_TIME_DRIVER_FIXTURE = 'C:\path\to\owned\qcwlanhmt8380.sys'
python research/adapters/inspect_private_exports.py `
  --driver $env:WIFI_TIME_DRIVER_FIXTURE `
  --output artifacts/private-export-static.json
python -m unittest discover -s tests -p test_private_export_routes.py -v
```

- `--driver`: existing exact-build driver file. Other hashes are rejected before
  route extraction.
- `--output`: new JSON receipt; an existing file is never overwritten. Choose a
  new filename for a repeat run.
- **Output:** eight selected range hashes, command identity, selected direct-call
  offsets, three imported helper names and the fixed-payload comparison.
- **Interpretation:** range hashes and instruction matches support repeatability.
  The behavioral conclusions above come from manual control/data-flow inspection;
  the tool is not a general disassembler or a proof of all reachable behavior.
- **Exit codes:** 0 means offline inspection completed; 1 means rejected input or
  file failure; 2 means invalid command-line usage. Zero is not live qualification.
- **Rollback:** no device/system state changes. The only persistent output is the
  requested local receipt.

For this investigation, fresh installed `dumpbin /disasm:nobytes` output matched
the saved exact-build disassembly in all eight selected ranges: 932 instruction
or literal lines. The locally retained range-validation and inspector receipts
have identical range hashes. Proprietary disassembly and the driver remain out
of Git; the reusable inspector emits neither their bytes nor the driver path.

## Decision and remaining work

- Keep `get_rx_stats` outside the existing live command allowlist. Its output
  does not meet the timestamp need, and its refresh behavior needs separate
  qualification before any proposed use.
- Do not mistake the test-service serializer for an existing hardware exporter.
  A driver change that substitutes hardware records would need its own ownership,
  completion, concurrency and identity design.
- Continue searching only where a concrete producer-to-return path can be traced.
  The unresolved [normal RX boundary](qualcomm-rx-export-boundary.md) and
  [FTM ownership boundary](../ftm/ftm-buffer-ownership-and-identity.md) describe
  the records and lifetimes any candidate must preserve.
- The [complete-record gate](../evidence/raw-timestamp-export-gate.md) remains
  closed. No private command, trace, register access or hardware experiment was
  performed for this report. No downstream capability is promoted.

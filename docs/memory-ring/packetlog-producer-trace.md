# Where the packet-log bytes come from

The selected packet-log writer receives a firmware HTT packet-log message through Qualcomm's internal event dispatcher. We can now follow its payload, callback registration and return path in the exact Windows driver. We still cannot identify that payload as a complete management frame plus its timing metadata. The next missing evidence is the firmware log-record schema and a safe publication contract, not another generic buffer copier.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** The QUTS client is a separate owned-byte return candidate. It does not repair the existing ring publication or temporary-buffer lifetime gaps. See [current findings](../knowledge/current-findings.md).
<!-- /historical-context -->

## Contents

- [Result and scope](#result-and-scope)
- [The connected producer path](#the-connected-producer-path)
- [Follow the bytes](#follow-the-bytes)
- [Registration and lifetime](#registration-and-lifetime)
- [Separate MLO timing lead](#separate-mlo-timing-lead)
- [What the supplied references add](#what-the-supplied-references-add)
- [Reproduction and validation](#reproduction-and-validation)
- [Next decision](#next-decision)
- [Glossary](#glossary)

## Result and scope

- Inspected: owned ARM64 `qcwlanhmt8380.sys` **1.0.4374.1300**, SHA-256
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Method: Ghidra 12.1.4, Windows compiler specification, decompilation,
  cross-references, ARM64 instruction review and exact-file byte comparisons.
- Research baseline: `ebe1f21158d0b1f6ec00d7782217a0d77f0c19ca` plus local research.
- This is a **conditional static connection**. No runtime subscription, callback
  invocation, firmware record or private request was observed in this pass.
- The original open Ghidra workspace was preserved. This investigation used the
  separate private project `PacketlogProducer_1300`.

The `wdi_*` names below belong to Qualcomm's internal data-path event mechanism.
Do not confuse event `0x101` with a Windows WDI indication or WMI firmware event
`0x7001`; those are different dispatch namespaces.

## The connected producer path

```text
Firmware HTT receive buffer
  |
  | message type 0x08, named HTT_T2H_MSG_TYPE_PKTLOG
  v
HTT handler: skip the first 4-byte transport word
  |
  | remaining pointer -> internal event 0x101
  v
Qualcomm data-path dispatcher
  |
  | if the selected callback is initialized and subscribed
  v
process_offload_pktlog
  |
  | interpret a 16-byte log header, reserve storage, copy payload
  v
Binary packet-log ring -- selected reader --> IHV result --> completion
  ^
  | complete-record publication and snapshot lifetime still unqualified

Separate route:
WMI management event 0x7001 -> decoded header/frame/optional timing slots
                            -> management callback -> metadata reduction

No connection carrying that complete WMI tuple into the log was established.
```

Arrows show selected code paths, not a measured execution. The ring-to-completion
portion is detailed in [the return-path report](packetlog-return-path.md).

| Stage | RVA | Exact-build evidence |
|---|---|---|
| Register HTT receive callback | `0x1fefc8` | Places `0x1fc970` in the receive-callback record passed to `0x1b6e08` |
| Receive HTT message | `0x1fc970` | Reads the first byte of the buffer's current data view as message type |
| Classify type | `0x1fcf48` | Names type `0x08` `HTT_T2H_MSG_TYPE_PKTLOG` |
| Select packet-log event | `0x1fcc20..0x1fcca8` | Type 8 selects payload at current data `+4`, event `0x101`, then calls `0x1fb730` |
| Dispatch to subscribers | `0x1fb730` | Resolves a device context, selects its subscription list and calls each registered callback |
| Selected callback | `0x217300` | Event `0x101` passes its payload pointer to `0x220e90` at `0x2173b8` |
| Reserve and copy | `0x220e90` | Builds selected log-header fields, reserves through `0x220ac0`, then copies payload at `0x220f80` |

These RVAs are offsets, not live pointers. Add `0x140000000` to navigate this
Ghidra project; for example, the HTT handler is at `0x1401fc970`.

## Follow the bytes

Let **H** be the start of the HTT buffer's current data view and **P = H + 4**.
These symbols describe pointers in the selected code, not an approved API.

- `H[0] == 0x08` selects this packet-log branch.
- `P` enters internal event `0x101` as the payload argument. At the callback
  call, the ARM64 instructions put this pointer in `x2`; the callback moves it
  into `x1` for `process_offload_pktlog`.
- The writer takes the copy length from the upper 16 bits of the 32-bit word
  at `P + 4`, constructs a local header, and copies that many bytes from `P + 16`.
- The ring receives transformed header fields and copied payload. It does not
  retain the complete HTT transport envelope through this operation.
- The previously inspected reservation adapter narrows the candidate metadata
  at input-header `+8` to 16 bits. A timestamp interpretation must account for
  that reduction; integer width alone supplies no units or clock identity.

The selected forwarding and copy operations do not decode a Beacon, Probe
Response, WMI management header or optional reordering/timing block from those
payload bytes. Firmware could define additional record types inside the opaque
payload, but this analysis has not recovered their schema or observed them.
Therefore **a copied log payload is not yet a complete timestamp record**.

## Registration and lifetime

### Callback binding is conditional

- Initializer `0x216cd0` writes callback `0x217300` into subscription object
  `0x3bd7a0` when its selected context's byte at `+0x54` is zero. The runtime
  value was not inspected.
- `wdi_pktlog_subscribe`, `0x217530`, subscribes that object to event `0x101`
  when the requested mask intersects `0x10d`. This does not mean logging is active.
- Bridge `0x217150` obtains a common-operations table and invokes slot `+0x88`.
  The selected constructor installs root table `0x392ac0`; its `+8` pointer is
  `0x3925f0`, whose `+0x88` entry is `0x1fb880` (`dp_wdi_event_sub`).
- The subscription function links the object into the device's list at
  `+0x5ea8`, indexed by event minus `0x100`.
- Dispatcher `0x1fb730` traverses that list. A subscription object's `+0` is its
  callback, `+8` its callback context and `+0x10` the next subscription.

The dispatcher also has a fallback from event `0x102` to the `0x108` slot when
the former has no subscriber. The same number or an RX-labelled routine is
insufficient to infer a record format without tracing the actual path.

### The original buffer is temporary

The HTT handler proceeds to its release/decrement path after dispatch. One
selected branch calls the buffer release helper `0x6ae0` at `0x1fcf1c`; another
decrements a reference count. A saved pointer does not grant new ownership.

The packet-log writer makes a byte copy during the callback, but the ring's
publication and teardown concerns remain. In particular, the reservation cursor
can advance before payload copy, and the selected readback function has no
demonstrated matching snapshot protocol. The new producer trace does not fix
those limitations or establish which physical source a later global lookup uses.

## Separate MLO timing lead

The exact message-name routine identifies type **`0x28`** as
`HTT_T2H_MSG_TYPE_MLO_TIMESTAMP_OFFSET_IND`. The HTT handler routes it to
`0x1fd7e0` at `0x1fcd50`.

That selected handler:

- Dispatches internal event `0x10c` with the original message pointer.
- Copies selected fields into a device-associated region at `+0x5ff0..+0x600c`.
- Surrounds those writes with calls matching the inspected WDF spin-lock
  acquire/release slots.

This is a useful **separate lead** for relationships between radio links.
The packet-log callbacks inspected here do not handle event `0x10c`. Its name
and cached words do not establish field units, validity, participating clocks,
reset behavior, application export or a QPC relationship. Do not interpret it
as a working cross timestamp or enable a clock capability from it.

The [MLO cache follow-up](mlo-cache-and-symbol-search.md) now matches a pinned
Qualcomm reference schema to these stores and traces initialization, ordering
and detach. No independent reader or matching native PDB was recovered; the
schema match does not qualify live firmware contents or a host-clock relation.

## What the supplied references add

- **Microsoft ARM64 debugging:** relevant to a future controlled debug session.
  For remote kernel debugging, the debugger's host architecture and the target
  architecture must be distinguished. The reference does not itself enable
  access to this driver or the Wi-Fi firmware processor.
  [ARM64 debugging](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/debugging-arm64).
- **Qualcomm Windows-on-Snapdragon overview:** the supplied page covers app
  development and ARM64/ARM64EC/Arm64X interoperability. It provides architecture
  context, not this WLAN event ABI or a private timing-return interface.
  [Qualcomm overview](https://docs.qualcomm.com/nav/home/core-app-overview.html?product=1601111739937064).
- **.NET Portable PDB:** describes symbols for managed .NET scenarios. This
  driver has PE machine `0xaa64`, no CLR directory and a native RSDS debug entry.
  The article does not supply or reconstruct the driver's native symbols.
  [Portable PDB design](https://github.com/dotnet/designs/blob/main/accepted/2020/diagnostics/portable-pdb.md).

The exact native symbol identity is `qcwlanhmt8380.pdb`, GUID
`DFE3ADE4-EB12-4165-B34A-3AAA18371C82`, age `1`. A HEAD query for the corresponding
uncompressed file at Microsoft's public symbol endpoint returned **404** on
2026-10-04. That one lookup does not prove that the symbols are unavailable from
all stores or from Qualcomm.

One additional Microsoft reference directly helps this analysis:
[classic ARM64 call checkers](https://learn.microsoft.com/en-us/windows/arm/arm64ec-abi#call-checkers).
The guarded target is held in `x15`; a separate checker runs before the target
call. At `0x1fb804..0x1fb828`, the instructions establish callback arguments more
reliably than Ghidra's unresolved `extraout_x15` C expression. This driver uses
the classic ARM64 pattern; the reference also describes a different ARM64EC
pattern, which must not be substituted here.

## Reproduction and validation

Use the [Ghidra setup guide](../adapters/ghidra-workspace.md) and
[TraceQualcommPacketlog.java](../../research/adapters/ghidra/TraceQualcommPacketlog.java).
The script reads the imported program, exports one level of references and
decompiles the containing functions. It does not change program labels, call
prototypes, the driver or the device.

With the portable JDK configured, run from the repository root. Close the
specified project before headless processing; the original GUI project may
remain open if it is a different project.

```powershell
$ghidraRoot = 'C:/Tools/ghidra_12.1.4_PUBLIC'
$repoRoot = (Get-Location).Path
& "$ghidraRoot/support/analyzeHeadless.bat" `
    "$repoRoot/artifacts/ghidra/projects" PacketlogProducer_1300 `
    -process qcwlanhmt8380.sys -noanalysis `
    -scriptPath "$repoRoot/research/adapters/ghidra" `
    -postScript TraceQualcommPacketlog.java `
    "$repoRoot/artifacts/ghidra/reports/producer-new" `
    220e90 217300 217270 216cd0 217530 217150 1fb730 1fb880 1fc970 1fefc8
```

- Preconditions: exact imported hash, ARM64 Windows language/compiler, original
  image base; existing project and output parent; a new output directory.
- Parameters: output directory followed by **1–32 space-separated hexadecimal
  RVAs without `0x`**. Do not pass a comma-separated argument through the batch
  launcher; it split that argument in the first attempt, which was rejected.
- Bounds: at most 256 references per seed, 96 exported functions, 30 seconds per
  decompilation and 4,096 instructions per function. Truncation is recorded.
- Outputs: `xrefs.tsv`, `receipt.tsv`, private `*.asm.txt` and `*.c.txt` files.
  Read the receipt and log: Ghidra can return exit 0 despite a script error.
  The 2026-10-06 review correction rejects seeds that resolve no functions before
  creating output. A success marker requires a nonempty resolved selection;
  per-function instruction truncation and decompiler warnings still need review.
- Permissions: ordinary file access. No elevation or live capture.
- Rollback: close the research project and remove only its local output/project
  if no longer needed. Keep proprietary exports out of Git.

Five successful local export passes covered **27 distinct functions**. All
receipts reported zero decompilation failures and no instruction truncation.
Byte comparison checked **4,826 exported instruction rows**, representing
**3,996 unique addresses**, against the exact owned image. This checks exported
bytes, not the correctness of every inferred C type or runtime behavior.

The [offline packet-log inspector](../../research/memory_ring/inspect_packetlog_return.py)
now includes 32 selected range hashes, the recovered subscription-table pointers,
direct branches and explicit unqualified capability flags. Its five tests passed
with the owned driver fixture. Ghidra's Java execution is local qualification;
the hosted Python/PowerShell workflow does not execute it.

The new exporter also rejected a wrong image hash, an out-of-image seed and an
existing output directory; the existing receipt remained unchanged. Syntax
checks and the full local suite passed: **211 tests, no skips**, with the owned
driver/Windows fixtures and ARM64 native harness enabled. No hosted run for
that local checkpoint is claimed. The later
[publication checkpoint](../evidence/owned-event-extension.md#validation-and-operation)
records hosted results for the published changes.

## Next decision

1. Decode the firmware packet-log record types and their actual producer
   contracts. Require a frame identity, timing identity and complete payload
   before considering this path for acquisition.
2. Trace readers/exporters of the separate MLO offset cache. Establish its
   schema and clock domains without treating a link offset as host correlation.
3. If the log does not preserve the needed tuple, use the demonstrated management
   callback boundary for a vendor-supported or instrumented owned exporter.
4. Keep live admission closed until publication, lifetime and source identity
   are established. Hardware/QPC correlation remains a separate requirement.

## Glossary

- **HTT:** Qualcomm host/target transport used here for data-path messages.
- **WMI:** Qualcomm WLAN firmware/control messaging, separate from HTT and from
  Windows Management Instrumentation.
- **Subscription:** a callback registered to receive one internal event type.
- **MLO:** multi-link operation. A relationship between radio-link clocks is not
  automatically a relationship to Windows time.
- **RSDS / PDB GUID and age:** the binary's debug-record format and identity used
  to find a matching native symbol file.
- **QPC:** Windows QueryPerformanceCounter, a host performance-counter clock.
- **Static evidence:** what the inspected file's code and data show; it does not
  show which branches ran on the current hardware.

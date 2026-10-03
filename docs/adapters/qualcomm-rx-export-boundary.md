# Where the normal receive path loses a usable timestamp contract

The normal receive path retains the descriptor containing candidate radio timestamps, then moves the packet view past that prefix before handing data toward Windows. This investigation traces that handoff and its metadata. It establishes a capture location to investigate, but no existing userspace export with complete timing and packet identity.

**Terms:** RX means receive. A descriptor is device/driver metadata beside packet
data. PPDU identifies a physical radio transmission; an MSDU is a smaller data
unit that may share that transmission. HAL is the driver's hardware-abstraction
table. An RVA locates code in the on-disk binary, not a callable userspace API.
See the [glossary](../glossary.md).

## Contents

- [Scope and current outcome](#scope-and-current-outcome)
- [Descriptor to Windows packet](#descriptor-to-windows-packet)
- [Completion and packet identity](#completion-and-packet-identity)
- [Alternate fragments and retained descriptor consumers](#alternate-fragments-and-retained-descriptor-consumers)
- [What an exporter still needs](#what-an-exporter-still-needs)
- [Validation](#validation)

## Scope and current outcome

- Date: 2026-10-03, America/New_York.
- Research baseline: `0e866ed6b2409231c100af75a6aef97c6bdd2fa3`.
- Inspected ARM64 Qualcomm driver: 1.0.4374.1300, SHA-256
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Method: owned driver-file inspection, pointer-table resolution and fresh
  bounded disassembly compared with the retained disassembly.
- No device, private request, trace, scan, register access or logging change.

**Outcome:** normal-path reachability is better understood. A complete raw
timestamp acquisition remains unqualified. This is not a whole-driver proof
that every possible export route is absent.

## Descriptor to Windows packet

The selected constructor and hardware table connect these stages:

1. Receive processing holds the original descriptor/data pointer.
2. A completion check rejects unfinished receive descriptors.
3. A branch advances the packet view past the descriptor prefix and padding.
4. Internal helpers retain access to descriptor metadata for classification.
5. The registered OS callback queues the packet.
6. The Windows-facing queue publishes fragment and checksum metadata.

| Evidence location | Observed operation | Supported conclusion |
|---|---|---|
| `0x218d00..0x218d0c`, helper `0x219e80` | Install HAL slot `+0x3c8`; helper writes `0x180` to both length outputs | Prefix length is 384 bytes on this selected initialization path |
| `0x1cb8ac..0x1cb8f4` | Constructor supplies context `+0x60/+0x62` as those outputs | Connects the length helper to the receive context |
| `dp_rx_process_be`, `0x225ffc..0x226070` | Retain original descriptor pointer in register x26 | The known timestamp words are at full-prefix `+0x68/+0x70` at this point |
| `0x226454..0x226474`, `0x22652c..0x226598` | Obtain padding, advance data pointer by context `+0x62` plus padding, subtract from length | Timestamp prefix moves before the packet payload indicated onward |
| `0x2f71c..0x2f724`, table entry `0x3923c0`, `0x1c40ec..0x1c40f4` | Register `OsifReceiveData` (`0x141940`) through the primary operations table into vdev `+0x68` | Resolves the receive callback for this constructor/table path |
| `0x20dac0..0x20dae0` | Invoke the registered callback with context, selector and packet chain | Connects internal receive delivery to the OS-facing callback |
| `0x141bb8`, `0x140d00`, `0x140e88` | Queue, dequeue and call `RxQueueReportOnePkt` (`0x142e40`) | Establishes the normal packet-publication chain |
| `0x142340`, `0x142378`, `0x1423b4` | Request virtual-address, return-context and checksum extensions | No timestamp extension request was found in this inspected queue initializer |
| `0x142e40..0x143210` | Populate fragment addresses/lengths, return context, protocol/checksum fields and queue positions | No transfer of the split timestamp words or hardware/QPC tuple was identified in this publication routine |

The requested extension names are `ms_fragment_virtualaddress`,
`ms_fragment_returncontext` and `ms_packet_checksum`. Their presence is a
specific setup observation; it does not exclude other driver/framework paths.

Advancing a packet pointer does not erase the prefix or establish that all
metadata is discarded. It does mean the indicated payload is not itself an
identified timestamp-record interface. A userspace caller must not read backward
from a packet buffer or treat a kernel pointer as a getter.

## Completion and packet identity

- HAL slot `+0x3f8` resolves to `0x21b530`, which reads full-prefix `+0x84`, bit 31.
  Normal receive processing checks it at `0x2260d8..0x2260f8` and reports
  `MSDU DONE failure` on zero before counting/cleaning up the packet.
- This is a descriptor-completion check. It does **not** establish a
  timestamp-specific valid bit, counter freshness, or safe userspace lifetime.
- A diagnostic identifies a 16-bit `phy_ppdu_id` at full-prefix `+0x0a`.
  Getter `0x2191f0`, installed at HAL slot `+0x210`, reads that halfword.
- That field is an identity lead, not proven persistent uniqueness or one-to-one
  identification of every MSDU. No normal export of the pair of timestamp words
  together with that identifier was established.

The final caller check confirmed registration at `0x218aa8..0x218ab4`, but found
no immediate B/BL reference to the getter in the saved disassembly. Four `+0x210`
load candidates in the selected receive/datapath interval `0x1c0000..0x227000`
were data arguments to other framework calls, not resolved calls through this
HAL slot. Computed/cached table access and other code regions remain outside that
negative result. The getter's presence still supplies no known userspace route.

The [earlier boundary investigation](../memory-ring/timing-boundary-investigation-2026-10-03.md)
uses descriptor-relative `+0x60/+0x68`. Its wrapper adds eight bytes. The
full-prefix locations here are consequently `+0x68/+0x70`; these coordinate
systems must not be mixed.

## Alternate fragments and retained descriptor consumers

The follow-up resolves the specific alternate path and selected consumers that
still receive the original descriptor:

| Path | Observed behavior | Timestamp-export consequence |
|---|---|---|
| `0x20e8a8..0x20ead4` | Normalize packet-chain lengths, build fragment links and return the existing chain head | No timestamp-record allocation or copy identified |
| HAL `+0x2c8` -> `0x21a150` | Fill an eight-byte stack temporary from full-prefix `+0x30/+0x34/+0x36`; caller uses the first halfword for padding/prefix length | Does not read timestamp `+0x68/+0x70` or PPDU ID `+0x0a` |
| `0x1f1980..0x1f19fc` | Advance packet data pointer/offset and adjust length | Changes the indicated payload without publishing descriptor metadata |
| `0x2255d8..0x2257c8` | Read descriptor flags through two resolved HAL getters and pack packet `+0x1a2` | Preserves checksum/protocol flags, not a raw timestamp record |
| `0x20dc70..0x20e34c` | Read twelve resolved HAL classification getters and update counters/histograms | No timestamp/PPDU-identity tuple or original-pointer export identified |

The fifteen selected leaf getters comprise twelve statistics getters, one
fragment-info getter and two checksum getters. Their inspected source fields
are outside the timestamp and PPDU-ID fields. This closes these specific leads,
not every receive mode, constructor or possible private metadata consumer.

The original descriptor remains available internally after payload adjustment;
the normal caller passes it to these checksum/statistics helpers. Do not describe
the prefix as immediately destroyed or infer a safe caller lifetime from that
temporary internal retention.

## What an exporter still needs

- An existing validated return interface, or a separately designed instrumented
  driver path that owns a complete copy before buffer reuse.
- A mapping from each reported timestamp to its packet, physical transmission,
  aggregation/retry context, link and clock epoch.
- Timestamp-specific validity and loss accounting, beyond descriptor completion.
- Counter units, meaningful width, clock source and physical reference instant.
- Defined host observation instants. A later callback or queue notification does
  not become the hardware sampling instant.

The [raw-export acceptance gate](../evidence/raw-timestamp-export-gate.md)
records these requirements and the still-missing hardware acquisition.

## Validation

The initial trace freshly checked 26 bounded ranges containing 1,087 instruction
lines. The alternate-path follow-up checked 21 additional ranges containing 896
instruction lines. All checked lines matched the retained disassembly, and the
final PPDU-ID caller check added six ranges containing 44 matching instructions.
The driver hash was recomputed. Authored notes and receipts remain in ignored
`artifacts/RxExportInvestigation/`; no proprietary bytes or disassembly are
published here.

These checks validate the stated static data flow. They do not produce a live
record, prove timestamp semantics or qualify an application provider.

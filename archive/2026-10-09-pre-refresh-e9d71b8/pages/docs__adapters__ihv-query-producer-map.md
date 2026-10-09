# IHV query routes: payload sources and control effects

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__adapters__ihv-query-producer-map.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

The remaining generic vendor-response path does not turn every “query” into a passive read. Exact-build tracing connects selected queries to scan initiation, channel control, GPIO-output commands and host-state clearing. Other branches return channel/BSS information or PCI configuration data. This narrows the producer search and prevents unsafe probing; it does not establish a complete timing-event return or rule out every other route.

**Disposition, 2026-10-05:** deferred exploratory avenue at the user's request.
Retain this evidence for later; it is not the active clock implementation path
or a proposal for live selector testing. Revisit it when the research scope is
explicitly reopened. The active clock work follows the
[complete-operation qualification rule](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/driver-event-return-integration.md#required-producer-and-response-contract).

## Contents

- [Scope and result](#scope-and-result)
- [Dispatch comes before payload interpretation](#dispatch-comes-before-payload-interpretation)
- [Selected query producers](#selected-query-producers)
- [The GPIO path is an output command](#the-gpio-path-is-an-output-command)
- [Device information is a PCI bus read](#device-information-is-a-pci-bus-read)
- [Consequences for the exporter](#consequences-for-the-exporter)
- [Reproduction and validation](#reproduction-and-validation)
- [Glossary](#glossary)

## Scope and result

Offline follow-up on **2026-10-05**, after publication of `df71460`. All addresses
are RVAs in the owned ARM64 `qcwlanhmt8380.sys`, package version `1.0.4374.1300`,
SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
No nested IHV query, GPIO command, scan, channel operation or register read was executed.

The [live positive control](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/device-service-positive-control.md) already
established an eight-byte return from a different fixed-pattern service. This pass
examines the nested IHV output producer at `0x12e860`; it does not repeat that test
or transfer its qualification to another selector.

## Dispatch comes before payload interpretation

```text
IHV request handler 0x12e4f0
    |
    v
MpNicSpecificExtension 0x11cde8
    | Decode selector + request type + inner buffer lengths
    | Apply special cases BEFORE generic dispatch
    |
    +--> special packet-log / P2P branches
    |
    +--> query type 0 --> 0x39528 --> selected producer
    +--> set   type 1 --> 0x3a5b8 --> selected producer
    +--> method type 2 -> 0x39e38 -> extension re-entry case
    |
    | Some port contexts pass through 0x11ca70 first
    | Removal/recovery and port/OID preprocessing can reject the operation
    v
Actual result count -> serializer -> common completion 0x13a890
```

**Legend:** arrows are statically traced call relationships. “Query”, “set” and
“method” identify dispatch branches; they do not certify the operation's effects.
The selectors below are inner protocol values, not top-level IOCTL numbers or a
live allowlist.

The method dispatcher recognizes `0x0d01035c` and re-enters the extension. The
extension explicitly rejects that same inner selector. This is not an unrestricted
recursive route to arbitrary driver functions. The port forwarder also checks
removal/recovery flags, excludes selected OIDs and calls a port-mode preprocessor.
No live bypass of those checks is established.

## Selected query producers

| Inner selector | Selected destination / behavior | Consequence |
|---|---|---|
| `0xff01010e` | `0x37eb8` constructs a channel list | Channel information, not a complete receive event |
| `0xff000080` | `0x2d6f0`, named `Mp11ScanStart` | Can initiate a scan; not a passive read |
| `0xff000081` | `0x38958` → `0x54ee0`, port-specific BSS enumeration | Cached BSS route; not proof of original RX timing metadata |
| `0xff000084` | `0x3a950`, named `MpSetSpecificChannel` | Forwards zero/nonzero input through channel-control operations |
| `0xff500001`, `0xff500002` | Inner header/body readers; outer dispatcher instead selects log start / combined return | Preserve the previously established selector-precedence distinction |
| `0xff500010`, `0xff500003` | Packet-log stop/configuration helpers | Retain the separate log lifetime and state-change requirements |
| `0xff500014`, `0xff500015` | Write one / zero to host context field `+0x36240` | Concrete host-state writes in query dispatch |
| `0xffb00004` | `0xcb48` → `0x183058` | Submits a GPIO-output command; details below |
| `0xffb00005` | `0x39c10` → `0xd1c0`, then an indirect operation | Returns a reduced one-byte status; downstream operation remains unqualified |
| `0xffb00009` | `0xcbe8` | Clears parts of a host record region and a byte field |
| `0xff50000b` | `0x2f180`, named `MpGetDeviceInformation` | Parent-bus configuration-space read at offset zero |
| `0xff210004` | Sum of two helper results | Reduced counter result, not a complete event |

The clear routine starts at host-object `+0x20f8`, writes 32 zero bytes per
52-byte stride for 100 iterations, then clears the byte at `+0x3548`. The record
schema is not established here. It is incorrect to call this a full-array clear,
a firmware reset or a hardware epoch transition based on those stores alone.

An additional inline selector, `0xff800003`, reaches `0x39ee0`, which builds a
16-byte result from capability-dependent arithmetic and small fields. Other
standard query cases return vendor/address/link information. This pass does not
classify every nested dependency or prove a whole-driver absence of timestamps.

## The GPIO path is an output command

The connection is explicit in the selected ARM64 instructions:

1. Query dispatch calls `0xcb48` at `0x39a30`, passing the caller's first word.
2. `0xcb48` sets the GPIO-number argument to **1**. It produces output argument
   **1 when the input is zero**, otherwise **0**, then branches to `0x183058`.
3. `0x183058`, named `wmi_unified_gpio_output`, allocates a **12-byte command**.
   Its header word is `0x009a0008`: tag `0x9a` with eight value bytes.
4. It writes the GPIO number and output argument, then submits WMI command
   **`0x1e002`** through `0x169678`.

This establishes command construction and submission, not a live change on a
physical pin. Pin routing, electrical availability, firmware behavior and any
relationship to TSF capture remain unknown. A GPIO-output status cannot serve as
a TSF value, a firmware response token or a hardware-to-QPC latch.

## Device information is a PCI bus read

The indirect callback behind `0x2f180` is now attributable:

- `WlanBusNICAllocateSoftwareResources`, `0x437aa8`, requests
  `GUID_BUS_INTERFACE_STANDARD` (`496b8280-6f25-11d0-beaf-08002be2092f`).
- The selected `WdfFdoQueryForInterface` call supplies a 64-byte interface,
  version 1, at device context `+0x360`.
- `0x2f180` loads its context at `+0x368` and callback at `+0x398`, matching
  the `Context` and `GetBusData` members of that interface.
- The selected caller supplies offset zero and its buffer capacity. The wrapper
  supplies data type zero; the query case accepts a returned count of four bytes.

Microsoft defines this interface and `GetBusData` as access to the device's bus
configuration space. This route is not a demonstrated radio-register or TSF read.
See [BUS_INTERFACE_STANDARD](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_bus_interface_standard)
and [GetBusData parameters](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nc-wdm-get_set_device_data).
The scope here is static association; no bus read was performed.

## Consequences for the exporter

- The tested fixed-byte service is a useful return mechanism, but its producer
  remains a literal. It does not gain access to TSF by changing its input.
- The nested IHV query family contains heterogeneous data and controls. Its
  direction bit is not sufficient grounds for a live read profile.
- Channel/BSS results and reduced counters do not supply the complete original
  TSF/RX/FTM event. Previously identified packet-log copying still lacks qualified
  concurrent publication and lifetime guarantees.
- The GPIO route is a hardware-control lead with separate qualification needs;
  it has not been promoted into the acquisition tools.
- A complete-event producer/export connection remains required. Existing timing
  claims and the TSF campaign quarantine are unchanged.

## Reproduction and validation

The new [file-only inspector](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/adapters/inspect_ihv_queries.py)
pins the exact driver, checks 15 selected selector literals, GPIO construction
words and the bus-interface identity, and emits 14 code-range hashes plus selected
direct branches. Role descriptions are manual interpretations; these checks are
not an automatic proof of control flow or an authorization to execute a selector.

```powershell
python research/adapters/inspect_ihv_queries.py `
  --driver '<owned-qcwlanhmt8380.sys>' `
  --output '<new-private-receipt.json>'
python -m unittest discover -s tests -p test_ihv_queries.py -v
```

- Preconditions: Python 3.11+, repository dependencies, owned exact file and an
  existing private output parent. Ordinary file-read rights; no elevation.
- Bound: 16 MiB input. Reject unknown hashes and existing output files.
- Exit codes: `0` receipt written; `1` rejected input/I/O; `2` CLI usage.
- Rollback: remove only the generated receipt if no longer needed; no device
  state is changed by inspection.
- Private Ghidra exports: `artifacts/ihv-producer-map-20261005/`, four completed
  bounded passes, no selected decompilation failures or instruction truncation.
- Focused tests cover unknown/mutable/oversized input, output preservation,
  exact-file routes, altered selector/command/argument/interface bytes and false
  live qualification flags. `WIFI_TIME_DRIVER_FIXTURE` enables owned-file cases.
- Local checks passed: Python compilation; **306 tests, zero skips** with the
  installed ARM64 compiler and exact owned driver/Windows fixtures; documentation,
  workflow/index consistency and Git whitespace checks. The focused new suite
  passed four tests. No new live acquisition or elevation was used.
- At this follow-up's original validation checkpoint, these files were local and
  hosted checks for `df71460` covered the preceding publication. Current publication
  and review status are tracked in the [gap ledger](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/gap-closure-ledger.md).

## Glossary

- **IHV:** independent hardware vendor; here, a nested vendor request/response path.
- **GPIO:** general-purpose input/output pin; pin-control commands are not clock samples.
- **BSS:** a Wi-Fi network's cached discovery information.
- **PCI configuration space:** device configuration managed through the parent bus.
- **MMIO:** memory-mapped device registers; distinct from PCI configuration data.
- **RVA:** a location relative to the loaded image base, used here for static evidence.

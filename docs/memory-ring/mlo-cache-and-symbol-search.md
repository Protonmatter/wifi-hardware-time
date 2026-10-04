# MLO timing cache: field meanings, readers and symbols

The MLO timing message now has a strong public-schema match, including microsecond fields and sub-microsecond clock counts. Its Windows handler updates a device cache, but this pass found no independent reader or application export in the inspected paths. The native symbol search found an identical public driver package, not its PDB. These findings improve the exporter design without qualifying a live clock source.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** The QUTS client is a separate owned-byte return candidate. It does not repair the existing ring publication or temporary-buffer lifetime gaps. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

## Contents

- [Evidence and outcome](#evidence-and-outcome)
- [Field mapping](#field-mapping)
- [Callback ordering and lifetime](#callback-ordering-and-lifetime)
- [Reader search and its limits](#reader-search-and-its-limits)
- [Native PDB search](#native-pdb-search)
- [Reproduce and validate](#reproduce-and-validate)
- [Next useful implementation boundary](#next-useful-implementation-boundary)
- [Glossary](#glossary)

## Evidence and outcome

- Inspected driver: ARM64 `qcwlanhmt8380.sys` **1.0.4374.1300**, SHA-256
  `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
- Baseline: `ebe1f21158d0b1f6ec00d7782217a0d77f0c19ca` plus local research changes.
- Tools: Ghidra 12.1.4, exact-file inspection and pinned public source comparison.
- Offline only: no device open, private request, runtime memory read, firmware
  command, debugger attachment, reset or clock adjustment.

| Question | Result | Evidence limit |
|---|---|---|
| What do the fields probably mean? | Qualcomm's eight-word message and cache structure match the selected Windows masks and stores | Public-reference semantics; actual firmware population remains unobserved |
| Is the callback a cache-update completion notification? | No: it runs before the selected cache update | Static ordering; no measured callback timing |
| Is there an independent cache reader? | None established by this bounded search | Does not exhaust aliases, computed offsets or whole-object copies |
| Does a matching native PDB exist in the checked sources? | None recovered | Not a claim that Qualcomm or another private store lacks it |
| Can this drive a clock now? | No capability promoted | Owned export, freshness, identity, host correlation and accuracy remain open |

## Field mapping

The pinned Qualcomm reference is revision
`05544565496f121bc1ecbf35b55b3b3e1b055022` in Google's published Qualcomm WLAN tree:

- [HTT message declaration](https://android.googlesource.com/kernel/google-modules/wlan/qcom/wcn6740/wlan/+/05544565496f121bc1ecbf35b55b3b3e1b055022/fw-api/fw/htt.h#18266).
- [Reference handler](https://android.googlesource.com/kernel/google-modules/wlan/qcom/wcn6740/wlan/+/05544565496f121bc1ecbf35b55b3b3e1b055022/qca-wifi-host-cmn/dp/wifi3.0/dp_htt.c#2793).
- [Reference cache structure](https://android.googlesource.com/kernel/google-modules/wlan/qcom/wcn6740/wlan/+/05544565496f121bc1ecbf35b55b3b3e1b055022/qca-wifi-host-cmn/dp/wifi3.0/dp_types.h#2563).

This source targets another platform. The matching masks and assignment order
support field interpretation; they do not certify the Windows firmware ABI.
Offsets below are relative to the **32-byte message** and to the Windows device
object, respectively. Units are the reference's units, not live measurements.

| Message offset | Windows cache offset | Reference meaning |
|---|---|---|
| `+0x00` | `+0x5ff0` | Type bits 0–7, physical-device ID bits 8–9, chip ID bits 10–11, MAC clock frequency in MHz bits 16–31 |
| `+0x04`, `+0x08` | `+0x5ff4`, `+0x5ff8` | Low/high words of WLAN global time at the last sync interrupt, in microseconds |
| `+0x0c`, `+0x10` | `+0x5ffc`, `+0x6000` | Low/high words of MLO time offset, in microseconds |
| `+0x14` | `+0x6004` | Additional offset clock ticks for sub-microsecond resolution |
| `+0x18` | `+0x6008` | Compensation: 16 microsecond bits and 10 clock-tick bits |
| `+0x1c` | `+0x600c` | 22-bit compensation period, in microseconds |

Important interpretation limits:

- The cache header is **normalized**: the handler stores its resolved host
  physical-device ID instead of retaining the original message ID unchanged.
- Clock-tick fields provide a resolution lead. They do not establish nanosecond
  accuracy, synchronization to another laptop or an absolute Windows time.
- Signed offset interpretation, adjustment direction, split-word sampling,
  freshness and valid operating modes are not qualified by these stores.
- The 32-byte reference structure has no explicit report sequence or epoch.
  Reserved bits must not be repurposed as validity flags without evidence.
- Keep raw words as well as interpreted fields in any future owned record.

Do not substitute the Linux layout blindly. In the inspected
[Linux v6.13 header](https://github.com/torvalds/linux/blob/v6.13/drivers/net/wireless/ath/ath12k/dp.h#L1456),
the documented chip/frequency bit positions differ, and the diagram and C
structure disagree on the offset low/high ordering. The pinned Qualcomm masks
match the selected Windows instructions more closely. This comparison does not
diagnose the behavior of a running Linux device.

## Callback ordering and lifetime

Read this sequence from top to bottom. All addresses are RVAs in the exact image.

```text
HTT type 0x28 arrives
  |
  v
0x1fd7e0 resolves the destination device
  |
  v
0x1fd904 dispatches internal event 0x10c with the original message pointer
  |  Callback runs here. The cache can still contain the previous report.
  v
0x1fd930 acquires the selected framework lock
  |
  v
0x1fd93c..0x1fd9e4 writes the normalized cache fields
  |
  v
0x1fda08 releases the lock
  |
  v
HTT receive handler later reaches buffer release/reference decrement
```

The public handler uses the same event-before-lock ordering. A future exporter
inside that callback must preserve the event payload during its valid lifetime;
it cannot treat callback entry as proof that the cache contains that event.
The callback argument list does not itself supply a byte count. A bounded copy
still needs an established length/ownership contract at the transport boundary.

The cache belongs to the device object:

- `0x1c3190` allocates `0x6010` bytes and zeroes that allocation at `0x1c31f8`.
  The entire cache fits inside it. Zero-filled storage does not prove a report
  was received or provide a firmware-ready indication.
- Selected main-operations table `0x392280` has deinit wrapper `0x1c3500` at
  `+0x40` and detach wrapper `0x1c3550` at `+0x38`.
- Deinit body `0x1c6428` reaches internal event-list cleanup and sets device
  state `+0xf8` to one. The event dispatcher checks that state before callbacks.
- Detach body `0x1c6688` clears the device-list entry at `0x1c674c` and passes
  the device object to the release thunk at `0x1c675c`.

These paths do not establish how every reset, suspend, reassociation or roaming
operation affects the cache. They establish that its address and contents must
not be treated as persistent across object recreation or detach. No live
concurrency or teardown-quiescence guarantee was tested.

## Reader search and its limits

The new [offline inspector](../../research/memory_ring/inspect_mlo_cache.py)
searches executable sections for selected ARM64 forms: unshifted `MOVZ`,
`ADD` immediate including its page shift, and integer unsigned-immediate memory
offsets. It records candidates rather than declaring them readers.

- **74 sites** contained a value in `0x5ff0..0x600f` in those forms.
- All 74 had exported Ghidra instruction context. Nine are in the known writer;
  the other 65 classify as command/event identifiers, flags or allocation sizes.
- The writer's masked field updates include reads of its own cache words. These
  read/modify/write operations are not independent consumers or export APIs.
- A separate review of the selected `0x10c` immediate sites identified the
  actual event dispatch; other matches were wake-pattern strides or a diagnostic
  line number. No active subscriber or application response was established.

This is **not an exhaustive no-reader proof**. Register-derived offsets,
interior pointers, generic memory copies, alternate implementations and runtime
callback registration can escape this search. The conclusion is that no usable
reader was established, not that reading the cache is impossible.

## Native PDB search

The exact driver requests this native symbol identity:

```text
File:      qcwlanhmt8380.pdb
GUID:      DFE3ADE4-EB12-4165-B34A-3AAA18371C82
Age:       1
Store key: DFE3ADE4EB124165B34A3AAA18371C821
```

Searches on 2026-10-04 produced these results:

| Source | Checked | Result |
|---|---|---|
| Microsoft public symbol store | Exact `.pdb`, compressed `.pd_` and `file.ptr` entries | All three returned HTTP 404 |
| GitHub code index | Exact PDB filename and GUID | Zero indexed results; binary/archive contents are not exhaustively covered |
| WOA Qualcomm reference repository | Pinned `8380_CRD` and `Surface/8380_LAN` subtrees | 7,141 and 979 entries, neither truncated; no loose PDB/DBG/TMF files |
| Matching-version driver cabinet | `Surface/8380_LAN/200.0.13.0/qcwlanhmt8380.cab` | 34 listed files, no PDB; extracted SYS is byte-identical to the owned driver |
| Bounded local inventory | Qualcomm installation, Downloads and this research workspace's source/evidence/side-repo directories | No matching basename |

The [pinned package](https://github.com/WOA-Project/Qualcomm-Reference-Drivers/blob/ad6e472836d40d6ba81855e57bbd3c7c0522735f/Surface/8380_LAN/200.0.13.0/qcwlanhmt8380.cab)
has SHA-256 `1cacae1873570a27b29698e21fb77622ac1ff95d90d313455082ac9d9b232d6f`.
Only the SYS was extracted for comparison; nothing was installed or executed.
The full repository tree request failed to return usable JSON, so the successful
subtree checks above define the repository-search coverage.

No native PDB was recovered or loaded. An older or differently built driver's
PDB must not be force-matched. Microsoft explains that matching symbols identify
the corresponding binary in its [symbol guidance](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/symsrv).

The concrete vendor request is the PDB named above, with that GUID and age,
preferably including private type information and any relevant trace metadata.
The public source improved field enumeration in this pass, but it is not a
replacement for exact native symbols. No vendor message was sent.

## Reproduce and validate

Normal file-read permission, Python 3.11+ and the existing repository dependency
are sufficient for the inspector. Run from the repository root:

```powershell
$env:WIFI_TIME_DRIVER_FIXTURE = 'C:/OwnedDrivers/qcwlanhmt8380.sys'
New-Item -ItemType Directory -Path artifacts/mlo -Force | Out-Null
python research/memory_ring/inspect_mlo_cache.py `
    --driver $env:WIFI_TIME_DRIVER_FIXTURE --output artifacts/mlo/inspection-new.json
python -m unittest discover -s tests -p test_mlo_cache.py -v
```

- Input: exact owned driver, maximum 16 MiB. Unknown builds are rejected.
- Output: native RSDS identity without the private build directory, six range
  hashes, selected direct branches, lifecycle-table bindings and constant sites.
- The output must be new and its parent must exist. Exit 0 means inspected,
  1 means input/I/O rejection, 2 means command-line misuse.
- Keep local outputs, downloaded binaries and full decompilations private.
  Rollback consists of removing only the generated artifact after preserving
  any needed evidence; the inspector changes no device or system setting.
- The existing [Ghidra exporter](../../research/adapters/ghidra/TraceQualcommPacketlog.java)
  produced seven successful local passes covering **42 distinct functions**.
  All receipts reported zero failures and no instruction truncation.
- **13,270 instruction rows**, covering **12,857 unique addresses**, matched
  the exact owned image. This verifies bytes, not all decompiler interpretations.
- Seven focused tests cover native identity formatting, path suppression,
  malformed records, immediate decoding, build rejection, output preservation
  and the exact-image findings. They do not read live memory.
- Python syntax checks and the full local suite passed: **218 tests, no skips**,
  with the owned driver/Windows fixtures and ARM64 native harness enabled.
  These were pre-publication local results. The later
  [publication checkpoint](../evidence/owned-event-extension.md#validation-and-operation)
  records hosted coverage separately.

## Next useful implementation boundary

1. Obtain a vendor-supported complete-event return or an instrumented callback
   with a validated buffer span. Preserve raw message bytes and normalized
   device identity separately before the transport releases the source.
2. Establish firmware validity, clock identities, adjustment direction and
   epoch/freshness rules. A cached last-sync report is not necessarily fresh.
3. If exporting from the cache instead, establish a matching reader lock,
   lifetime pin and event association. An address plus a copy routine is insufficient.
4. Establish hardware-to-QPC correlation independently. No host counter bracket
   is supplied by this MLO message, and sub-microsecond field resolution does
   not demonstrate sub-millisecond synchronization accuracy.

## Glossary

- **MLO:** multi-link operation. Its timing relationships concern radio domains.
- **PDEV:** the driver's physical-device context; its ID is not automatically a
  clock ID or a permanent interface identity.
- **Epoch:** a period during which a counter's identity and continuity hold.
- **RSDS:** the native debug record containing a matching PDB's GUID and age.
- **PDB:** program database, containing compiler/linker symbol information.
- **RVA:** an offset from the driver image base, not a live userspace address.
- **QPC:** Windows QueryPerformanceCounter, a host performance counter.

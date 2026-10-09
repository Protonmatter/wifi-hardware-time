# Where Windows obtains the BSS host timestamp

On the inspected Windows builds, WiFiCx can supply system time when it incorporates a BSS list, or use the driver's age field when a configuration flag requires it. That value reaches the WLAN API's host-timestamp field. A separate link-quality update can refresh the stored time without replacing the frame, so a cached host timestamp is not automatically the receive instant of its peer TSF.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__adapters__windows-bss-host-time.md).
<!-- /research-history -->

## Contents

- [Scope and provenance](#scope-and-provenance)
- [Source and copy chain](#source-and-copy-chain)
- [Cache refresh caveat](#cache-refresh-caveat)
- [Reproduce the offline checks](#reproduce-the-offline-checks)
- [Limits and glossary](#limits-and-glossary)

## Scope and provenance

This is static inspection of owned ARM64 files on 2026-10-03. No running memory,
device, scan, trace, IOCTL, clock adjustment or configuration change was accessed.

| File | Version | SHA-256 |
|---|---|---|
| `wificx.sys` | 10.0.26100.9278 | `7587df7324f4daa70af890edae6e60316b2277a2bb6e21b29ecf6d71f3f3635d` |
| `wlanmsm.dll` | 10.0.26100.9444 | `2e80a99a59d604df8f4c05da0149792acca3f7f50d4fcfae5196493b1d91055b` |

Microsoft public PDB symbols supply function names. Their GUIDs and DBI ages
match each image's CodeView identity. PDB information-stream ages differ and are
recorded separately; no blanket equality of every age field is claimed.
Raw symbols, disassembly and provenance receipts remain under ignored
`artifacts/WindowsBssTimeInvestigation/`.

Installed SDK headers `ksarm64.h`, `windot11.h` and `wlanapi.h` corroborate shared
system-time/tick-count offsets and the public structure fields. RVAs below are
relative to the named image and apply only to its exact hash.

## Source and copy chain

| Stage | Exact selected evidence | Interpretation |
|---|---|---|
| Decode BSS indication | `wificx!CPort::OnBSSEntryNotification`, `0x71c8` | Parses the BSS list and selects one of two feature-dependent incorporation paths |
| Sample Windows time | `CPort::IncorporateBSSEntryList`, `0x6de8`; read at `0x6ea4..0x6eb0` | Reads shared `SystemTime`, directly or through `QuerySystemTime` at `0x1e888`; sampled before the list loop |
| Alternate implementation | Incorporation at `0x66568` calls `CSystem::get_CurrentTime` (`0x28210`) | Same system-time source through the alternate path |
| Select time source | `ReceiveBeaconOrProbe`, `0x9260`, especially `0x94cc..0x9520`; alternate `0x7e958` | For the inspected type-1 manager, nonzero manager byte `+0x2c` requires age optional bit 3; absent age is rejected, present age replaces the supplied time with container `+0x68`. With that byte zero, Windows time is retained |
| Pass time to stored entry | `UpdateBSSEntry`, `0x9be0` | Forwards the selected time through virtual slot `+0x28`; the inspected base-class table at `0xf2770` resolves this to `0x7fa00` |
| Store frame's host time | `SetBeaconOrProbeResponse`, `0x7fa00` | Stores input time at object `+0x2a0` for beacon (`0x7fa80`) or `+0x278` for probe (`0x7fabc`) |
| Build DOT11 result | `FillDot11BSSEntry`, `0x7a318` | Selects the beacon/probe stored time and writes `DOT11_BSS_ENTRY+0x30` at `0x7a354` |
| Build WLAN result | `wlanmsm!IniDot11MsmScanMgrCopyBssEntry`, `0x2eb68` | `0x2eccc..0x2ecd0` copies DOT11 `+0x30` to WLAN `+0x50`, the SDK's `ullHostTimestamp` |

The peer timestamp follows a separate copy: DOT11 `+0x28` to WLAN `+0x48` at
`0x2ecc4..0x2ecc8`, corresponding to `ullTimestamp`.

The source distinction is consequential:

- **Windows-generated path:** an OS observation during BSS-list incorporation,
  not a NIC hardware read. One time value can serve multiple entries in a list.
- **Driver-age-required path:** requires the optional driver-supplied field.
  The selected Qualcomm builder leaves that field absent. It cannot be assumed
  to take this branch successfully.
- The manager flag's runtime value and feature-path selection were not read.
  The trace does not assign a past cached record to one of these branches.
- The generated path reads system time, not QPC or the Qualcomm tick-based
  millisecond value. No conversion between those clocks is established here.

The normal base-class path and selected alternate implementation were traced;
not every possible derived BSS class or complete RPC/service delivery path was
qualified.

## Cache refresh caveat

`CBSSEntry::OnLinkQualityUpdate` at `0x7e310` supplies another writer:

- It tests an unsigned link-quality value against 30.
- Above that threshold, if beacon data exists, it calls `get_CurrentTime` and
  overwrites the beacon host time at `0x7e340..0x7e344`.
- Otherwise, if probe data exists, it updates the probe host time at
  `0x7e354..0x7e358`.
- This routine does not receive a replacement frame argument. These are the same
  stored time fields later selected by `FillDot11BSSEntry`.

Thus the static implementation permits host-time refresh while retaining frame
bytes. It does not prove that this refresh occurred in any retained experiment.
A model must not automatically combine cached peer TSF and host timestamp as a
simultaneously sampled clock pair. This is stronger evidence about the cache's
limitations than inferring precision from its 100-nanosecond representation.

## Reproduce the offline checks

The [exact-image inspector](../../research/adapters/inspect_windows_bss_time.py)
uses existing Python dependencies, requires ordinary file-read permission and
emits hashes for 14 selected ranges. It does not fetch symbols, load a driver or
read any kernel address. Each input is bounded to 16 MiB. The output parent must
exist, and an existing output is never overwritten.

```powershell
python research/adapters/inspect_windows_bss_time.py --wificx C:\Windows\System32\drivers\wificx.sys --wlanmsm C:\Windows\System32\wlanmsm.dll --output artifacts/windows-bss-time-new.json
$env:WIFI_TIME_WIFICX_FIXTURE = 'C:\Windows\System32\drivers\wificx.sys'
$env:WIFI_TIME_WLANMSM_FIXTURE = 'C:\Windows\System32\wlanmsm.dll'
python -m unittest discover -s tests -p test_windows_bss_time.py -v
```

Exit 0 means the exact files were inspected; 1 means input/I/O rejection; 2 means
CLI misuse. A Windows update changing either image requires a new investigation,
not bypassing the hash gate. Tests cover invalid images, oversized input,
no-overwrite behavior, failure without output and optional owned-image fixtures.
There is no device rollback; only local receipts are created.

## Limits and glossary

- **System time:** the Windows wall-clock domain; it is distinct from QPC and
  radio counters.
- **QPC:** the host performance counter used for interval measurements.
- **Age information:** the optional BSS field carrying the driver's host-time
  observation when that contract is used.
- **PDB:** a symbol file used here only to name offline functions and tables.
- **Static chain:** source and copy instructions in exact files; no claim about
  which branch a particular runtime record took.

This result locates a Windows host-timestamp source and copy path. It does not
establish radio event time, simultaneous sampling, receive latency, firmware
semantics, calibrated accuracy or a usable hardware-to-QPC relationship.
See the [Qualcomm cache and serializer trace](qualcomm-bss-serialization.md).

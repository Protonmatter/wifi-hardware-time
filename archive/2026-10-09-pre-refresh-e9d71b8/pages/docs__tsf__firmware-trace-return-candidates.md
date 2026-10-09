# Firmware trace returns: diagnostic messages, CAPTUREH and QDSS

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__tsf__firmware-trace-return-candidates.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

The package's firmware message catalog defines a TSF report containing TSF, QTIMER, TQM and clock identifiers. The driver has a matching version-gated diagnostic decoder and copies incoming diagnostic bytes into a queue before formatting. This is a stronger producer lead, but no such live record or owned application return has been obtained. Separate QDSS file and DMA paths are also mapped; none yet establishes the original `0x5005` event or hardware-to-QPC sampling.

## Contents

- [What changed](#what-changed)
- [The fuller firmware diagnostic report](#the-fuller-firmware-diagnostic-report)
- [CAPTUREH is a separate event](#captureh-is-a-separate-event)
- [QDSS has a firmware-to-file path](#qdss-has-a-firmware-to-file-path)
- [The private DMA control](#the-private-dma-control)
- [Configuration and local observations](#configuration-and-local-observations)
- [Next qualification step](#next-qualification-step)
- [Reproduce and validate](#reproduce-and-validate)
- [Glossary](#glossary)

## What changed

This 2026-10-05 file-only trace uses ARM64 `qcwlanhmt8380.sys`, driver package
`1.0.4374.1300`, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
Addresses below are relative virtual addresses (RVAs) in that image.

| Path | Established statically | Still missing |
|---|---|---|
| Original TSF event | Pre-removal boundary at `0x168d7c`, before normalization and `0x216b00` reduction | An installed producer copy and application return |
| Firmware diagnostic report | Catalog entry 25950 names counters/IDs; WMI diagnostic handler allocates and queues copied payload bytes | A captured matching-version record, source bounds and an application return before formatting |
| CAPTUREH | Different registered event, shared byte cache and pointer/length getter | Original-wire representation, coherent owned return and timing identity |
| QDSS save | Firmware save indication, copied internal notification and two file-writing routes | Live execution, complete delivery and trace record meanings |
| QDSS private control | Allocation/mapping, release and a cached device-field response | A firmware writer feeding that allocation and a complete-record protocol |

The [saved ETW audit](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/saved-trace-byte-audit.md) ruled out an unparsed binary tail
in its 88 selected log records. The paths below are additional mechanisms in the
driver, not a reinterpretation of those text records.

## The fuller firmware diagnostic report

The installed `Data20.msc` is a firmware message catalog, not a native Windows
PDB and not a demonstrated QDSS MAC/PHY trace decoder. Its size is 1,510,137 bytes,
SHA-256 `44f472870771bb5022764e62e29c1f5625d53b47b0e0a79cd86849b5a446bbaa`,
and its header declares version **268535144**.

Entry **25950**, signature `iIIIIIIii`, names `wlan_vdev_tsf_report` and describes
nine arguments, in this order:

1. `vdev_id`.
2. `tsf_low`, `tsf_high`.
3. `qtimer_low`, `qtimer_high`.
4. `tqm_low`, `tqm_high`.
5. `mac_id`, `tsf_id`.

Those are definition labels, not measured values. Adjacent selected entries
describe the requested action (25949), interface-up state (25948), automatic
reporting (25041), and TSF allocation/reallocation/free (68/69/70). Their IDs are
firmware catalog message IDs, not WMI selectors, requests or public IOCTLs.

The exact Windows binary supplies a connected consumer:

```text
WMI diagnostic event 0x1d011       Data20.msc definitions
              |                         |
              v                         v
diag_fw_handler 0x1b01a0 ------> catalog/version gate
              |
              v
Allocate and copy diagnostic payload before queue insertion
              |
              v
dbglog_process 0x1ae5e0 -> decoder 0x1b1128
              |                         |
              |                         v
              |              Catalog message types 3 / 7
              |                         |
              |                 formatted FWLOG text
              v
Free queued payload after processing
```

- Registration `0x1ada30` binds WMI event `0x1d011` to `0x1b01a0`.
- Catalog parser `0x1aded0` reads the `VERSION:` header. The receive handler
  compares catalog and firmware-advertised versions before admitting data.
- The handler obtains a payload pointer/count from the normalized diagnostic
  wrapper, allocates and copies bytes, fills a queue entry and links it under
  framework lock calls. This is a real kernel-side copy before publication.
- Worker `0x1ae5e0` invokes decoder `0x1b1128`, then frees the copied payload.
  Allocation-failure fallback processes borrowed bytes synchronously. Neither
  path establishes an application-owned binary return or live teardown safety.
- The decoder distinguishes record types, resolves catalog IDs and formats
  message records. It can emit `FWLOG` text and retains a separate 128-byte
  formatted cache copy. That formatted cache is not the complete diagnostic bytes.

The same two saved traces were searched across WlanLogger event IDs for the
catalog report/action names and `FWLOG`. There were **zero matches**, with **11
existing host TSF-report controls found in each file**. This is a text-search
result; it does not rule out compressed records, another provider, disabled
emission or a future capture. The matching runtime catalog version was not observed.

This catalog entry could expose more counters and identifiers than the current
host TSF log, but it does not list every original TLV field: validity flags,
report class and other omitted words still need qualification. Neighboring action
and report messages cannot be paired solely by temporal proximity. Neither a
catalog definition nor a version check proves fresh or simultaneous sampling.

The next focused trace is the incoming diagnostic record and any return path
from the copied bytes **before `0x1b1128` formats them**. Keep this firmware
diagnostic lane separate from the QDSS MAC/PHY trace lane below.

## CAPTUREH is a separate event

`ol_ath_txbf_attach` at `0x1dd9c0` allocates two `0x804`-byte caches and registers
the CAPTUREH callback `0x1ddb90` for **event `0x1e003`**, not TSF event `0x5005`.
The selected schema table describes one fixed 16-byte object, tag 194.

- The callback prints byte values, stores the supplied length at cache base
  `0x3f3980`, then copies its argument into the cache after that length word.
- The length store at `0x1ddc54` precedes the copy at `0x1ddc6c`.
- Getter `0x1ddb50` returns the cache payload pointer and current length. It does
  not make an application-owned copy. Detach `0x1ddab0` releases the caches.
- No publication lock, generation protocol or original-event identity is
  established by these selected bodies. The callback supplies the received count
  as both copy size and destination-size argument, not the independently known
  2,048-byte payload capacity.
- Registration uses the normalizing WMI dispatcher, while this callback treats
  its argument as flat bytes. That representation needs reconciliation; a flat
  copy here is not proof that original firmware bytes were preserved.

The H name should not be expanded to “header.” Public Qualcomm headers describe
captured H information, and the exact Windows attachment belongs to the `txbf`
path. This does not establish a general WMI-event tap.
[Public CAPTUREH definition](https://android.googlesource.com/kernel/msm-modules/wlan-fw-api/+/android-msm-bluecross-4.9-pie-qpr1/fw/wmi_unified.h).

## QDSS has a firmware-to-file path

QDSS is Qualcomm's debug/trace infrastructure. This is a static route in the
actual inspected Wi-Fi driver, separate from finding a QUTS protocol in userspace.

```text
Firmware QDSS save indication: QMI 0x41
                    |
                    v
Decode save metadata at 0x14b778
                    |
                    v
Copy internal notification; dispatch message 0x1f
                    |
                    v
Driver handler 0x14b400 examines source value
             /                         \
            v                           v
     Source 0: DMA spans          Source 1: request chunks
         0x14d8b8                QMI 0x42 at 0x14e9c8
            |                           |
            v                           v
       File writer                Assembled buffer
         0x14bef0                        |
            |                           v
            |                    File writer 0x14f448
            \___________________________/
                          |
                          v
               File under SystemRoot/Temp
                          |
                          ? Trace record schema and timing identity unqualified
```

Arrows show inspected software flow, not a capture performed in this run. QMI
selectors, internal message numbers and WMI event selectors are different namespaces.

- `0x149b40` dispatches QMI save indication `0x41` to `0x14b778`. That routine
  decodes a `0x508`-byte object and submits internal message `0x1f`.
- `0x150290` allocates a queue item, copies a fixed `0x9c8`-byte internal envelope,
  links it under framework lock calls and signals a worker. This is copied
  notification storage; neither size is the raw trace's wire length.
- `0x14b400` selects source 0 or 1. Source 0 resolves indicated addresses into
  tracked DMA spans before writing. Source 1 requests segments with QMI `0x42`.
- The source-1 loop checks total-size/segment/data validity fields, segment ID
  and a 6,144-byte chunk limit. It assembles bytes and requires an end indication.
- `0x14f448` reaches `ZwCreateFile` and `ZwWriteFile`; the selected default filename
  is `qdss_trace.bin`. Source 0 can use a filename supplied by its save indication.

Public Qualcomm QMI definitions corroborate the segment ID, optional total size,
payload length/data and end-marker structure. They are architectural comparison,
not a schema certificate for the installed Windows firmware.
[Public QDSS QMI definitions](https://android.googlesource.com/kernel/msm/+/e6f5f48ea0a4a9be9e44f5ce20850bb7163ea5c8/drivers/net/wireless/cnss2/wlan_firmware_service_v01.c).

This path still needs integrity review. In the selected chunk body, the checks
do not establish `chunk length <= remaining allocation` or nonzero progress.
The DMA file writer does not establish an all-segment success result; source-1
callers do not propagate every file-write result. No live malformed-data or
failure experiment was performed. Do not treat a helper return as a completeness
certificate or the presence of a file as proof of coherent hardware publication.

## The private DMA control

`MPDispatch_iwpriv` at `0x11e840` recognizes **IOCTL `0x98742004`** with selected
104-byte input / 100-byte output framing and dispatches to `0x122d58`.

| Subcommand | Inspected behavior | Consequence |
|---|---|---|
| 0 | Allocate and zero DMA backing; build an MDL; map it into user mode; return mapping/device-address information | Resource allocation, not retrieval of an existing timing record |
| 1 | Unmap/free one selected allocation or all tracked allocations | State-changing cleanup, not a read |
| 3 | Return a cached 16-bit device-context field | No timestamp or firmware event supplied |

The allocation body does not establish a firmware producer writing to the new
mapping. That association, mapping permissions, caller/process lifetime, cache
visibility, publication, loss and teardown must be qualified before use. No
request builder or executable command for this interface is introduced here.
The previously deferred nested IHV query/control avenue remains deferred.

## Configuration and local observations

The loader at `0x1496c0` selects between two files using a hardware-version field.
The base directory is derived from the driver's path by `0x2f258`. Both files are
present in the inspected driver package and listed by its INF.

| File | Bytes | SHA-256 |
|---|---:|---|
| `qdss_trace_config_v1.cfg` | 4,912 | `2f319ff82e661606c1bdd3b6520c99a8e972a84839b116be9a69fb86bbbb5eac` |
| `qdss_trace_config_v2.cfg` | 5,089 | `d1f7d7ffc5178aae14f0725055c5a32535b45f10b124c190b253c222f6f990f9` |

Lexical inspection finds:

- Uncommented memory-request, MAC-event and PHY-event sections in both files;
  v2 also has a low-power trace section.
- Named `umac`, `dmac`, `pmac0`, `pmac1`, `phya0` and `phya1` sections. RX/TX
  component names are leads, not established packet timestamps.
- Commented NoC, MAC-TLV, MAC test-bus and IRQ trace sections.
- No uncommented directive key explicitly naming TSF, FTM, QTIMER or timestamp.
  This does not prove that the resulting trace records lack timestamps.
- One repeated `0x` prefix in an uncommented v1 directive, line 37. It was
  preserved unchanged. Firmware parser acceptance and interpretation are unknown.

Uncommented text is not evidence that the file was loaded or tracing is active.
An exact-adapter advanced-property query returned “More data is available.” A
separate read of that adapter's persisted driver key found no `qdssTraceEnable`
value. Neither establishes the runtime gate or its default. The default file
`SystemRoot/Temp/qdss_trace.bin` was absent; other names/locations were not ruled out.

## Next qualification step

1. Prioritize catalog message 25950: establish its incoming binary record layout,
   matching firmware/catalog version and application delivery from the copied
   diagnostic bytes. Observe a real record before making a capability claim.
2. Independently identify the decoder/schema for configured QDSS MAC/PHY records, including
   source IDs, event references, timestamp units/width, wrap and loss markers.
3. Determine whether each schema carries a complete original TSF report or another
   attributable timing event. Generic trace bytes are not sufficient.
4. Establish the configuration's supported enable/flush/disable flow and runtime
   sink ownership. Allocation of a user mapping does not connect its producer.
5. Prefer inspection of an existing attributable trace. Any new QDSS configuration
   or capture is a separate reviewed experiment; this inspection enables nothing.
6. If these traces lack the required event, retain the original pre-removal WMI
   producer integration requirement. Qualify hardware-to-QPC sampling separately.

## Reproduce and validate

Python 3.11+ and the existing `pefile` dependency suffice; ordinary read permissions
are required. The inspector reads files only and rejects a different driver hash.

```powershell
python research/tsf/inspect_event_export_candidates.py `
  --driver 'C:\owned\qcwlanhmt8380.sys' `
  --config 'C:\owned\qdss_trace_config_v1.cfg' `
  --config 'C:\owned\qdss_trace_config_v2.cfg' `
  --catalog 'C:\owned\Data20.msc' `
  --output artifacts/firmware-trace-candidates-new.json

python -m unittest discover -s tests -p test_event_export_candidates.py -v
```

- Config arguments are optional, at most two, and hash-pinned when supplied.
- The optional catalog is also hash-pinned. Only selected definitions are indexed;
  no firmware record is decoded or acquired by reading the catalog.
- Output is authored metadata, code-window hashes and scoped conclusions; no raw
  driver bytes, masks, memory addresses from the live machine or device IDs.
- Exit 0 means inspection completed, 1 rejected input/I/O, 2 argument misuse.
- Output must be new with an existing parent. No overwrite or device cleanup.
- Tests distinguish comments from uncommented text, preserve lexical anomalies,
  reject wrong builds/oversized input and retain false hardware qualification.
- Raw Ghidra assembly and vendor config contents remain in ignored artifacts.
  No live IOCTL, trace enablement, DMA mapping, firmware request or clock change
  occurred. Hosted CI and live timing qualification remain separate.

## Glossary

- **QDSS:** Qualcomm debug/trace infrastructure; the name does not identify a clock.
- **QMI:** service-message protocol used by this driver path.
- **WMI:** Qualcomm firmware control/event protocol in this document.
- **DMA:** device transfer to/from host memory; it needs a valid buffer/lifetime contract.
- **MDL:** Windows memory descriptor used to describe pages for a mapping.
- **MAC / PHY:** Wi-Fi medium-access and physical-layer processing.
- **Owned copy:** bytes whose storage remains valid independently of the producer.

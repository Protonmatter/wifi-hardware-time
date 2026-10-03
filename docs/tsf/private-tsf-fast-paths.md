# Private TSF returns, automatic reporting and TX-completion timing

Can private driver paths return Wi-Fi counters faster or report them automatically? Static analysis links counter reports to an averaged transmit delay and identifies automatic-report state changes. It finds no full-counter return in that path; reporting cadence, cleanup, packet export, and physical sampling times remain unqualified.

TSF (Timing Synchronization Function) is the Wi-Fi timer; SoC means system on chip. A vdev is a virtual wireless interface. TX completion reports transmit processing; PPDU names a physical-layer radio transmission. RVAs locate evidence within the exact binary. See the [glossary](../glossary.md).

## Contents

- [1. Resolve the indirect callbacks rather than stopping at them](#1-resolve-the-indirect-callbacks-rather-than-stopping-at-them)
- [2. Exact private arguments and state effects](#2-exact-private-arguments-and-state-effects)
- [3. The stored delta feeds TX-completion timestamps](#3-the-stored-delta-feeds-tx-completion-timestamps)
- [4. A private non-ETW return exists, with different semantics](#4-a-private-non-etw-return-exists-with-different-semantics)
- [5. What to qualify next](#5-what-to-qualify-next)
- [Validation and limits](#validation-and-limits)

Later exact-build evidence: [ring and RX boundaries](../memory-ring/timing-boundary-investigation-2026-10-03.md) identify diagnostic/recovery consumers and nonadjacent PPDU timestamp words. These findings do not qualify a fast getter, simultaneous sample or packet export.

Status: exact-build, offline reconstruction on 2026-10-03. Private commands,
IOCTLs and firmware operations are primary research candidates here; public API
status is not an acceptance gate. Exact-build qualification and long-term ABI (binary interface)
stability are separate questions.

The new result is a concrete connection from the private TSF report to a
TX-completion timing calculation and a private statistics return. **The statistics
return exposes an averaged uplink delay, not the full TSF/SoC pair.** Automatic
reporting selects firmware actions 5/6 and changes shared per-vdev host state.
Its firmware cadence, stop acknowledgement and prior-owner restoration have not
yet been established, so no automatic-report operation was executed.

All RVAs apply to ARM64 `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`, recomputed in
this pass. RVAs identify inspected instructions/data, not callable user APIs.
Only this report was added. No hardware request, trace, device-memory operation,
debugger, register access or driver change occurred.

## 1. Resolve the indirect callbacks rather than stopping at them

The TSF report and auto-report wrapper both traverse an object at parent-context
offset `0x38ea0`. The object construction path now resolves its operations:

| Location | Exact-build observation |
|---|---|
| `0x16f6bc`–`0x16f6c4` | Store the result of constructor wrapper `0x1cbce8` into parent `+0x38ea0` |
| `0x1cbce8`–`0x1cbcec` | Forward to constructor `0x1cb788` |
| `0x1cb8c4`–`0x1cb8cc` | Install operations root at image RVA `0x392ac0` into object offset 0 |
| Root `+0x08` | On-disk pointer to secondary table at RVA `0x3925f0` |
| Secondary table `+0xd8` | Callback `0x1f6980`: store the report's 32-bit delta |
| Secondary table `+0xe0` | Callback `0x1f6a30`: set the per-vdev reporting gate |
| Secondary table `+0xe8` | Getter `0x1f6880`: return/reset mean uplink-delay statistics |

These pointers were read from the on-disk PE (Portable Executable binary) and matched freshly inspected
functions. This resolves the earlier unknown report callback on this constructor
path; it does not claim every runtime object uses that constructor without
exception.

The report callback at `0x1f6980` looks up the vdev using its byte ID, stores the
supplied word at vdev `+0xf0c` (`0x1f69d0`), then releases its vdev reference.
Its input is the low-word TSF-minus-SoC difference computed at `0x216c00`–
`0x216c08`, not a pointer to the full report.

Within report handler `0x216b00`, the full TSF, SoC and global-TSF words are copied
into a temporary 44-byte allocation, logged as individual words, and the allocation
is freed at `0x216c98`–`0x216c9c`. The inspected callback path persists only the
32-bit difference. No full-counter return buffer or retained full-counter object
was identified in this handler.

## 2. Exact private arguments and state effects

The command table records at `0x33df3c` and `0x33df58` are set-class commands,
each accepting one integer. Their selectors are 229 and 230. The dispatcher
loads the first integer and calls the registered wrappers through parent slots
`+0x37680`/`+0x37688`; registration is at `0x18effc`–`0x18f018`.

| Private command | Integer argument | Host-side behavior | Firmware action passed to builder |
|---|---:|---|---:|
| `tsf_read_value` | 1 | No auto-report gate update in its wrapper | 3 |
| `tsf_read_value` | 0 | No auto-report gate update in its wrapper | 4 |
| `tsf_auto_report` | 1 | Write 1 to selected vdev `+0xf10` | 5 |
| `tsf_auto_report` | 0 | Write 0 to selected vdev `+0xf10` | 6 |

The wrapper tests zero versus nonzero, not a sampling-rate value. An exact-build
experiment should constrain the argument to 0/1 even though other nonzero words
take the same firmware branch. The action numbers above are established by the
Windows instructions. Firmware enable/disable behavior for actions 5/6 remains a
testable hypothesis supported by the command name and host gate, not a live result.

`tsf_auto_report` at `0x18e910` calls the gate setter first. Setter `0x1f6a30`
stores the argument with release ordering at vdev `+0xf10` (`0x1f6a80`–`0x1f6a88`).
Only after that succeeds does the wrapper select action 5 for nonzero or 6 for
zero (`0x18e978`–`0x18e990`). Builder `0x1955e8` submits command `0x5012`, length
20. It writes the vdev and action; no interval/rate argument is passed through this
wrapper or written into the command by the builder.

Important operational consequences of that order:

- State belongs to the referenced vdev, not a process handle or request lifetime.
  No ownership token, prior-value return or automatic process-exit rollback is
  visible in this path.
- A firmware-submission failure can follow an already completed host gate write.
  The wrapper has no observed rollback of that write.
- Turning the gate off does not clear the accumulated delay or sample count in
  this setter. A later enable can encounter statistics left from an earlier
  owner/interval until the getter clears them.
- Neither wrapper selects the older capture-reset action 2. This excludes that
  explicit action from these branches; it does not prove actions 5/6 have no
  firmware-internal reset or scheduling effect.
- No firmware auto-report cadence or rate configuration was recovered from this
  command. The integer must not be advertised as a rate control.

The known 128-byte named-command envelope remains the appropriate candidate for
an exact-build auto-report tool. Existing `build_request` deliberately accepts
only the previously qualified commands, so a new guarded builder/test would be
needed before attempting auto-report. This report changes no request allowlist.

## 3. The stored delta feeds TX-completion timestamps

The per-vdev readers identified in this bounded pass are getter `0x1f6880` and
the TX statistics path at `0x1fb2e0`. The latter gates accumulation on `+0xf10`,
loads delta `+0xf0c`, then invokes delay reconstruction `0x1f8090` with a decoded
completion-status structure. The source of each input can now be traced more precisely:

```text
completion descriptor in software descriptor +0x60
  -> HAL completion decoder at 0x21c3a0
  -> decoded status on caller stack
  -> 0x1f7b60 -> 0x1faef8
  -> 0x1fb2e0 uses vdev report gate/delta
  -> 0x1f8090 computes one delay
  -> per-vdev delay sum and count
```

HAL means hardware abstraction layer: the driver code that interprets hardware-specific records. At `0x1f7878`–`0x1f7894`, the caller passes the completion descriptor and a stack
output structure to HAL slot `+0x90`. Registration at `0x218798`–`0x2187a4` assigns
that slot to `0x21c3a0`. The output is passed onward at `0x1f78a0`–`0x1f78ac`;
`0x1f7ea8`–`0x1f7eb0` passes the same decoded status to `0x1faef8`.

| Decoded field | Exact source in completion descriptor | Width and use established in Windows code |
|---|---|---|
| `+0x08`, diagnostic name `tsf` | Raw `+0x18`, copied at `0x21c4e8`–`0x21c4ec` | 32-bit word used as the completion-side timestamp operand |
| `+0x14`, diagnostic name `buffer_timestamp` | Raw `+0x10` bits 31:13, copied at `0x21c4f0`–`0x21c500` | 19 meaningful bits; reconstruction shifts them left 10 |
| `+0x04` bit 28 | Raw `+0x14` bit 0, copied at `0x21c428`–`0x21c434` | Validity gate checked before delay arithmetic |
| Vdev `+0xf0c` | Private TSF report callback | 32-bit modular TSF-minus-SoC difference |

`0x1f8090` reconstructs a 29-bit-aligned buffer time relative to the high bits of
`tsf - delta`, selecting the preceding wrap interval if required. It subtracts
that reconstruction from the adjusted timestamp, clamps a signed-negative result
to zero, masks to 29 bits and rejects a result greater than `0x01000000`.
The accepted delay is divided by 1000 in `0x1fb2fc`–`0x1fb30c`, using unsigned
multiply/shift, before updating 32-bit sum/count at vdev `+0xf14`/`+0xf18`.
Additional release/status/statistics gates precede this path; it must not be
treated as a record for every packet or every retry.

**These inputs are not host QPC samples in the inspected path.** The decoder
loads descriptor fields; the reconstruction makes no host-clock query. The
producer that originally sets the 19-bit buffer timestamp, and its relationship
to software enqueue time, have not yet been traced in the installed binary.
Host-observed completion time is also not an input to this calculation.

### Primary-source comparison: useful names, not assumed build parity

Qualcomm-origin QCA6490 descriptor documentation published in Android's source
tree has the same release-ring field location: 19-bit `buffer_timestamp` at
byte `0x10`, bit 13, with units of 1024 microseconds. It describes this as a
timestamp carried from transmit-buffer metadata. This is a matching structural
reference from another hardware/source lineage, not proof of installed firmware
parity. [WBM release descriptor](https://android.googlesource.com/kernel/msm-modules/wlan-fw-api/+/refs/heads/android-msm-bonito-4.9-android11-qpr1/hw/qca6490/v1/wbm_release_ring.h).

The corresponding rate-statistics header names the 32-bit field
`ppdu_transmission_tsf`. Its sampling point can be PPDU start **or** finish,
depending on hardware scheduler configuration. That unresolved choice prevents
assigning an exact over-the-air reference point to the Windows value merely from
its name. [Rate-statistics descriptor](https://android.googlesource.com/kernel/msm-modules/wlan-fw-api/+/refs/heads/android-msm-bonito-4.9-android11-qpr1/hw/qca6490/v1/tx_rate_stats_info.h)
(observed file blob `721d2d4afdab62ae606dbe214b4df9247eb2b255`).

The related transmit-command header associates buffer time with a global system
timer and allows the first relevant software/TCL/TQM stage to populate it when
not already valid. Therefore a host-enqueue clock function must not be invented
for the Windows path. [Transmit-command descriptor](https://android.googlesource.com/kernel/msm-modules/wlan-fw-api/+/refs/heads/android-msm-bonito-4.9-android11-qpr1/hw/qca6490/v1/tcl_data_cmd.h).

Public Qualcomm host code under `WLAN_FEATURE_TSF_UPLINK_DELAY` also implements
the same delta subtraction, 29-bit masking, division by 1000, accumulation and
read/reset getter, and describes the final mean in milliseconds. This strongly
supports the intended metric's interpretation. The inspected Windows routine
has additional wrap/negative handling, so the source is a comparison rather than
a replacement for the exact Windows arithmetic.
[Uplink-delay implementation](https://android.googlesource.com/kernel/google-modules/wlan/qcom/wcn6740/wlan/+/refs/heads/android-gs-akita-android16/qca-wifi-host-cmn/dp/wifi3.0/dp_tx.c)
(observed file blob `4a0d94483265352655d1fd41dbba3f257207137a`). Units and physical
sampling configuration still require exact-build qualification before clock use.

## 4. A private non-ETW return exists, with different semantics

Top-level dispatch at `0x11f108`–`0x11f110` compares against private IOCTL
**`0x002201cc`**, then calls `sta_ll_stats_dump` at `0x126e50` via `0x11f42c`.
This is a concrete dispatch constant recovered from the binary, not a guessed
control value. It is distinct from the named-command IOCTL `0x00220182`.

The handler requires at least eight input bytes and at least 52 output bytes.
It logs the two input words as request ID and mask. At `0x127274`–`0x127294`, it
calls operations slot `+0xe8`, resolving to the uplink-delay getter `0x1f6880`.
It stores the returned word at output offset `0x2c`; values at or above
`0x10000` become `0xffffffff` (`0x127298`–`0x1272a8`).

The getter requires the per-vdev gate to be nonzero and sample count to be
nonzero. It returns unsigned integer `sum / count` and resets both accumulators
using separate atomic stores. Reading the statistics clears them; the separate
sum/count accesses are not an atomic measurement snapshot.

The outer IOCTL is broader still: it issues firmware link-statistics operations,
waits for a statistics event, and invokes a later statistics-clear path. The mask,
full return layout, clear semantics, port binding and timeout/error paths must be
qualified before a live invocation. No invocation occurred here. Even a successful
result would expose an aggregate delay, not raw per-packet timestamps or full TSF.

## 5. What to qualify next

The strongest new candidate is the decoded TX-completion record before aggregation.
It contains a timestamp, a coarse buffer-time operand, validity and packet-related
metadata. The next bounded static step is to follow the transmit submission path
that populates the raw buffer timestamp/valid bit, and any existing private
completion-record consumer/export. Also identify the installed scheduler setting
that selects PPDU start versus finish. This can establish the field's actual clock
origin and physical reference without using a blind register read.

For private auto-report, the request encoding and host state write are established;
the remaining gate is firmware action behavior and ownership/cleanup, not whether
the API is public. Before an enable experiment, establish a known off baseline
under exclusive test ownership and a bounded disable/cessation check. The future
experiment should use only argument 1, a short predeclared observation window and
report-count cap, then argument 0 in cleanup. It must verify cessation separately
from IOCTL completion and preserve a failure receipt if host/firmware state may
have diverged. No rate argument should be invented. No auto-report call is proposed
as immediately executable until those outstanding state semantics are resolved.

At the time of this report, the candidate for high-rate full-counter observation
was the previously tested one-shot action-3/action-4 path with explicit request
windows. Later [scan comparison results](../acquisition/scan-tsf-results-2026-10-03.md)
left private acquisition quarantined; the earlier testing does not override that
current restriction. Investigating an existing raw return remains separate. Automatic reporting may reduce
request overhead but does not itself create a non-ETW full-counter return.
The meaning and requirements of the user's “AS” objective remain pending; no
accuracy target or synchronization protocol is assumed by this report.

## Validation and limits

- Recomputed exact driver hash; read command-table records and operations-table
  pointers from the installed PE.
- Freshly inspected wrapper, report, resolved callbacks, HAL decoder, delay
  reconstruction, statistics getter and IOCTL dispatch ranges.
- Cross-checked reader/caller references against saved disassembly, including
  the two TX-status callers and the single delay-helper caller.
- Checked the multiply/shift division against integer division at zero, 999,
  1000, 1001, the accepted upper-delay bound and UINT32_MAX.
- Consulted the linked primary comparison sources; no vendor implementation or
  raw binary material was copied into the repository.
- Checked Markdown local links, fences and whitespace. This report changes no
  executable code, so no code tests were added.

Not validated: live auto-report enable/disable, firmware cadence, restoration of
another owner's state, complete statistics IOCTL contract, raw per-packet export,
installed buffer-time producer, PPDU reference-point configuration, counter epoch,
QPC/UTC mapping, synchronization or accuracy. Static pointer/reference searches
are bounded evidence, not a whole-program proof that another return path is absent.

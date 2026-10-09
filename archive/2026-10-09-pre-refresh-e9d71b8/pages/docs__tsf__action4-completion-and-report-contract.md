# Action 4: command completion and complete reports

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__tsf__action4-completion-and-report-contract.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Action 4 remains the useful refresh lead, but its request return cannot certify that firmware has sampled a clock. The exact driver can accept a command into a queue and return success before issuing it. We have mapped that boundary and added a diagnostic decoder that preserves complete report bytes under explicit reference layouts. Fresh sampling and hardware-to-host conversion remain open.

## Contents

- [Scope and terminology](#scope-and-terminology)
- [What the send path completes](#what-the-send-path-completes)
- [What must survive the report path](#what-must-survive-the-report-path)
- [Implemented offline tools](#implemented-offline-tools)
- [The next acquisition contract](#the-next-acquisition-contract)
- [Validation and limits](#validation-and-limits)

## Scope and terminology

Inspected on 2026-10-05: ARM64 `qcwlanhmt8380.sys`, version `1.0.4374.1300`,
SHA-256 `ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
Addresses below are RVAs: offsets relative to this executable's loaded base.
They are navigation points for analysis, not callable application APIs.

- **TSF:** the Wi-Fi timing counter. Its clock identity is separate from request identity.
- **QPC:** Windows's host interval counter, read with `QueryPerformanceCounter`.
- **WMI:** here, Qualcomm's host/firmware message interface.
- **HTC/HIF:** host-target communication and host-interface transport layers.
- **TLV:** a record containing a type tag, length and value bytes.
- **vdev:** a virtual wireless interface.
- **Sampling fence:** a completion whose contract proves the relevant hardware read has finished.

Function names recovered from diagnostic strings aid interpretation; Ghidra's
decompiled C is approximate. The conclusions below come from selected code paths,
not a live instruction trace. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) for other terms.

## What the send path completes

```text
Application records request-start QPC
                  |
                  v
Private request -> action selection -> WMI command 0x5012, action 4
                  |
                  v
HTC prepares the transport packet
                  |
                  v
HTCTrySend adds accepted packets to the endpoint queue
                  |
                  +-- another sender active --> return SUCCESS with work queued
                  |
                  +-- sender can proceed ----> HTCIssuePackets -> HIF send

Application records request-return QPC
                  |
                  ?  This return does not establish a firmware sampling fence

Separate firmware report 0x5005 -> driver handler -> diagnostic log -> reader
                  |
                  ?  Exact request association and fresh sampling still needed
```

Arrows show control/data flow, not equal-duration steps. The two branches describe
static possibilities. The diagram does not identify which branch a historical
capture took. A `?` marks a missing timing contract.

| Location | Inspected behavior | Consequence |
|---|---|---|
| `0x18e9e0` | Selects action 3 for a positive argument and action 4 for zero | The existing guarded request encoding already reaches action 4 |
| `0x1955e8` | Builds the 20-byte command and submits `0x5012` | Command construction supplies no demonstrated per-request response cookie |
| `0x169678` | Clears the fifth argument before entering `0x169680` | This TSF caller does not supply the optional barrier object |
| `0x16aaf8` | Dispatches barrier types `0x6002` and `0x5002` | These lead to peer-delete and vdev-delete queues, respectively |
| `0x16ab60`, `0x18d540` | Append deletion requests under inspected framework lock operations | They are not a demonstrated generic TSF sampling fence |
| `0x1b90b8`, `0x1b9140` | Single-packet wrapper and `HTCSendPktsMultiple` | Prepare transport packets and enter endpoint queue handling |
| `0x1b9400` | `HTCTrySend` admits packets before checking whether a sender is active | Its busy branch can return zero while accepted packets remain queued |
| `0x1b7e38` | `HTCIssuePackets` enters the HIF send path at `0x1b40a0` | Lower transport submission is distinct from the later TSF report |
| `0x1b7690` | Selected `DoSendCompletion` invokes an endpoint callback | The later receive/return trace resolves WMI's callback to `0x169220`: outgoing buffer/cookie release, not TSF sampling |

The queue trace identifies an endpoint-relative queued count at `+0x78` and an
atomic sender-active counter at `+0xdc`. The busy branch decrements that active
counter, releases its lock and returns zero without issuing the newly queued
work in that invocation. This is a concrete counterexample to interpreting
transport success as a universal firmware-completion guarantee.

**Do not repurpose the deletion barrier for TSF.** No inspected caller connects it
to event `0x5005`, and changing an undocumented argument would not establish the
missing firmware contract.

A roughly 54-microsecond request return and a later report log also do not locate
the hardware read inside those 54 microseconds. The sample could occur after
return, or a report could contain an earlier value. Even the wider interval from
request start to report logging is a sampling bound only after proving both
freshness and causal association. A fitted regression cannot supply those proofs.

## What must survive the report path

The separate report handler at `0x216b00` uses selected words from event `0x5005`.
Its schema table expects 60 decoded bytes, but that is not proof of 60 original
wire bytes: normalization can supply absent fields. The
[field-coverage inspection](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-association-and-quarantine-disposition.md)
identifies which words the selected handler omits.

The later [internal consumer trace](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/private-tsf-fast-paths.md) already establishes
that the selected callback stores a low-word TSF/SoC difference. Its related
getter supplies an averaged uplink-delay statistic. It is not a full-counter
return path. Export must preserve data before reduction or use another producer
that demonstrably retains the complete event.

Two public reference definitions also disagree at one important position:

| TLV position | Older 48-byte reference | Newer 60-byte reference |
|---|---|---|
| `0x08/0x0c`, `0x10/0x14` | TSF pair, Qtimer pair | Same field labels |
| `0x18/0x1c`, `0x20` | TSF ID/validity, MAC ID | Same positions |
| `0x24` | Independent MAC ID validity | Report class: TSF or uplink delay; MAC validity instead uses `tsf_id_valid` |
| `0x28/0x2c` | Global TSF pair | Same field labels |
| `0x30/0x34`, `0x38` | Absent | TQM timer pair and selection flag |

Sources: [older Qualcomm reference](https://android.googlesource.com/kernel/msm-modules/wlan-fw-api/+/refs/heads/android-msm-coral-4.14-android11/fw/wmi_unified.h)
and [pinned newer Qualcomm reference](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8650/blob/38d50357db2728300a61b6f757f2d3a09651c155/vendor/qcom/opensource/wlan/fw-api/fw/wmi_unified.h).
These are reference layouts, not certificates of the running Windows firmware ABI.
Qtimer and TQM are vendor timer labels; no host-clock equivalence is implied.

The record does not echo action 4 or contain an established request token. A
candidate TSF ID of zero can be valid; its validity flag controls interpretation.
Neither the ID nor a TSF report-class label proves a particular request caused it.

## Implemented offline tools

- [inspect_action4_completion.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/inspect_action4_completion.py)
  checks the exact owned image, verifies the selected wrapper instructions and
  fingerprints the traced code windows. The output explicitly labels manual
  trace conclusions; hashes do not independently prove those conclusions.
- [decode_tsf_report.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/tsf/decode_tsf_report.py) accepts one
  complete TLV under an explicitly selected reference layout. It preserves raw
  bytes and a hash, assembles 64-bit containers without floating-point loss,
  retains unknown validity values and returns a detached immutable snapshot.
- The decoder rejects truncation, extra bytes, wrong tags/lengths, an implicit
  layout, command `0x5012` in place of event `0x5005`, and declared normalized input.
- Byte-copy ownership is tested using stable synthetic input followed by source
  mutation. This does not test copying concurrently changing driver/DMA memory.
- Declaring `captured-unqualified` does not attest acquisition. A fabricated or
  rewritten header can resemble wire data; file parsing cannot detect that.
- Units, meaningful counter width, epoch and host sampling interval remain
  unknown. All live-clock qualification fields remain false.

From the repository root, using Python 3.11+ and the existing dependencies:

```powershell
python research/tsf/inspect_action4_completion.py `
  --driver 'C:\path\to\owned\qcwlanhmt8380.sys' `
  --output artifacts/action4-completion-new.json

python research/tsf/decode_tsf_report.py artifacts/synthetic-tsf-report.bin `
  --event-id 0x5005 --reference-layout reference-60 `
  --origin fixture --representation wire

python -m unittest discover -s tests -p test_action4_completion.py -v
python -m unittest discover -s tests -p test_decode_tsf_report.py -v
```

The example report file must be supplied; it is not a bundled hardware capture.
For diagnostic decoding of an independently acquired original TLV, use
`--origin captured-unqualified` and keep its separate acquisition provenance.
Adding `--require-clock-input` always rejects this diagnostic-only decoder.

Operational contract:

- Permissions: ordinary file reads/writes; no administrator or UAC request.
- Inspector input: at most 16 MiB plus one rejection byte; exact hash required.
- Inspector output: new JSON file, existing parent directory; never overwrite.
- Decoder input: at most 60 bytes plus one rejection byte in TLV-only mode;
  the later `event-wire` mode allows 64 plus one. Exact selected size is required.
- Decoder output: JSON on stdout, including potentially sensitive raw bytes.
  Store hardware-derived output only in ignored private evidence locations.
- Exit codes: `0` diagnostic success, `1` rejected input/I/O/unqualified clock
  admission, `2` command-line misuse.
- Rollback: none for hardware; the tools do not open devices or change state.

## The next acquisition contract

Continue action 4 by establishing these producer-side properties in order:

1. **Original event ownership:** copy the original `0x5005` TLV, actual byte count
   and transport event identity while the producer guarantees valid access.
   Preserve presence information before any normalization and publish only after
   the owned copy is complete.
2. **Correct schema and clock:** establish the running firmware's field meanings,
   units, validity, meaningful widths and split-word acquisition behavior. Do not
   select a schema from size alone.
3. **Association and freshness:** require an echoed producer token or a proven
   ordering/exclusion contract across all producers, late reports and epochs.
   Otherwise classify a record as autonomous, without inventing a request match.
4. **Host relationship:** preserve request-start, request-return, report-entry,
   log and reader-receipt host times separately. An associated fresh sample with
   a proven sampling order may support a request-start-to-report-entry bound.
   The inspected request-return boundary cannot supply its end point.
5. **Admission:** reject partial, ambiguous, late, stale or continuity-uncertain
   records. Review the existing quarantine against new producer evidence before
   restarting a private campaign; collector restart is not firmware drain.

The [event-ingress follow-up](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md) now traces the
original-length handoff, normalization and TSF-specific cleanup. It adds an owned
original-event diagnostic form. Live wire length and a real export before reduction
remain unmeasured. The subsequent
[return-candidate trace](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/tsf-event-ingress-and-owned-copy.md#existing-return-candidates)
resolves the registered WMI send completion to outgoing-buffer/cookie release;
that completion does not establish firmware sampling.

## Validation and limits

The 2026-10-05 Ghidra passes exported six selected functions without truncation or
decompilation failure: three submission/deletion-queue functions, two queue/
completion functions and `HTCIssuePackets`. Receipts and raw exports remain in
ignored `artifacts/action4-qualification-20261005/`. The preceding command/report
trace remains in `artifacts/tsf-completion-bracket-review-20261005-01/`.

Validation on this local working tree:

- Python compilation passed for `research` and `tests`.
- The configured full suite passed **279 tests with zero skips**, including the
  12 new tests, native C regression and owned Windows-image fixtures. The local
  configuration supplied ARM64 MSVC and exact driver, WiFiCx and WLAN image paths.
- Index consistency, documentation links and canonical diagram/embed checks passed.
  This page's new workflow is plain text; no existing Mermaid source changed.
- Exact-image inspection succeeded. The active Qualcomm interface remained Up
  on driver `1.0.4374.1300`, with the same driver SHA-256 after the work.
- These are local validation results. Hosted checks belong to the exact containing
  revision in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3/checks);
  previous green revisions do not validate later additions.

The owned-image unit test is optional on machines without the fixture. Set
`WIFI_TIME_DRIVER_FIXTURE` to the exact owned driver path to include it; a skipped
fixture is not a passed image check. Synthetic tests require no hardware.

These checks validate selected static evidence plus synthetic structural,
rejection and detached-copy behavior. No new full firmware report was acquired, no private
IOCTL was sent, and no elevation was requested. No live firmware sampling instant,
publication consistency, QPC conversion or synchronization accuracy is established.
The current private campaign remains quarantined; the software decoder adds a
testable return boundary without changing that disposition.

Return to [TSF research](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/tsf/README.md) or [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).

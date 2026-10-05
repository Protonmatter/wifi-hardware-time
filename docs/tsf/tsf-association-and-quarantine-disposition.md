# TSF association, fresh sampling and quarantine disposition

The driver expects a larger TSF report than its diagnostic handler exposes. A newer vendor header names omitted clock-identity and report-type fields, giving us a concrete acquisition lead. Those fields have not been retrieved or qualified on this firmware. Saved evidence still contains unmatched reports, so quarantine remains in force and fresh clock sampling remains unproven.

<!-- current-context:2026-10-04 -->
**Current context (2026-10-04):** The TSF sampling and response-association contract remains open. New diagnostic return interfaces do not automatically qualify a fresh TSF getter. See [current findings](../knowledge/current-findings.md).
<!-- /current-context -->

## Contents

- [New field-coverage finding](#new-field-coverage-finding)
- [Clock identity is separate from event identity](#clock-identity-is-separate-from-event-identity)
- [What would establish association and freshness](#what-would-establish-association-and-freshness)
- [Quarantine disposition](#quarantine-disposition)
- [Validation and next bounded task](#validation-and-next-bounded-task)

## New field-coverage finding

Exact driver: ARM64 `qcwlanhmt8380.sys` 1.0.4374.1300, SHA-256
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
An RVA is a relative virtual address: an offset from the loaded image base,
not a raw file offset or a callable user interface. A TLV is a tag/length/value
structure. QPC is the host interval counter; a vdev is a virtual
wireless interface. See the [glossary](../glossary.md).

- Event `0x5005` has one descriptor in the driver's schema table at `0x39003c`:
  tag `0x18b`, expected structure size **60 bytes**, including its TLV header.
- That is the driver's expected layout, not proof that every firmware response
  contains 60 wire bytes. The generic decoder can normalize shorter structures.
- The report handler at `0x216b00` reads payload words at offsets
  `0x04, 0x08, 0x0c, 0x10, 0x14, 0x28, 0x2c` into its temporary report object.
- In the inspected handler, payload words at `0x18, 0x1c, 0x20, 0x24, 0x30,
  0x34, 0x38` are not consumed. The existing logging path does not expose them.

A newer [vendor-published WMI header](https://github.com/OnePlusOSS/android_kernel_modules_and_devicetree_oneplus_sm8650/blob/38d50357db2728300a61b6f757f2d3a09651c155/vendor/qcom/opensource/wlan/fw-api/fw/wmi_unified.h)
has a 60-byte layout with matching positions for the already identified fields.
Its omitted positions supply these **candidate labels only**:

| Offset | Reference-header name | Potential use if exact firmware semantics are established |
|---|---|---|
| `0x18` | `tsf_id` | Identify which TSF clock supplied a value |
| `0x1c` | `tsf_id_valid` | Determine whether clock/MAC identifiers are meaningful |
| `0x20` | `mac_id` | Identify the hardware MAC context |
| `0x24` | `ul_delay_or_tsf_report`, formerly `mac_id_valid` | Distinguish uplink-delay reporting from a TSF report |
| `0x30`, `0x34` | `tqm_timer_low`, `tqm_timer_high` | Additional timer words, whose relationship remains unknown here |
| `0x38` | `use_tqm_timer` | A timer-selection indicator requiring firmware qualification |

This is other-platform source evidence, not installed-firmware schema proof.
In particular, the documented repurposing at `0x24` makes blindly applying an
older header unsafe. No values for these fields were recovered from hardware.
The candidate TSF/MAC identifiers name clock contexts, not unique requests.

The 20-byte command builder supplies a header, vdev and action. Its allocation
helper clears the requested buffer, and the builder leaves the last two words
zero. The reference header labels those words periodic-report period/flags;
neither builder inspection nor that header identifies a per-request cookie.
Do not place a token into those words or enable reporting based on this comparison.

## Clock identity is separate from event identity

The clock identifier answers **which timer supplied the value**. Frame/report
type and capture provenance answer **what event the value describes**. A request
identifier is required only when claiming a particular request caused a response.
An unsolicited observation can be useful without belonging to any host request.

- Scope a clock ID to its device/source and continuity period. Do not assume a
  link ID, hardware MAC ID, vdev ID and TSF ID are interchangeable. Multi-link
  operation makes their mapping important; the active mapping is not yet verified.
- A beacon's embedded timestamp belongs to the transmitting BSS's timebase.
  A receiver's RX descriptor timestamp belongs to its own identified clock.
  Those two values describe related events but are not automatically the same
  clock or physical instant.
- A probe response's subtype, transmitter/receiver/BSSID and capture context
  describe the observation. They do not always identify one unique request;
  [unsolicited broadcast probe responses](https://cdn.kernel.org/doc/html/latest/driver-api/80211/cfg80211.html#c.cfg80211_unsol_bcast_probe_resp)
  also exist. Do not manufacture a request match from subtype/address alone.
- In legacy 802.11mc FTM, the initial request's fixed body has a Trigger field.
  The FTM measurement frame carries Dialog and Follow-Up Dialog Tokens, with
  follow-up context associating reported times with an earlier measurement.
  It is not generally an echo of a token from the initial request. Preserve
  peer, session, exchange and retry context; the driver's internal wrapping
  request byte is a separate identifier. See
  [Wireshark's frame parser](https://github.com/wireshark/wireshark/blob/987d3f8d5d2102fa9922adf616f87a9c028a43d2/epan/dissectors/packet-ieee80211.c)
  (`add_ff_ftm_request`, `add_ff_ftm`).

A validated aggregate RTT API can hide timer identities from its consumer because
its producer performs the required within-clock differences and exchange matching.
Raw event-time consumers must establish those domains and rate assumptions themselves.
Our generic firmware TSF report is not an on-air beacon or FTM frame, and no such
frame type may be assigned to it without a traced producer connection.

## What would establish association and freshness

The following are acceptance requirements, not newly established capabilities:

1. **Solicited profile:** when claiming request/reply association, require an
   echoed request token bound to the same result, or an
   independently established ordering/exclusion contract covering all producers
   and late reports. One outstanding application request does not provide that
   contract when other activity can emit the same event.
2. **Autonomous profile:** require an identified frame/event, source clock,
   validity, capture provenance and defined sampling/age semantics. No host
   request token is required. Do not present it as a reply to a pending request.
3. **Clock and event fields:** preserve report/frame type separately from vdev,
   MAC, link, TSF identity and validity. A timer ID does not identify a request;
   a report-class filter does not by itself identify the producing operation.
4. **Fresh sample:** for a solicited sample, prove a new value after the request.
   For an autonomous sample, establish its event reference and age through its
   capture path. A cached management-frame record is not a fresh RF observation.
   SoC refresh and increasing TSF values alone do not establish either contract.
5. **Host bracket:** for a solicited operation, prove a causal interval from host QPC before that operation
   to host QPC after processing its attributable fresh result. IOCTL return need
   not be the upper endpoint. A report-log time can only participate after its
   semantics and association are established; delayed receipt is not sampling.
   Autonomous observations need their own qualified timestamp pairing or capture
   interval; the start of an unrelated host request cannot supply its lower bound.
6. **Lifetime and continuity:** own the result before buffer reuse and establish
   the applicable clock generation. Reject uncertain generation, stale, partial,
   duplicate, lost and unclassified observations for clock-model updates.

An atomic hardware/host cross timestamp would be stronger, but a genuinely
bounded sampling interval can be useful without asserting simultaneity. Its
measured width and other error terms must fit the clock's declared error budget.

## Quarantine disposition

**Decision: retain quarantine. No rearm, private request, scan, reset or mode
change is part of this disposition.** This is a research review result, not a
new runtime control or a change to the existing marker.

Fresh offline replay of the finalized rejected capture confirms:

- 9 command groups and 11 report/SoC/delay groups: **2 groups remain unattributed**.
- All 9 submitted request receipts report success and handle closure.
- Submission records show 9 drained states and 1 aborted attempt. These are
  controller/probe states, not proof that firmware reports have drained.
- The capture remains failed; the existing marker has automatic rearm disabled.
- The report does not recover missing final observer-stop evidence or convert
  independent process/session termination into a normal-stop return code.

The later scan experiment shows another report-producing operational context,
but cannot identify the two historical reports conclusively. The omitted
report-type fields were not logged, so they cannot be retroactively filled from
an action name, timestamp ordering or a related-platform header.

Reopening acquisition requires an evidence-backed isolation/association design
and a reviewed bounded profile with target, request budget, deadline, cleanup and
abort behavior. A quiet window, collector restart, longer timeout or changing
the marker filename is insufficient. Raw diagnostic access and clock admission
must remain separate decisions.

## Validation and next bounded task

The [2026-10-05 action-4 follow-up](action4-completion-and-report-contract.md)
now traces queued-success transport behavior and supplies an owned diagnostic
decoder. It preserves the separate association, sampling and live-publication gates.
The subsequent [ingress trace](tsf-event-ingress-and-owned-copy.md) resolves original
length handling, padding and TSF-specific cleanup. Its original-event software
record still needs an attributable live producer and export implementation.

The next useful target is **complete TSF report coverage**: establish exact
firmware meanings and an owned export of the currently omitted metadata at the
event-decoding/handler boundary. Preserve raw bytes and validity rather than
adding inferred fields to historical records. If that metadata still cannot
associate a request, the solicited profile needs a producer-side token or proven
serialization/drain contract. Alternatively qualify a distinct autonomous
observation profile with its own event and sampling evidence; do not relabel the
failed campaign retroactively. The existing diagnostic reader remains unqualified
for clock input.

The new offline inspector reads an owned exact-build file, not running-driver
memory. Its small decoder counts only unsigned-immediate 32-bit loads in a
selected copy block; manual inspection of the full handler supplies context.

```powershell
python research/tsf/inspect_tsf_report_contract.py `
  --driver 'C:\path\to\owned\qcwlanhmt8380.sys' `
  --output artifacts/tsf-report-contract-new.json
python -m unittest discover -s tests -p test_tsf_report_contract.py -v
```

Python 3.11+ and existing dependencies; ordinary file-read permission suffices.
The input is capped at 16 MiB plus one rejection byte. Output must be new and
its parent directory must exist. Exit 0 means inspection completed, 1 means
rejected input/I/O, and 2 means CLI misuse. Output contains offsets/hashes only;
no device state changes or operational rollback are involved.

Fresh disassembly matched four selected ranges, 223 instruction/literal lines
(the word-copy subrange overlaps the full handler). Driver identity was checked
before and after. Three focused tests cover the narrow decoder, build rejection
and owned-file schema. Private receipts and the pinned reference header remain
under ignored `artifacts/TsfAssociationInvestigation/`.

The packaged firmware hash was checked, but its TSF sampling producer and running
image identity were not established in this pass. No firmware instructions or
driver functions were executed. These findings narrow the missing contract;
they do not complete it or justify a timing-accuracy claim.

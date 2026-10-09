# Keeping source metadata with returned bytes

The broker can now carry an operation description together with the original returned bytes. The consumer checks operation, software identities, provenance and format before exposing diagnostic counter values. Unknown clock and loss information stays unknown. This is a tested software integration layer for fixtures and saved captures; a live timing producer and a qualified clock conversion remain separate dependencies.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__evidence__source-operation-record.md).
<!-- /research-history -->

## Contents

- [Implemented boundary](#implemented-boundary)
- [Supported profiles and record fields](#supported-profiles-and-record-fields)
- [Rejection and quarantine behavior](#rejection-and-quarantine-behavior)
- [Host observations are not hardware sampling intervals](#host-observations-are-not-hardware-sampling-intervals)
- [Use and reproduce](#use-and-reproduce)
- [Validation and limits](#validation-and-limits)
- [Glossary](#glossary)

## Implemented boundary

The [source-record module](../../research/export_contract/source_record.py) adds
an envelope inside the existing broker's opaque payload. An envelope is a small
record that keeps the bytes and their interpretation metadata together. The C
broker API and its `WHTR` version 1 format are unchanged.

```text
Fixture or saved capture bytes + declared source metadata
                         |
                         v
             build_source_record
       Validate profile and original payload
       Encode metadata + bytes into one immutable record
                         |
                         v
                Native rb_publish
             Copy the entire record
             Publish only after copying
                         |
             original buffer can be reused
                         |
                         v
          rb_read returns caller-owned WHTR bytes
                         |
                         v
             decode_broker_source <--- expected operation and session identities
       Check broker header AND contained source record
                         |
                         v
           Owned diagnostic observation
     Raw TSF/SoC reference view when applicable
     Unknown clock meaning and sampling stay explicit
     Clock eligibility and quarantine release remain false
```

**Legend:** these arrows describe implemented software, not a running firmware
capture. The native tests overwrite the input after publication and the output
after decoding; the returned diagnostic data remains intact. A real producer must
still supply a valid, coherent source span at the
[driver integration boundary](driver-event-return-integration.md).

The operation profile records entry route, original entry route where known,
framing, selector, selector precedence, state effects, producer, returned-byte
meaning and completion meaning. The profile is defined in code and fingerprinted.
Matching that fingerprint identifies the expected description; it does not prove
that supplied bytes actually followed the described hardware path.

## Supported profiles and record fields

Five profiles are currently accepted:

| Profile | Original payload accepted |
|---|---|
| `qcom-fixed-test-get-v1` | Exactly the eight fixed bytes from the positive-control format |
| `qcom-tsf-wmi-reference-48-v1` | Four-byte WMI header plus the 48-byte reference TLV |
| `qcom-tsf-wmi-reference-60-v1` | Four-byte WMI header plus the 60-byte reference TLV |
| `qcom-tsf-htc-reference-48-v1` | Original HTC envelope containing that WMI event, including any valid-length opaque trailer |
| `qcom-tsf-htc-reference-60-v1` | Same envelope under the 60-byte reference layout |

These are explicit **reference layouts**, not a certificate of the installed
firmware schema. HTC records require a separately supplied expected endpoint.
Neither a transport endpoint nor a virtual-device field becomes a qualified clock ID.

The source record is canonical ASCII/UTF-8 JSON, at most **4,096 bytes**, inside
the existing broker payload. Original data is at most **327 bytes** under these
profiles. Larger or unsupported records are rejected, not truncated. This profile
does not support arbitrary RX frames or pre-aggregation FTM records.

| Field group | Meaning and enforced boundary |
|---|---|
| Schema/profile/digests | Exact schema and code-defined operation profile; original-payload content hash |
| Provenance | `fixture` or `replay-unqualified`, matching the enclosing broker origin |
| Driver identity | Pinned Qualcomm driver-file hash; this does not attest the loaded firmware |
| Capture evidence | Replay requires the saved input artifact's SHA-256, independently expected by the consumer |
| Software scope | Nonzero session, generation and source labels; must match the receiver's expected scope and broker header |
| Source observation sequence | Producer-side software ordinal, checked against the receiver's expectation; not a firmware token |
| Source loss | Explicit null for unknown, or a canonical integer count; never silently replaced with zero |
| Continuity | `unknown` or `gap-reported`; no verified-continuity claim exists in these profiles |
| Firmware/clock fields | Firmware identity, request identity, hardware epoch, clock ID, units and meaningful width must remain null |
| Host interval | Optional named host observation with QPC frequency and ordered endpoints |
| Original payload | Exact length, hash and original bytes; event/transport headers remain available |

Integer identities, counters and QPC values use canonical decimal strings to
avoid JSON floating-point loss. Unknown or missing fields, duplicate JSON keys,
noncanonical encodings, unsupported capability assertions and malformed extents
are rejected. The builder validates bounded metadata before serialization.

Hashes establish content identity and detect inconsistency. They are **not
authentication**, proof of a driver callback, or permission to admit a clock sample.
The consumer must obtain its expectations from its selected evidence/session,
rather than deriving every expectation from the untrusted record itself.

## Rejection and quarantine behavior

The consumer checks two distinct layers:

1. The broker response must match the expected application read ticket, session,
   software generation and source scope.
2. The contained source record must match its independently expected operation,
   software scope, source observation sequence, evidence digest and HTC endpoint
   where applicable. A valid outer header cannot hide a mismatched inner record.

These functions are **stateless validators**. The application owns its expected
sequence and lifecycle state. Advancing that expectation rejects an earlier
software record; repeatedly supplying the same expectation does not provide
persistent replay protection. Application tickets and source ordinals are not
firmware request associations. No late firmware report is newly qualified here.

- A reported source gap, local broker overflow or broker rejection count sets
  `quarantine_required` in the diagnostic result.
- Unknown source loss remains null. A reported zero does not establish lossless
  firmware delivery or verified continuity.
- `quarantine_required: false` means no represented gap was detected by this
  validator. It does not mean the existing campaign may resume.
- **`quarantine_release_qualified`, `clock_input_eligible`,
  `hardware_qpc_qualified` and `firmware_association_qualified` remain false.**
- End-of-session broker health is still required: a final overflow may have no
  later record on which to report its count. See [broker health](raw-event-response-broker.md#loss-and-continuity).

## Host observations are not hardware sampling intervals

Supported labels are `api-call`, `callback-copy` and `replay-processing`.
They describe the caller-declared host activity between two QPC observations.
The format checks ordering and a positive frequency, but does not authenticate
the measurement or the hardware event's occurrence inside that interval.

An API interval may be retained alongside TSF diagnostics without being treated
as a sampling bracket. `hardware_sampling_interval_qpc` and `sample_age_ns` stay
null, and freshness stays `unknown`. Parsed counter values remain available under
the existing reference decoder, with clock and schema qualification unchanged.

## Use and reproduce

The module is an experimental research API. It performs no file, network or
device I/O, and requires no elevation. The maintained application provider still
belongs in `userspace-clock`; this change does not enable its hardware backend.
This decoder belongs at the acquisition/replay boundary, not in a fast clock-read
loop. No timestamp-read latency target is claimed for JSON decoding.

```python
from research.export_contract.source_record import decode_broker_source

# owned_response_bytes comes from rb_read. Expectations come from local context.
observation = decode_broker_source(
    owned_response_bytes,
    expected_ticket=read_ticket,
    expected_session=session,
    expected_generation=generation,
    expected_source=source_scope,
    expected_operation="qcom-tsf-htc-reference-60-v1",
    expected_sequence=next_source_sequence,
    expected_endpoint=declared_endpoint,
    expected_evidence_sha256=saved_capture_digest,  # required for replay
)
# Retain diagnostics. This profile never grants clock-input eligibility.
assert observation["clock_input_eligible"] is False
```

`build_source_record` constructs an immutable record from original bytes and
explicit metadata. `decode_source_record` validates a source record without the
outer broker; `decode_broker_source` validates both layers. Invalid inputs raise
`ValueError`. Caller mappings must remain stable during construction; none are
retained afterward. `SourceRecord.wire` is immutable, while each diagnostic result
is a fresh detached dictionary.

Reproduce software checks with existing dependencies:

```powershell
python -m unittest discover -s tests -p test_source_record.py -v
powershell.exe -NoProfile -File research/export_contract/Build-RawEventBroker.ps1 -Architecture arm64
python tests/test_raw_event_broker.py artifacts/raw-event-broker-arm64/raw_event_broker.dll
```

The build installs no driver. Generated binaries stay under ignored `artifacts`.
Rollback is removing generated replay/build outputs after preserving evidence;
there is no device configuration to restore.

## Validation and limits

- Nine focused tests cover all profiles, identity/provenance mismatches, header
  corruption even with a recomputed payload hash, unknown/false claims, duplicate
  keys, malformed/deep/oversized input, metadata ownership and gap reporting.
- The configured full local suite passed **315 tests, zero skips**, including
  a fresh native build and source-envelope consumer test. Python compilation,
  documentation links, workflow/index consistency and Git whitespace checks passed.
  Independent code and documentation review reported no P0/P1/P2 issues.
- The ARM64 DLL-to-Python test preserves a complete synthetic HTC/WMI event,
  trailer and source metadata after both native buffers are overwritten.
- A separate **saved-artifact replay** used the earlier successful eight-byte
  control receipt. Its record was 932 bytes and retained the eight-byte payload,
  original receipt digest and named host interval through the native broker.
  Source loss remained unknown and clock eligibility false. No new live control
  or firmware acquisition occurred.
- Private replay evidence is under `artifacts/source-operation-record-20261005/`.
  It is not public Git content and is not an independent timing reference.
- At this experiment's original validation checkpoint, these changes were local
  and hosted CI for `df71460` covered the preceding revision. Current publication
  and review status are tracked in the [gap ledger](../overview/gap-closure-ledger.md).

The remaining hardware dependency is still a complete producer-owned event with
demonstrated source validity, publication, identity and lifetime. This software
layer preserves supplied evidence and rejects inconsistent packaging; it cannot
recover discarded fields or prove fresh simultaneous sampling.
Legacy counter-only ETW evidence remains supported by the existing evidence tools;
do not invent a wire header or missing firmware words to fit these raw-event profiles.

## Glossary

- **Envelope:** metadata stored together with the data it describes.
- **Provenance:** where evidence is declared to have come from; a declaration needs verification.
- **Canonical encoding:** one defined byte representation for equivalent supported data.
- **Software generation:** an application lifecycle label, separate from hardware clock continuity.
- **Quarantine:** a stop on admitting further observations until a failure is understood.

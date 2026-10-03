# Prepared lifecycle and timing qualification cases

These test cases describe the evidence needed before clock observations can survive collection, connection or power changes. They are preparation only: no adapter restart, sleep or roaming is authorized. The current collector cannot yet record every required transition, and the private acquisition quarantine must remain in place.

QPC is Windows' high-resolution host counter. An epoch is a period of assumed clock continuity. Reassociation reconnects to an access point; roaming changes access-point radios. BSSID identifies a radio, while GUID and PnP identity identify the selected Windows interface and device. See the [glossary](../glossary.md) for related terms.

## Contents

- [Preconditions common to future hardware cases](#preconditions-common-to-future-hardware-cases)
- [Independently controlled cases](#independently-controlled-cases)
- [Offline negative cases before those operations](#offline-negative-cases-before-those-operations)
- [Sampling, packet and independent-reference campaigns](#sampling-packet-and-independent-reference-campaigns)

Status on 2026-10-03: **preparation only; no disruptive execution authorized**.
The user selected no restart, suspend or roaming in this pass. This document is
a test specification, not an executable live harness or permission to clear a
quarantine. The private and final failed-observation markers remain preserved.

## Preconditions common to future hardware cases

1. Save one explicit interface index, GUID, PnP identity, driver version/hash,
   loaded firmware identity if obtainable, boot identity, existing profile and
   association identity in an ignored private manifest. Recheck immediately
   before action; do not rely on the historical interface index. Missing loaded
   firmware identity limits the claim rather than being silently replaced by
   driver-package identity.
2. Pin observer/controller/decoder sources and binaries. Inspect any retained
   observation lock and verify exact owned process/session cleanup before a
   separately reviewed new manifest. Never remove the private marker to run a
   lifecycle test. No new private requests are part of these initial cases.
3. Record a healthy ten-second baseline with QPC, native WLAN events, same-target
   identity and trace-health receipts. Output is exclusive, private and bounded
   to 32 MiB. Record observation gaps explicitly; no interpolation over loss.
4. A future lifecycle runner must keep collecting diagnostic evidence after the
   first invalidation while prohibiting usable observations. It must distinguish
   expected planned transition events from unexpected identity/build changes.
   The current passive runner rejects lifecycle changes and is **not** already
   qualified to collect the complete disruptive phase. Do not weaken its gate.
5. Require local sign-in access, a recovery path and fresh explicit permission
   for the chosen case. Never depend on the Wi-Fi connection being tested to
   deliver recovery instructions. If automatic recovery fails, make no repeated
   automatic reset attempts; the operator recovers through Windows Settings.
6. Check all trace-loss counters, final decoder status, input/output parity,
   observer shutdown and exact session absence. An incomplete or failed cleanup
   fails the experiment and retains evidence. API success alone is insufficient.

No new live runner is supplied by this preparation. The common collector's
continuous power/boot evidence and post-invalidation diagnostic mode must be
implemented and offline-tested before any disruptive execution.

## Independently controlled cases

| Case | Bounded stimulus after prerequisites and authorization | Required evidence and acceptance | Failure/stop |
|---|---|---|---|
| Collector stop/start | Stop only the owned collector; start one new collector with a new identity | Distinct collection epochs, unavailable interval, rejection of saved old-epoch records, healthy shutdown/start receipts; no claim of firmware drain | Unexpected process/session, missing stop/start or stale record accepted |
| Adapter restart | Restart the exact selected adapter once; no other adapter/profile changes | Continuous transition receipts, invalidation before any further usable return, reacquired identity and association, recovery observed within 60 seconds | Wrong identity, second restart needed, failed recovery or cleanup |
| Suspend/resume | One operator-initiated sleep/resume; expected sleep up to 30 seconds, 60 seconds recovery observation after resume | Explicit power transition evidence in addition to QPC, same boot or explicit reboot classification, invalidated conversion before reuse, new acquisition epoch | No recorded suspend/resume pair, reboot misclassified as sleep, unresolved gap or recovery failure |
| Reassociation | One separately permitted disconnect/reconnect to existing profile | Old association invalidated; same- or different-BSSID result recorded privately; new model required even if counters increase | Profile/security change, unknown association or stale model accepted |
| Roaming | One agreed transition between two controlled BSSIDs of the authorized network | Old/new BSSID and link identity, transition events, timestamp domain/epoch changes, late-report rejection | No controlled second AP, no actual BSSID transition, unknown AP or stale model accepted |

One passing example qualifies only that observed case and build. An adapter
restart is not proof of platform-level power reset, crash recovery, suspend,
roaming or all firmware-drain behavior. Reconnecting to the same BSSID is not a
roam. A host wall-clock/QPC difference alone does not prove that sleep occurred.

## Offline negative cases before those operations

Existing tests exercise the following relevant boundaries:

```powershell
python -m unittest discover -s tests -p test_lifecycle_evidence.py -v
python -m unittest discover -s tests -p test_passive_observation.py -v
python -m unittest discover -s tests -p test_scan_comparison.py -v
python -m unittest discover -s tests -p test_clock_pairing_hypothesis.py -v
python -m unittest discover -s tests -p test_ring_publication_model.py -v
```

| Failure fixture | Required rejection / interpretation |
|---|---|
| Timeout followed by plausible late report | Keep quarantine; do not assign by arrival order |
| Duplicate, missing or out-of-order group | Reject incomplete/ambiguous bundle |
| Reassociation with larger counters | Invalidate old model despite monotonic endpoints |
| Trace loss, incomplete tail or cleanup failure | No usable acquisition result |
| Caller restarts Python object/session | New object alone is not a firmware isolation certificate |
| Stable ring position and equal copied bytes | Cannot establish committed record completeness |
| Affine counter fit, narrow residual, unknown fixed bias | Conditional fit only; no calibrated conversion |

The `Lifecycle.start()` model assumes externally established isolation; it
cannot enforce firmware isolation. The new collector must not call it merely
because a process was restarted. These tests validate software decisions, not
the real occurrence, timing or completeness of power/association notifications.

## Sampling, packet and independent-reference campaigns

These cases have additional prerequisites and cannot be folded into restart
testing or inferred from successful FTM ranging:

Here, an ABI is the exact interface between caller and implementation. An oracle
is an independent way to check the expected result. FTM is Wi-Fi Fine Timing
Measurement, RTT is round-trip time, and RX/TX mean receive/transmit. PPDU, MPDU
and MSDU name physical, MAC-frame and MAC-service data units; their timestamps
cannot be treated as interchangeable.

- **Ring getter:** identify its exact ABI and producer completion protocol;
  obtain positive/negative fixtures for length, wrap, overwrite, epoch and loss;
  compare concurrent copies with an independent committed-record oracle. Measure
  latency separately after consistency passes. Do not trigger reset diagnostics
  or read arbitrary kernel memory as a substitute.
- **Fresh cross sampling:** obtain hardware value plus known before/after QPC
  samples for the same physical acquisition, nominal rate, source/epoch identity
  and validity. A producer change must explicitly address cached and simultaneous
  sampling. Reject stale values, invalid brackets, delayed mismatches and resets.
- **FTM absolute export:** obtain complete raw responses before reduction,
  fragment and per-exchange identity, all absolute fields, units/widths/wrap,
  validity and reference instants. Test failed/partial/reused-ID responses and
  correlate with a controlled peer/air capture. Aggregate RTT is not clock offset.
- **RX and TX:** qualify separately. Use known packets and independent packet
  identity; retain PPDU/MPDU, aggregation, retries, link, direction and source
  epoch. Check missing/duplicate completion handling. A PPDU timestamp must not
  silently become a unique timestamp for every deaggregated MSDU or TX retry.
- **Sub-millisecond synchronization:** use a second controlled node and an
  independent comparison reference whose uncertainty and delivery path are
  characterized. State relative-node versus UTC target, prediction/holdover age,
  offset sign, rate correction and path-asymmetry assumptions. Evaluate held-out
  runs and report sample count, median, tails, maximum, failures, outages and
  reference error budget. A <1 ms claim must name its percentile or interval;
  finite observed maxima are not universal guarantees. A rough AP distance,
  nanosecond output units or model residual cannot supply the missing reference.

No equipment has been added in this pass. The previous report of no controlled
second node or independent reference remains a prerequisite gap, not an accuracy
test result. Existing diagnostic return paths may require vendor cooperation or
a separately designed, signed instrumented driver; an ordinary companion driver
does not automatically have a safe contract to access another driver's buffers.

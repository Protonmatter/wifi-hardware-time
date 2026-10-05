# Concurrent owned responses for raw timing events

The new native broker turns stable source bytes into bounded, independently owned application responses. It implements publication, loss accounting, read tickets, cancellation, timeouts and shutdown, with real Windows thread tests and a Python DLL consumer. This completes a useful application-side component. The Qualcomm kernel copy points remain unconnected, so accepted data is limited to fixtures or unqualified replay and cannot enable a hardware clock.

## Contents

- [Integration boundary](#integration-boundary)
- [Publication and response flow](#publication-and-response-flow)
- [Request and shutdown behavior](#request-and-shutdown-behavior)
- [Loss and continuity](#loss-and-continuity)
- [Response format](#response-format)
- [Build and run](#build-and-run)
- [Validation and remaining work](#validation-and-remaining-work)

## Integration boundary

The [HIF producer investigation](../tsf/hif-receive-buffer-producer.md) identifies
two internal driver points that retain complete transport data. The current
WLANLIB/IOCTL investigation has not connected either point to a userspace return.
Changing an IOCTL number or opening another device name cannot create that link.

This broker is a **user-mode C library**, built as a Windows DLL or Linux shared
library. Applications call its C functions; it uses ordinary process locks and
condition variables. It must not be called directly from a kernel callback or
interrupt context. A vendor-supported or instrumented driver exporter must first
establish its own source ownership, execution level, synchronization and return
transport. That driver adapter is not implemented here.

The [driver integration contract](driver-event-return-integration.md) now maps the
existing WDF notification queue and its forced-completion callers. It specifies
the separate producer copy, source envelope, request pairing and callback-rundown
requirements needed before a live adapter can feed this broker.

```text
Future Qualcomm copy point A or B
      |
      ?  Kernel copy/publication and userspace return: NOT CONNECTED
      |
      v
Stable userspace source span             Current fixture / replay producer
      |                                             |
      +-----------------------+---------------------+
                              v
                       rb_publish
                 Bounds + generation checks
                 Copy header and all payload bytes
                              |
                              v
                Publish queue entry under one lock
                              |
Application reserves ticket -> rb_read -> complete caller-owned response
                              |
                              v
                  Strict Python response decoder
                  Optional TSF envelope diagnostics
                  All live-clock qualifications false
```

Arrows describe implemented software flow below the missing connection. A ticket
identifies an application read, not a firmware request. The diagram does not claim
that a live Qualcomm event traversed the pipeline.

## Publication and response flow

The new [header](../../research/export_contract/raw_event_broker.h) and
[implementation](../../research/export_contract/raw_event_broker.c) are additive.
The existing `te_*` and `te_event_*` APIs are unchanged.

1. Create a broker with nonzero software session, generation and source labels.
   Provenance must be `RB_FIXTURE` or `RB_REPLAY_UNQUALIFIED`.
   Choose a fresh software session for each instance; the library does not keep
   a persistent registry of previously used session labels.
2. A producer supplies a stable, accessible source span: base, capacity, offset
   and received byte count. The broker checks subtraction-safe bounds and rejects
   empty, oversized or wrong-generation input. It does not prove that a caller's
   claimed capacity is the allocation's actual size.
3. Under one internal lock, copy the complete header and payload into an unused
   slot. Only then increase the published queue count and wake readers.
4. An application reserves a one-use ticket and calls `rb_read`. A successful
   read copies the complete response into caller-owned storage, inserts the read
   ticket, removes the queue entry and retires the ticket before unlocking.

There are eight queue slots, eight request slots and a 4,096-byte payload limit.
No allocation occurs during publication or reads. The broker retains no caller
pointers. Source data must remain stable throughout `rb_publish`, including time
waiting for its lock. The caller owns and exclusively accesses output buffers
until the call returns. Internal locking does not synchronize DMA or another
component modifying the source memory.

These limits are software profile limits, not a statement about maximum firmware
event size. Oversized events are rejected, never silently truncated. Payloads stay
opaque: the broker does not invent TSF clock identity, units or sampling meaning.

## Request and shutdown behavior

| Operation or condition | Defined outcome |
|---|---|
| Reserve before the reader starts | Creates a ticket that can already be cancelled |
| Cancel a waiting or unused ticket | Wakes the reader; cancellation checked before record delivery |
| Record delivery wins the lock first | Read succeeds; later cancellation returns not-found while open, or closed after broker closure |
| Cancelled read | Does not consume a queued event; another ticket may read it |
| Output too small | Returns required size, writes zero bytes, retains the event and retires the accepted read ticket |
| Timeout | Uses one monotonic deadline, returns zero bytes and retires the ticket; a later event is not attributed to that ticket |
| Poll with timeout zero | No condition-variable wait; acquiring the internal lock can still block |
| Duplicate concurrent read of one ticket | Returns busy without disturbing the first reader |
| Late cancellation after completion/timeout | Returns not-found while open; a closed broker returns closed. Tickets are not reused within the broker |
| Close | Idempotently rejects new work, discards queued data with counts, retires unused tickets and wakes waiting reads |
| Destroy | Requires closed/quiescent state and the owner to have stopped/joined every caller |

Once a read is accepted, terminal precedence is: cancellation already recorded,
closed state, expired positive deadline, available record, then wait/empty. Close
retires tickets whose read has not started, so those subsequently return closed.
Argument-validation failures and busy results do not consume an unused ticket;
release it explicitly with `rb_release_read` if it will not be used.

Timeouts are bounded requests up to 60,000 ms, not real-time scheduling guarantees.
The timeout clock is for software waits; it supplies no hardware/QPC sample.
Requests are autonomous queue reads, not pending action-4 firmware transactions.

Teardown is deliberately two-stage:

1. `rb_close` or `rb_invalidate` while callers may still be running.
2. Stop/join all producer and reader threads, take final health, then `rb_destroy`.

The destroy-state check cannot protect a dangling pointer held by a thread that
enters after destruction. Its no-concurrent-entry precondition is mandatory.
Restarting a broker neither drains firmware nor clears the existing research
campaign's quarantine.

## Loss and continuity

Health counters distinguish:

- Successfully published and delivered records.
- Queue-full drops: drop the newest incoming event and consume a host observation
  sequence number, so a subsequent response can expose the gap.
- Records discarded at close.
- Rejected input, including stale generation and publication after close.
- Source losses explicitly reported by the producer, separately from local drops.
- Reads that terminate as cancelled or timed out. Repeated cancel calls do not
  themselves count as multiple completed cancellations.

For a quiescent broker, `published = delivered + queued + dropped_close`.
Each record carries the overflow/rejection counts as of its publication. Read
health during collection and before destruction: a final overflow may have no
later response in which to expose its count.

`rb_invalidate` closes the broker when the producer reports source loss or unknown
continuity. It wakes readers and accounts for discarded queue contents. Zero
reported source losses is not proof of lossless hardware. Session/generation
labels are software declarations; their firmware binding remains unqualified.
Only the first successful invalidation adds source losses; later calls return
closed without incrementing that count.

## Response format

The response is explicit **little endian**, with a 96-byte header and exactly the
declared payload bytes. It contains no pointers or native C padding.

| Offset | Field |
|---|---|
| 0 | Four-byte magic `WHTR` |
| 4, 6 | 16-bit version 1 and header size 96 |
| 8, 12 | 32-bit total response size and payload size |
| 16, 20 | 32-bit provenance and capabilities; capabilities must remain zero |
| 24, 32, 40 | 64-bit software session, generation and source scope |
| 48 | 64-bit host observation sequence, not a firmware sequence |
| 56, 64 | 64-bit local overflow/rejection counts before publication |
| 72, 76 | 32-bit declared copy point and reserved zero |
| 80, 88 | 64-bit application read ticket and reserved zero |
| 96 | Owned opaque payload |

Fixture copy-point labels simulate A/B. Replay accepts only an unknown copy point.
There is no live origin enum or capability bit that a caller can switch on.

The [Python decoder](../../research/export_contract/read_raw_response.py) requires
the expected ticket, session, generation and source. It rejects wrong extents,
identities, reserved fields and unsupported capability claims. It copies at most
the maximum response plus one rejection byte, then validates that immutable
snapshot. Mutable-input growth cannot bypass the bound. All returned hardware,
source-copy and clock qualification fields remain false.

## Build and run

With installed Visual Studio C tools and SDK, ordinary user permissions:

```powershell
powershell.exe -NoProfile -File research/export_contract/Build-RawEventBroker.ps1 -Architecture arm64
```

Use `-Architecture x64` for an x64 target that can execute locally. The script
builds the DLL, import library and native harness in
`artifacts/raw-event-broker-<architecture>`, then runs the harness with a 30-second
timeout. It downloads nothing and opens no device. Exit 0 means build/tests passed;
exit 1 means failure. Re-running rebuilds those generated artifacts. Rollback is
removal of that specific output directory after preserving useful receipts.

The configured cross-platform test command is:

```powershell
python -m unittest discover -s tests -p test_raw_event_broker.py -v
```

On Windows, initialize the installed developer environment first. Set
`WIFI_TIME_NATIVE_CC` to require a specific compiler. Without a compiler, the native
test skips; a skip does not validate it. The test also builds a shared library and
loads it from a Python child process, publishes a synthetic TSF replay, reuses the
source buffer, reads the owned response and decodes its retained event bytes.

To decode an independently saved broker response:

```powershell
python research/export_contract/read_raw_response.py artifacts/response.bin `
  --expected-ticket 1 --expected-session 11 --expected-generation 7 --expected-source 9
```

Supply identities from that application's actual request; the example numbers are
not hardware IDs. The decoder reads at most 4,193 bytes and writes diagnostic JSON
to stdout. Exit 0 means decoded, 1 rejected input/I/O, 2 CLI misuse. Keep captured
payloads and generated binaries out of public Git. No elevation or device rollback
is involved.

## Validation and remaining work

Local validation on 2026-10-05 passed **299 tests with zero skips** with the
installed ARM64 compiler and exact Windows-image fixtures configured. The native
DLL build and harness also passed through Windows PowerShell 5.1 after correcting
the launcher's completed-process exit-code handling. Python syntax, PowerShell
execution/parser checks, documentation navigation, index consistency and existing
diagram synchronization passed. No elevation was requested.

The native harness checks ownership after source reuse, malformed spans, small
outputs, bounded request slots, overflow sequence gaps, source-loss invalidation,
timeouts, cancellation before/during a wait, duplicate reads, and two-stage close.
It runs 80 cancellation/publication races, 40 close/publication races, and 1,200
publication attempts each with one and four readers. Concurrent tests verify
whole payload patterns, no duplicate deliveries and counter conservation.

An independent reviewer reproduced a P2 mutable-input size-check race in the first
Python decoder. The bounded snapshot fix and a controlled second-thread regression
resolved it. Review found no remaining P0/P1/P2 issues in the scoped code. Stress
tests and review do not exhaust every scheduler interleaving; deterministic
unrelated-wakeup/deadline-edge coverage remains a possible improvement.

The existing hosted workflow now includes a Windows broker build/test step, and
its Linux discovery includes the new native test. Hosted results belong to the
exact containing revision in [PR #3](https://github.com/Protonmatter/wifi-hardware-time/pull/3/checks).
Linux native execution and sanitizer runs remained unvalidated in the local
validation above; PSScriptAnalyzer was unavailable. No clock-read performance
target or hard real-time bound was qualified.

The live integration is still open. A kernel-side adapter must provide stable
source access, successful cache maintenance, complete publication, source loss and
continuity information, cancellation and teardown for the real driver return.
The user-mode broker does not implement those kernel operations. No live TSF
event, fresh sampling bracket, hardware-to-QPC conversion or synchronization
accuracy has been qualified by these software tests.

Return to [owned exporter research](../../research/export_contract/README.md) or
[current findings](../knowledge/current-findings.md).

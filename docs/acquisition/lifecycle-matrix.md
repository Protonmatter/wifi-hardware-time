# Conservative observation lifecycle

This offline model defines when a collected clock observation must become unusable: after a timeout, stale data, ambiguous reports, or a connection change. It tests software decisions, not device behavior. Restart, sleep and roaming tests remain preparation only, and a new software session cannot prove old firmware reports have stopped.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__acquisition__lifecycle-matrix.md).
<!-- /research-history -->

An epoch is one period of assumed clock continuity. Firmware drain means all earlier requests and reports have finished. TSF is the Wi-Fi timing counter; QPC is Windows' high-resolution host counter. See the [glossary](../glossary.md) for related terms.

The [prepared lifecycle cases](lifecycle-qualification-preparation.md) specify
the next distinct collector, restart, suspend, reassociation and roam experiments.
The latest authorization is preparation only. This model does not implement the
continuous diagnostic collector those cases require.

`research/acquisition/observation_lifecycle.py` implements a deterministic offline state model.
It has no timers, device handle, firmware transaction IDs or operating-system
event subscriptions. Its accepted state is `observed`, not a qualified clock
mapping. `max_age_ticks` is an explicit caller freshness policy, not accuracy.

| Event | Model behavior | Live qualification |
|---|---|---|
| New isolated acquisition session | Increment epoch; clear sample and pending request; acquire again | Collector/session isolation not yet implemented |
| Successful matched report | Preserve counter and host observation time | Saved report-window evidence only |
| Duplicate/mismatched report, overlapping request | Invalidate/quarantine | Synthetic tests |
| Request timeout | Invalidate; refuse reports and new requests until new session | Synthetic tests; no proven firmware drain |
| Counter regression or ambiguous wrap | Invalidate; do not unwrap speculatively | Synthetic tests |
| Freshness expires | Invalidate; no stale usable result | Synthetic tests |
| Disconnect/reassociation/restart | Invalidate even if endpoint counters increase | One prior restart; broader behavior unqualified |
| Suspend/resume, collector or trace loss, build change | Invalidate | Synthetic tests |
| Host time regresses | Invalidate and raise an error | Model behavior; not a QPC hardware fault claim |

Important precondition: calling `start()` after invalidation represents an
**externally established isolated/drained acquisition session**. This model
cannot prove that an old firmware report will not arrive in a new session. Until
a collector can establish that boundary, it must remain quarantined; restarting
a Python object or clearing a queue is not sufficient evidence of firmware drain.

`usable(tick)` means an admitted experimental observation is within the configured
host freshness window. It does not grant TSF-to-QPC conversion or reuse across a
bundle, device, boot or association. A runtime provider must bind source/build/
domain identities and deliver the real lifecycle notifications before adopting
these transitions. Pure tests do not substitute for disconnect, suspend or reset
qualification on hardware.

Run `python -m unittest discover -s tests -p test_lifecycle_evidence.py -v`.

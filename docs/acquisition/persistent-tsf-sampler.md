# Persistent TSF sampler v1

The bound campaign can reuse one worker and one qualified device session for action-4 requests. The implementation passed offline validation and subsequently completed a separately authorized [five-minute idle live smoke](persistent-tsf-smoke-2026-10-08.md), qualified as **conditional-research**. The existing per-request sampler remains the default. The worker retains unresolved I/O resources and durable campaign quarantine until actual completion is established.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__acquisition__persistent-tsf-sampler.md).
<!-- /research-history -->

## Scope and provenance

The implementation starts from `c620f47c94e4691347c6a905860fe435be1aa575`, the open settled-timestamps stack. `research/tsf/qualcomm_probe.py` remains the audited reference, unchanged. The persistent Win32 adapter intentionally duplicates its fixed device-open flags, action-4 payload, 128-byte input, 100-byte output capacity and overlapped layout; executable conformance tests check that contract. There is no arbitrary command interface.

Process reuse removes repeated worker setup. The existing report wait remains: the handoff's approximately 2.99-second cycle, 1.96-second delivery wait and 1.04-second other work are rounded user-reported figures, not measurements of this implementation or an exact decomposition. The subsequent smoke measured 2.005-second median and 4.009-second maximum request gaps; that is one run's result, not a guaranteed cadence or a controlled comparison with the historical hours. Its conditional coverage and bounds are reported with their denominators and assumptions. Previously unsupported synthetic-test counts remain withdrawn.

## Files and ownership

- [Sampler state machine](../../research/tsf/tsf_sampler.py): injected kernel, clock, controller owner, identity validator and evidence sink.
- [Win32 backend](../../research/tsf/sampler_win32.py): no device library is loaded at import; explicit live selection is required.
- [Worker](../../research/tsf/sampler_worker.py): retains the sampler for its whole lifetime, including indefinite unresolved drain.
- [Controller support](../../research/acquisition/persistent_sampler.py): file/mutex authorization, controller liveness, communication lease and fixed monotonic slots.
- [Receipt normalizer](../../research/tsf/sampler_receipts.py): validates provenance and constructs the existing analytical request through the sample screen.
- [Campaign](../../research/acquisition/run_bound_campaign.py): owns the adapter-scoped campaign mutex and unfinished-run record through cleanup and outcome persistence.

The controller creates the durable unfinished-run record before worker launch. The worker pins a controller process handle and checks its creation time, avoiding PID-reuse attribution. Readiness follows startup identity validation and handle opening. Each request needs a fresh sequential permit, consumed under the existing admission mutex. Revocation and submission use the same mutex; liveness is rechecked immediately before submission. Death concurrent with the native call is handled as an outstanding request that must drain. This protocol coordinates trusted local programs; it is not an authentication boundary against another process running as the same user.

Process death and unreadable/corrupt control records are detected on polling. A live but stalled controller loses its communication lease after 60 seconds; this permits the existing bounded identity lookup. No future request is authorized by the lease. The worker checks ownership between finite I/O waits. No sampler timeout invokes terminate/kill, and there is no automatic quarantine reconciliation.

## State and resource lifetime

```text
NEW -> READY -> IN_FLIGHT -> COMPLETED_SUCCESS -> READY
                       -> COMPLETED_ERROR -> STOPPED
                       -> DEADLINE_EXCEEDED -> CANCEL_REQUESTED
                       -> QUARANTINED_DRAIN_PENDING -> terminal completion -> STOPPED
READY/STOPPED + no outstanding I/O -> verified handle close -> CLOSED
```

Deadline failure and any cancellation attempt are sticky even if final I/O completes normally. The initial deadline is two seconds, with finite polls of at most 50 milliseconds. `WAIT_TIMEOUT`, `ERROR_IO_INCOMPLETE` and `CancelIoEx` returning `ERROR_NOT_FOUND` do not establish completion. Wait failures and exceptions fail closed. The process retains the input/output buffers, `OVERLAPPED`, event and device handle while completion is unresolved. `close()` returns false while drain is pending. The worker continues draining even after controller loss or ordinary exceptions. Forced OS termination, power loss and hardware failure cannot be repaired by Python; the unfinished-run record then blocks further admission.

These choices follow Microsoft's [CancelIoEx contract](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-cancelioex) and [overlapped completion guidance](https://learn.microsoft.com/en-us/windows/win32/api/ioapiset/nf-ioapiset-getoverlappedresultex).

## Receipt contract and migration

The schemas are `wht/persistent-tsf-request-v1`, `wht/persistent-tsf-session-v1` and `wht/persistent-tsf-control-v1`. Persistent requests never contain `handle_closed`. They record session/sequence, action/protocol provenance, QPC frequency and submission/completion ticks, initial result, wait, deadline, cancellation result, terminal I/O result, returned extent and response bytes. Unknown completion timestamps remain null. Only session evidence records actual handle closure.

The worker writes append-only raw snapshots to `sampler-events.jsonl`, an immutable start snapshot to `sampler-session-start.json`, a current/final snapshot to `sampler-session.json`, and per-sequence raw `sampler-request-*.json` files. Unchanged drain snapshots are deduplicated so indefinite polling does not grow the journal indefinitely. Snapshots and control changes use flush/fsync plus atomic replace with unique temporary filenames. Internal readers and writers use the same admission mutex to avoid Windows file-sharing races. These files contain private adapter provenance and must remain in ignored local campaign artifacts. A disk failure stops submissions; the durable unfinished-run record is not cleared.

`requests.jsonl` retains completed controller receipts without rewriting worker evidence. Unknown schemas, missing fields, inconsistent clocks/provenance, session mismatch, invalid response extents and unresolved completion fail closed. Unversioned legacy receipts retain exactly the previous `success is True`, `handle_closed is True` and no-cancellation eligibility decision. A completed request can be analytically eligible while its session is still open. The run loader requires matching start/final session evidence, contiguous sequence records, a closed handle and zero outstanding operations before a campaign can be cleanly completed.

No sample thresholds, rate bounds, polygon operations, golden replay values or consumer APIs change. Replay retains its existing arrival rule (last required report-group arrival and request completion); controller processing, IPC and persistence delays are recorded separately and are not newly added to that analytical availability formula. They remain in the acquisition elapsed-time and achieved-spacing measurements. Online admission is deferred.

## Scheduling and report wait

`--sampler per-request` remains the default with two-second requested spacing. `--sampler persistent` defaults to one second; both retain the 0.5-second minimum. Persistent requests use fixed monotonic slots, skipping missed slots without catch-up bursts. A previous actual submission constrains the next slot so even late submissions preserve minimum spacing. Identity rechecks use a 30-second monotonic timer, with startup and final checks retained.

Long slot waits continue observer pumping, heartbeat renewal and periodic identity checks without granting a request. If an identity check misses a selected slot, the controller skips that slot and waits for the next eligible fixed slot.

`sampler-schedule.jsonl` records scheduled slots, skipped slots, actual QPC submission/completion, report original timestamp, report receipt timestamp, report wait, identity-check time, processing time and actual gaps. Identity and report-delivery delays remain in those gaps. The existing five-second report wait and own-loss policy, trace/observer/lifecycle/association checks and final trace verification remain in effect.

## Operation and rollback

Python 3.11+ and the repository's existing requirements are needed for offline checks. Live mode additionally requires Windows, the exact qualified adapter/driver, existing native observer/decoder artifacts, administrator rights and separately authorized acquisition. Nothing in this document authorizes a live run or elevation.

Inspect syntax without adapter discovery:

```powershell
python research/acquisition/run_bound_campaign.py --help
python -m research.tsf.sampler_worker --help
```

Future explicitly authorized invocation template (substitute the exact interface; do not run during phase 1):

```powershell
python research/acquisition/run_bound_campaign.py --sampler persistent --if-index <INDEX> --condition idle --duration-s 300 --execute
```

Campaign exit 0 requires successful persisted outcome and verified worker lifecycle; exit 1 means stopped/failed/quarantined. Invalid CLI arguments exit 2. Unexpected setup errors are nonzero and do not clear unfinished evidence. `--execute` does not self-elevate. Default campaign preview still uses existing read-only identity discovery; phase 1 validation invokes help and injected tests only.

`--etw-flush` (persistent sampler only) flushes the trace session after each completed request so the report group reaches the observer in milliseconds instead of waiting for the one-second flush timer. The plan records `etw_flush_after_completion`, and each `sampler-schedule.jsonl` row records the flush receipts in `etw_flushes`. A failed flush is recorded, not fatal; delivery then falls back to the timer. Each flush writes partially filled per-CPU buffers to the trace file, so the flag increases trace growth; measure it in a short run before an hour-long run, because the campaign stops at its trace cap. The flag does not authorize a run.

Rollback to legacy operation selects `--sampler per-request` or omits the option. Do so only after a completed lifecycle; changing mode never bypasses an unfinished/quarantined run. An unresolved worker must retain its resources, and its marker must not be removed as a convenience. Preserve evidence and reconcile explicitly before any later acquisition.

## Offline acceptance map

Run these from the repository root. All new tests inject hardware, identity, time and controller boundaries.

```powershell
python -m compileall -q research tests
python -m unittest discover -s tests -p test_tsf_sampler.py -v
python -m unittest discover -s tests -p test_sampler_win32.py -v
python -m unittest discover -s tests -p test_sampler_worker.py -v
python -m unittest discover -s tests -p test_persistent_receipts.py -v
python -m unittest discover -s tests -p test_persistent_controller.py -v
python -m unittest discover -s tests -v
python research/evidence/build_knowledge_index.py --check
python research/evidence/sync_workflow_diagrams.py --check
```

| Invariant | Executable test coverage |
|---|---|
| Immediate success, sequential requests, no stale output/event reuse | `SamplerTests.test_immediate_success_keeps_handle_and_resets_next_request` |
| Pending success, terminal error, output extent rejection | `test_pending_then_success_no_early_release`, `test_terminal_error_stops_session`, `test_returned_capacity_violation_fails_closed` |
| Deadline, cancelled completion, normal completion race | `test_deadline_normal_completion_and_cancelled_completion_stay_failed`, `test_cancel_abort_is_terminal_but_not_success` |
| Cancel not found, never completing I/O, finite polling | `test_not_found_does_not_establish_completion`, `test_never_completes_retains_resources_and_rejects_new_requests` |
| Wait failure, exceptions, close while pending | `test_wait_error_and_exception_preserve_ownership`, `test_submission_exception_is_ambiguous_and_retained`, `test_close_pending_requests_cancel_without_releasing` |
| Controller loss before submit and during wait | `test_controller_loss_at_submission_boundary_never_submits`, `test_controller_loss_during_wait_cancels_and_drains` |
| Repeated close, fresh permits, persistence failure | `test_repeated_clean_close_closes_once`, `test_no_permit_or_stale_sequence_never_submits`, `test_receipt_write_failure_stops_before_submission` |
| Exact payload/ABI and hardware path isolation | `test_payload_matches_audited_action4`, `Win32Tests` |
| Worker retained after controller/disk failure, bounded journal growth, Windows file-sharing serialization | `WorkerTests` (includes actual local named mutex and file I/O, with no device access) |
| Legacy compatibility and strict session/request schema | `ReceiptTests` |
| Default mode, fixed slots, identity timer, communication loss | `ControllerTests` |
| Report wait retained, identity delays, observer stop and no next request | `test_persistent_campaign_keeps_report_wait_and_stops_on_observer_failure` |

The accompanying implementation report records actual commands, counts, skips and platform. Synthetic results do not establish live adapter behavior, firmware drain or performance.

## Phase 2 and proposed first live check

Phase 2 explicitly includes live adapter requests, UAC elevation, report-wait decoupling, online admission, mathematical/API changes and merging. They are separate work items with separate applicable authorization; passing phase 1 tests does not authorize them.

Before a proposed five-minute idle test:

1. Review the exact local patch, base/stack and offline evidence; select an explicit target and approve the live test/elevation as applicable.
2. Re-identify the qualified adapter/driver and observer/decoder builds. Review existing quarantine and unfinished-run evidence; never clear it automatically.
3. Confirm controller/worker readiness, one request at a time and preserved report wait. Retain original timestamps, all rejection/loss records and achieved gaps.
4. Test the reviewed stop/drain procedure within the approved scope. Verify terminal I/O, zero outstanding operations, actual handle closure and final identity/trace checks.
5. Analyze measured arrival-aware coverage over a declared elapsed-time denominator, accepted-sample gaps and settle waits. Keep any physical/AP/UTC qualification separate.

The proposed five-minute smoke was subsequently authorized and completed; see its [dated evidence](persistent-tsf-smoke-2026-10-08.md). Longer idle/load campaigns, removing report wait, exact polygon clipping, settlement policy changes and bounded-wander estimates remain later experiments. The [roadmap](../overview/persistent-tsf-next-steps.md) defines their separate gates. Publication of this implementation does not authorize another hardware campaign or a downstream consumer change.

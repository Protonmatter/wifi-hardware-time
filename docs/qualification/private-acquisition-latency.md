# Private acquisition latency: measured stages and the next bounded experiment

Audit date: 2026-10-03. This is a source audit and fresh offline recomputation of
the existing `QualcommCampaign-ecfaed68f20e` artifacts. No private request, trace,
elevation, adapter change, or clock write was performed for this document.

Subsequent qualification: the corrected observer has been rebuilt, selected and
passed [two passive live checks](observer-passive-qualification-2026-10-03.md).
The historical measurements and source-audit findings below remain separate from
that later pass; private-command delivery latency has not been remeasured.

The tested private path already returns host-observed IOCTL completion in tens
of microseconds and emits its driver report log in hundreds of microseconds.
The roughly 1.6-second report-delivery delay is a separate collection problem.
Prioritize that path for raw acquisition experiments, while retaining QPC reads
for an application's fast local timestamp operation. A microsecond/nanosecond
representation does not establish timestamp accuracy or event reference point.

## Evidence and measurable reference points

The [completed campaign](acquisition-campaign-2026-10-02-results.md) contains
138 accepted requests: 120 action-3 READ_VALUE and 18 action-4 QTIMER_CAPTURE,
in 12 captures, split into 69 idle and 69 local-workload observations. This is
the campaign's saved evidence, not a new assertion about the currently active
adapter. QPC frequency in these artifacts is 10,000,000 Hz: one raw host tick
is 100 ns. Scaling those ticks to integer nanoseconds adds no information.

| Stage | Existing field/source | What it actually measures |
|---|---|---|
| Firmware sample / packet event | TSF and SoC payload fields; FTM diagnostic operands | Raw counters or deltas; exact sampling instant, simultaneity, units and packet identity are not all established |
| Request submission bracket | `qualcomm_probe.py`: `qpc_request_before` | Host QPC immediately before the private `DeviceIoControl` call |
| Host-observed completion | `qpc_request_completed` | Host QPC after return or overlapped completion; not a firmware-completion fence |
| Driver report emission | `decode_tsf_etl.c`: `raw_timestamp` | ETW event-header timestamp, preserved in the controller-selected QPC domain |
| Native consumer callback entry | `live_observer.c`: `live_event` | **Not recorded** in the existing campaign |
| Native stdout write | `on_event` called inside `output_lock` | Numeric serialization to unbuffered stdout; no separate before/after timestamps |
| Python reader receipt | `Observer._read`: `received_qpc` | QPC after Python receives a complete line, before queue insertion |
| Controller acceptance | `admission-*.json`: `accepted_qpc` | After queue processing, child completion, request validation and gate completion |
| Application model publication/read | No campaign field | No hardware-backed application model was published or timed by this campaign |

The native callback and Python reader are different boundaries. A buffer-health
record's QPC is sampled after processing that buffer's events; it cannot replace
an individual event's callback-entry measurement.

## Fresh recomputation from saved records

Medians use the ordinary median; p95 uses nearest rank. Units and sample counts
are explicit. No raw interface/AP identity is included here.

| Interval | Idle median / p95 / max | Workload median / p95 / max |
|---|---|---|
| Submission to completion, 69 per phase, us | 53.5 / 108.0 / 150.7 | 54.1 / 110.2 / 468.9 |
| Submission to report log, 69 per phase, us | 270.3 / 700.4 / 869.0 | 262.8 / 739.5 / 1047.7 |
| Report log to Python reader, 69 per phase, ms | 1649.3268 / 1890.5339 / 2833.6695 | 1606.5463 / 1838.8011 / 2546.3741 |
| Native connection-record QPC to reader, 1161 / 1180 records, us | 167.3 / 258.6 / 89787.4 | 169.9 / 252.5 / 114479.7 |
| Native buffer-health QPC to reader, 6535 / 6568 records, us | 112.8 / 751.3 / 2032.9 | 105.3 / 630.2 / 2476.4 |
| Report reader receipt to controller acceptance, 69 per phase, ms | 29.7708 / 40.0231 / 41.5366 | 29.2226 / 40.2941 / 41.9561 |
| Actual request-start separation, 63 within-run pairs per phase, s | 4.0451 / 4.2722 / 4.9403 | 4.0273 / 4.1879 / 5.2420 |
| Next request start minus previous acceptance minus requested spacing, 63 pairs per phase, s | 1.9164 / 2.0782 / 2.1503 | 1.9637 / 2.1432 / 2.4715 |

Reproduction uses each run's sorted `request-*.json`, `admission-*.json` and
`live-observer.jsonl`; pair ordered reports with ordered requests only after the
existing run's accepted count/order checks. Divide QPC differences by the saved
frequency. The final row subtracts 0.25 s for read captures or 0.5 s for mixed
captures. It includes wait overshoot, identity checks, process startup, discovery
and admission; it does not isolate any one of those costs.

These new control-record measurements make ordinary pipe delivery an unlikely
explanation for the median 1.6-second report lag. They do not prove the precise
share due to ETW buffering, scheduling, provider behavior, or callback locking:
the controls and report events have different production paths. Connection-record
outliers also show that occasional scheduling/transport stalls remain possible.

## Concrete source findings

1. **The session already uses the minimum timer-based flush interval.**
   `run_acquisition_campaign.py::capture` starts QPC, real-time plus circular
   file tracing with `-ft 00:00:01`, capped at 32 MiB. Microsoft specifies a
   minimum one-second `FlushTimer`; zero means the default one second for
   real-time sessions. A proposed 1 ms `FlushTimer` would not implement the
   desired experiment. Buffers also flush when full. `BufferSize` is in KiB;
   smaller buffers may fill sooner but do not bound low-rate delivery latency.
   The existing command does not explicitly select buffer size. Query the actual
   session settings before comparing variants. [Microsoft EVENT_TRACE_PROPERTIES](https://learn.microsoft.com/en-us/windows/desktop/ETW/event-trace-properties)

2. **The observer already disables C stdout buffering.**
   `live_observer.c` calls `setvbuf(..., _IONBF, ...)`. Adding `fflush(stdout)`
   is therefore not an explanation or demonstrated fix for this campaign's lag.
   Formatting and synchronous pipe writes occur under one critical section shared
   with connection/lifecycle/health output. A blocked writer can delay callbacks;
   measure callback entry before that lock and write completion separately.

3. **The 20 ms controller and admission polling add avoidable latency.**
   `Observer.wait`, the request/report loop, and `Admission.wait_permission` use
   `time.sleep(0.02)`. The controller's post-pump sleep can occur even when the
   current iteration just observed completion. This is consistent with the
   measured roughly 30 ms report-receipt-to-acceptance interval. It cannot explain
   the earlier 1.6-second log-to-reader interval, because the reader stamps before
   the controller queue is processed. Event-driven waits are a subsequent
   optimization; retain the named-mutex submission/revocation guarantee.

4. **The command line repeats expensive setup before each private request.**
   The parent invokes PowerShell for `identity(index)` each time. Each new Python
   probe invokes a second PowerShell discovery script, reads and validates the
   driver, prepares ctypes interfaces, waits for permission, and opens its handle.
   The measured approximately 1.9-second residual identifies a substantial
   setup/admission budget, without attributing all of it to PowerShell. Timestamp
   these stages before considering a persistent probe or cached discovery. Do not
   remove exact-target/build/lifecycle checks simply to improve throughput.

5. **P1 in the campaign observer: live loss admission used an unused field.**
   The campaign version of `live_observer.c::buffer_callback` printed outer
   `EVENT_TRACE_LOGFILEW.EventsLost`; Microsoft marks that member unused. The
   campaign gate's `live_trace_loss` check therefore does not establish timely loss
   detection. The existing offline decoder reads the distinct
   `LogfileHeader.EventsLost` and `LogfileHeader.BuffersLost`; its final header
   checks and live/offline record equality remain separate evidence and are not
   invalidated by this finding. Before another private latency trial, add bounded
   controller queries of `EventsLost`, `LogBuffersLost` and `RealTimeBuffersLost`
   to admission, and retain final stopped-session/header checks. Test nonzero and
   unavailable health responses rejecting the next submission. [Microsoft EVENT_TRACE_LOGFILEW](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/ns-evntrace-event_trace_logfilew)

## Source correction status at initial review

At this report's initial review, the source correction was uncommitted. It removes that buffer-health callback. Later [passive qualification](observer-passive-qualification-2026-10-03.md) and the [quarantined private repeat](private-campaign-2026-10-03-quarantine.md) record subsequent execution; see the [current ledger](gap-closure-ledger.md).
The observer's main/control thread now calls `ControlTraceW` with
`EVENT_TRACE_CONTROL_QUERY` during its nominal 250 ms monitoring cycle, outside
the ETW event callback. The cycle is not a hard maximum query period: synchronous
API calls, scheduling and output can extend it. Health records include query
status plus `EventsLost`, `LogBuffersLost` and `RealTimeBuffersLost`. Readiness
advertises `health_schema: controller-query/v1`; the gate rejects legacy records,
failed queries, invalid/missing/Boolean/negative/out-of-range counters and any
reported loss.

If owner shutdown races a query and the session is already missing, the observer
waits at most five seconds for successful `ProcessTrace` completion before treating
that result as normal shutdown. Otherwise it reports failed health and exits
unsuccessfully. Read-only review found no new concrete defect in this change's
cleanup, race handling or schema checks.

The author compiled the changed observer for ARM64 with `/W4 /WX` into ignored
`artifacts/live_observer-health.exe`, preserving the campaign binary. Independent
review ran `python -m unittest discover -s tests -p 'test_campaign*.py' -v`:
**11 tests passed**, including the new health-schema and controller-loss tests.
This validates source behavior and compilation, not new live loss detection,
controller query timing, the stop race, or private acquisition.

The controller still selects `artifacts/live_observer.exe`. The new gate will
deliberately reject the preserved legacy binary before private admission. A
reviewed build selection/replacement and refreshed source/binary qualification
receipt are required before another run. The historical metrics above belong
to the old observer; replacing its health emission also changes observer load,
so do not present them as measurements of the corrected implementation.

## Minimum-risk next experiment, not executed

First add instrumentation and complete qualification of the live-loss source
correction. Preserve the existing numeric timing parser and its live/offline
comparison: place callback/write/queue/publication timings in separate diagnostic
records keyed by capture-local sequence, rather than changing the timing records
that the gate compares. Record QPC API success and loss of diagnostic records.

Use one prospective campaign with the **same 138 private actions, same 12
sequences, one outstanding request, same exact-build/adapter/AP admission,
quarantine, cancellation/drain rules and 15-second request deadline**. This is a
proposal for a separately authorized run, not permission to rerun it now. Fix a
start schedule from the matching saved run's relative request-start offsets;
never submit earlier, and wait longer if completion/admission requires it. Also
retain the 250/500 ms post-completion minima. This prevents faster collection
from silently increasing private request cadence.

Within that fixed campaign, preassign balanced baseline/treatment requests by
action and workload. Baseline retains the one-second timer. Treatment adds a
controller-owned `EVENT_TRACE_CONTROL_FLUSH` attempt every 100 ms while waiting
for that request's report, capped at 150 attempts and the existing deadline.
Do not spawn `logman` for each attempt or flush from the consumer callback. Stop
the treatment timer when the report gate completes; retain the session and its
existing provider/keywords/file cap. Log every flush start/end/status and measure
CPU, event loss, file growth, and callback lag. The 100 ms value is an experiment
setting, not a timing SLA. Flush requests cannot force firmware to produce an
event or establish its sampling instant. [Microsoft ControlTraceW](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-controltracew)

Report each interval separately: log-to-callback, callback-to-write,
write-to-reader, reader-to-gate, and gate-to-model-publication if a model exists.
Include every request, invalid period, loss count, maximum and percentile; stratify
by action and workload. A shorter delivery interval supports only a collection
improvement claim. If the treatment does not materially improve callback arrival,
investigate provider emission and consumer scheduling before replacing ETW.

Rollback is stopping only the trial's named ETW session, joining its observer and
flush worker, restoring the baseline collector binary/configuration, and retaining
quarantine if any request remains ambiguous. No pending private-I/O process is
forcibly terminated. No firmware action, register command, automatic reporting,
driver modification or adapter reset is added.

## Raw TSF/FTM priority and accuracy boundary

Continue preserving raw integer counters and their source identity. The campaign
shows that action 4 refreshes the reported SoC value, while eligible adjacent
action-3 observations reuse it; action 3 is not a fresh SoC-sampling API. TSF
progresses at roughly one million raw ticks per host second in this evidence,
but TSF/SoC simultaneity and a qualified mapping remain open. Preserve host QPC
alongside the raw values instead of relabeling them as nanosecond hardware event
times. [Campaign freshness results](acquisition-campaign-2026-10-02-results.md)

The tested FTM path is useful evidence for ranging/firmware delivery, but its
current callback is an aggregate RTT result. The inspected operands and 51 saved
delta triplets establish subtraction, not recoverable absolute t1..t4. Reducing
ETW delay cannot recover those missing timestamps or offset information. Keep
FTM event-field investigation separate from this action-3/action-4 latency trial;
no FTM request is added here. [Clock relationship investigation](clock-relationship-investigation.md)

ETW can preserve original QPC event timestamps even when delivery is delayed:
`PROCESS_TRACE_MODE_RAW_TIMESTAMP` is already enabled by the observer and offline
decoder. Thus delivery latency alone does not disqualify ETW as an evidence
transport. It does prevent blocking an application timestamp read on this
collector, and it increases the age/error budget of any eventual model. Hardware
sample-to-host mapping and independent accuracy remain separate qualification
gates. [Microsoft EVENT_HEADER](https://learn.microsoft.com/en-us/windows/win32/api/evntcons/ns-evntcons-event_header)

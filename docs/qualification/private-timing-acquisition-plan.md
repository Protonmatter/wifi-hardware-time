# Private timing acquisition: practical research direction

The research is not limited to public NDIS or Windows APIs. Exact-build private
exports, IOCTLs, firmware commands and instrumented report paths are legitimate
candidates. The user's 2026-10-03 direction explicitly prioritizes the private
TSF/FTM mechanisms already discovered and exercised. Public timestamp interfaces
remain comparative probes; their failure does not gate the private backend.

This plan changes the research priority. It does not claim a new live command,
raw timestamp export or calibrated clock has already been qualified.

Latest execution state: the subsequent [private campaign quarantined on unmatched
reports](private-campaign-2026-10-03-quarantine.md). Its marker remains in place;
the passive observer qualification does not authorize automatic rearm.

Related exact-build work: [private TSF/TX routes](private-tsf-fast-paths.md) and
[saved-capture latency decomposition](private-acquisition-latency.md).
The latest offline follow-up identifies [changed SoC values in the unmatched
reports and a pre-ETW host-memory ring](unmatched-tsf-and-memory-log.md).
The ring has internal copy/file consumers; a safe userspace retrieval contract
and concurrent-copy consistency are not yet established.

## Four quantities that must remain separate

1. **Raw resolution:** counter tick period and any fine event-time fields.
2. **Reference semantics:** what physical or firmware event was sampled.
3. **Delivery/freshness:** when the record becomes available to the application.
4. **Accuracy:** error relative to another clock or physical reference.

A precise timestamp can arrive late. A fast API can return a cached counter.
Nanosecond or picosecond field units do not prove that resolution or accuracy.
For the private Qualcomm TSF/SoC fields, retain integer raw values and unqualified
units wherever producer semantics are still unknown. Formatting microsecond
values as nanoseconds adds no information. FTM delta/aggregate values do not
recover the missing absolute clock phase.

## Candidate paths and admission requirements

| Path | Current evidence | Next practical question |
|---|---|---|
| Private `QcomWifi` IOCTL `0x00220182`, `tsf_read_value`, action 3 | Repeated live delivery; IOCTL output is a zero-filled argument block, raw counters arrive asynchronously | Can the full counter report be returned through an existing private completion/getter instead of logs? |
| Same path, action 4 / QTIMER_CAPTURE | Refreshes the SoC field; tested mixed sequences | Where does the refreshed pair exist, what samples it, and can that data be exported before reduction? |
| Internal Windows FTM exports and callbacks | Real requests and result callbacks exercised with exact DLL hashes | Is there an earlier private result path preserving event values and exchange identity before aggregation? |
| Private `tsf_auto_report` | Command-table and dispatcher evidence | Establish arguments, firmware actions, ownership, disable/restore semantics and report rate before a bounded live trial |
| Raw FTM firmware ingress | Complete pre-aggregation records exist internally | Establish actual fields and a producer-to-consumer path; a supported public export is not a prerequisite for investigating a private one |
| `read_reg` / athdiag QMI | Route identified; clock address space and benign target not qualified | Establish exact memory type, register semantics, read side effects, coherency and transport timing before a single targeted read |
| Instrumented private driver/report bridge | Engineering option, not implemented | If no existing export preserves the data, define a narrow capture point and a minimal explicit userspace return contract |

The existing allowlist records what is qualified today, not a permanent feature
boundary. Extend it when a new path's exact input/output and state semantics are
established, with positive and rejection fixtures. Do not turn unknown commands
or addresses into a blind search. A driver replacement, kernel instrumentation
or a stateful firmware command is a different operation from repeating an already
qualified getter and requires its own concrete operational/recovery design.

## Next experiment: separate acquisition from transport

Use the already exercised action-3/action-4 requests, within existing request
count/cadence limits, to measure the delivery path before increasing request load:

```text
host submission -> IOCTL completion
                 firmware/driver report -> ETW timestamp
                                       -> callback-entry QPC
                                       -> reader QPC
                                       -> admitted observation QPC
```

The firmware sampling point is not established by any of those host times. Add a
native callback-entry timestamp and a sequence association so ETW delivery can
be separated from stdout/reader transport and controller admission. Preserve
timeout/ambiguity quarantine, lifecycle observation, exact-build/target checks,
and complete controller plus offline trace-loss validation.

The local observer source now emits `controller-query/v1` health using an actual
ControlTrace QUERY outside the ETW callback. The gate rejects the legacy ready
record and unused-counter health format before private admission. Rebuild the
observer before running the campaign after a source change. The corrected observer
is now selected at `artifacts/live_observer.exe` and has passed
[two passive live checks](observer-passive-qualification-2026-10-03.md). The legacy
binary is retained in the qualification backup directory. Future builds can use
an installed ARM64 MSVC developer shell after retaining the previous executable:

```powershell
cl.exe /nologo /W4 /WX /O2 experiments/qualcomm/live_observer.c /Foartifacts/live_observer.obj /Feartifacts/live_observer.exe /link /MACHINE:ARM64 advapi32.lib wlanapi.lib iphlpapi.lib
```

Do not remove the new gate checks to run the old executable. Revalidate the
passive observer, lifecycle events, final loss counters and cleanup before private
commands are admitted by a rebuilt acquisition campaign.

Compare the current delivery baseline with one bounded explicit-flush experiment,
recording flush duration/status and CPU cost. ETW FlushTimer has a one-second
minimum; setting it to a subsecond value or zero is not a low-latency solution.
ControlTrace FLUSH is a candidate to measure, not a guaranteed microsecond path.
[Microsoft session properties](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/ns-evntrace-event_trace_properties),
[ControlTrace](https://learn.microsoft.com/en-us/windows/win32/api/evntrace/nf-evntrace-controltracew).

In parallel, trace existing private full-width report consumers and investigate
a direct return channel. Optimizing ETW must not become a requirement to keep ETW
in the eventual runtime. It can remain a diagnostic side channel even if the
application provider obtains observations through an IOCTL completion, private
callback or a purpose-built narrow bridge.

Do not simply keep the existing control-device handle open or remove repeated
identity checks as a performance shortcut. A persistent collector needs explicit
request ownership, cancellation/drain handling, epoch invalidation and observed
continuity first. Changing collector or ETW sessions does not prove old firmware
reports have drained.

## Raw FTM and packet events

Trace the raw record producer and its handoff before the known delta subtraction
and aggregation. A hook around an already aggregated userspace callback can
measure callback overhead but cannot reconstruct discarded event information.
Private API status is not a reason to exclude a route; loss of the required
information is.

For each recovered event retain raw width, units/tick period if established,
clock/epoch, physical reference point, direction, validity/error flags and the
actual firmware/frame/exchange identity. A request-scoped ID is not automatically
a per-frame/retry ID. Timestamp-register access does not by itself establish
packet timestamps. FTM ranging and arbitrary RX/TX events remain separate
capabilities even when they share transport or hardware.

## Application architecture

```text
private/native acquisition -> validated observations -> qualified model snapshot
                                                       |
application timestamp read -> QPC -> snapshot evaluation + explicit quality
```

Consumers should not invoke firmware or wait for ETW on every clock read. Raw
hardware observations remain available as a separate API capability. A derived
clock uses a background observation model only after its clock relationship and
error/expiry rules are qualified. Late delivery affects freshness and holdover;
it does not justify relabeling a host receipt time as the hardware event time.

The maintained runtime belongs in `userspace-clock`; exact-build exploration and
qualification stay here. Preserve independent capability states for raw reports,
clock conversion, packet event timestamps, node synchronization and OS discipline.

No second node or independent reference is currently available. That limits
external accuracy validation; it does not block private-path engineering,
latency measurement, raw-field recovery or local consistency tests. The term
"AS" in the user's request remains to be clarified and is not assigned to a
particular command or hardware feature here.

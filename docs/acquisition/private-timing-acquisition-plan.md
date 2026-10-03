# Private timing acquisition: practical research direction

This plan prioritizes the private clock-report paths already found in the Qualcomm driver. It separates raw counter access, report delivery, sampling meaning and accuracy so progress in one does not imply the others. Private acquisition remains quarantined; further investigation must establish safe retrieval and report identity before another live campaign.

Private means an interface outside the documented public API. TSF is the Wi-Fi timing counter, SoC denotes the reported system-on-chip counter, and FTM is Wi-Fi Fine Timing Measurement. QPC is Windows' high-resolution host counter; ETW is its event-tracing system. See the [glossary](../glossary.md) for related terms.

## Contents

- [Four quantities that must remain separate](#four-quantities-that-must-remain-separate)
- [Candidate paths and admission requirements](#candidate-paths-and-admission-requirements)
- [Next experiment: separate acquisition from transport](#next-experiment-separate-acquisition-from-transport)
- [Raw FTM and packet events](#raw-ftm-and-packet-events)
- [Application architecture](#application-architecture)

Execution update: the [scan campaign](scan-tsf-results-2026-10-03.md) and [timing-boundary investigation](../memory-ring/timing-boundary-investigation-2026-10-03.md) now narrow the producer and return-path questions. Private acquisition remains quarantined; [lifecycle work](lifecycle-qualification-preparation.md) is preparation only.

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

Related exact-build work: [private TSF/TX routes](../tsf/private-tsf-fast-paths.md) and
[saved-capture latency decomposition](private-acquisition-latency.md).
The latest offline follow-up identifies [changed SoC values in the unmatched
reports and a pre-ETW host-memory ring](../memory-ring/unmatched-tsf-and-memory-log.md).
The ring has internal copy/file consumers; a safe userspace retrieval contract
and concurrent-copy consistency are not yet established.
The [subsequent passive live check](passive-and-retrieval-validation-2026-10-03.md)
passed without private requests. Its saved-trace follow-up also identified a scan
command shortly before the first unmatched report; causality remains unproved.

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

This proposed experiment remains blocked by the private quarantine. After separately reviewed recovery and authorization, it would use the previously exercised action-3/action-4 requests within existing count/cadence limits to measure delivery:

| Proposed measurement boundary | What the host observes |
|---|---|
| Submission to IOCTL completion | Driver-request call and completion |
| Driver report to ETW timestamp | The diagnostic log event |
| Callback entry to reader receipt | Native collector and pipe delivery |
| Reader receipt to admission | Controller validation |

These are host stages; their order does not identify the firmware sampling instant.

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
cl.exe /nologo /W4 /WX /O2 research/acquisition/live_observer.c /Foartifacts/live_observer.obj /Feartifacts/live_observer.exe /link /MACHINE:ARM64 advapi32.lib wlanapi.lib iphlpapi.lib
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

**Proposed architecture, not a qualified runtime:**

1. A background collector obtains and validates observations.
2. A qualified clock model would publish a snapshot with quality and expiry rules.
3. An application would read QPC and evaluate that snapshot, returning its quality state.

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

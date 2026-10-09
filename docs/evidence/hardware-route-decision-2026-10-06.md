# Hardware route decision: current Qualcomm integration is no-go

The current installed Qualcomm route is **no-go for live complete-event integration**. A supported vendor interface or instrumented producer with demonstrated access has not been established. The installed QMSL 6.1.365.1 callback chain is useful completed static evidence, but it does not supply the missing Wi-Fi endpoint, timing producer or bounded shutdown contract. This closes the S2 decision slice with a specific external prerequisite; it does not close the hardware acquisition gate.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__evidence__hardware-route-decision-2026-10-06.md).
<!-- /research-history -->

Decision date: 2026-10-06, America/New_York. Evidence baseline: research commit
`aca5b7ca7c96ca8731f15202361c34faf003f350`. See the
[current PR component map](../overview/pr3-component-review-map-2026-10-06.md)
for exact remote base/head and the distinction between tests and review coverage.
This decision reads existing evidence only; it adds no vendor execution,
hardware acquisition, binary trace or hardware-absence claim.

**Installed WPP follow-up:** the [WPP External 2.3.1.1 file assessment](wpp-external-2311-file-assessment.md)
now identifies concrete WLAN/firmware/diagnostic-bridge ETL collection scripts.
This narrows tool availability, but establishes no complete-payload callsite or
attributable live producer. Its Wi-Fi trigger changes logging and disables/enables
the device. No vendor tool ran; the no-go and reopening criteria are unchanged.

## Complete-event gate evaluation

The first milestone is an attributable, complete **diagnostic event**, even if
its timing semantics remain unknown. A complete timestamp and clock conversion
need the additional [raw timestamp gates](raw-timestamp-export-gate.md). The
[complete-event acceptance criteria](../overview/complete-event-2026-10-05/problem-and-scope.md)
give the following result for the current QMSL/Qualcomm route.

| Gate | Existing evidence | Decision and missing proof |
|---|---|---|
| Exact source and usable entry route | Current native and managed QMSL files are pinned; x86 CLR smoke used authored code only. QUTS connection consumes discovered handles | **Not met.** No attributable live device/protocol or supported user transport connects the installed PCI Wi-Fi target to this callback. File presence and method-name matching do not prove vendor startup or entitlement |
| Valid original source span and lifetime | Selected worker transfers binary/additional-payload ownership to the listener; V2 callback receives original bytes before application copying | **Partial static evidence.** Exact Wi-Fi producer, all upstream validity/short-envelope paths, actual lengths and callback lifetime under the selected operation remain unqualified |
| Complete owned application copy and publication | User-mode broker and source-operation fixtures preserve owned bytes and identities; QUTS client allocates payload storage | **Software only.** No complete original timing event has crossed the real producer-to-application boundary |
| Source identity, live/replay provenance and continuity | Separate live transport and playback leads exist; software tickets/generations are retained by the broker | **Not met for hardware.** No demonstrated producer/build association or live-versus-playback attribution for an acquired Wi-Fi record; software IDs do not identify firmware epochs |
| Explicit clock meaning and unknown fields | Diagnostic decoders and source-operation contracts preserve unknown clock/loss fields and keep capability flags false | **Software representation only.** Radio clock identity, units, event reference instant, firmware epoch and fresh hardware/QPC sampling remain unqualified; retaining an unknown does not resolve it |
| Loss, rejection and exact lengths | Authored contracts test loss/rejection; getter has a 13,312-byte native ceiling against a 2,046-byte managed allocation | **Not met for this route.** Producer size restrictions, actual marshalling, source loss and malformed-event disposition are not qualified; the managed getter is not an approved substitute |
| Bounded initialization, cancellation and teardown | Selected callback registration waits indefinitely; stop waits 1,000 ms then can wait indefinitely | **Not met.** No bounded vendor lifecycle or complete callback rundown proof. Killing a host process would not prove firmware cancellation or drain |
| One real retained event | Fixed test GET returned eight expected bytes; saved traces and replay contain scoped historical diagnostics | **Not met.** Neither fixed bytes, static paths nor authored replay constitute the required complete live timing event |

The decisive evidence is the [6.1.365.1 investigation](../adapters/qmsl-runtime-365.md),
the [QUTS discovery attribution](../adapters/quts-live-gate-and-commonio.md), the
[source-operation contract](source-operation-record.md) and the
[fixed-byte control](device-service-positive-control.md). The current-build
worker/listener trace is complete for its stated slice. Do not repeat it or
generic package enumeration without changed evidence.

## Route rulings and reopening criteria

| Route | Current ruling | Exact prerequisite that reopens review |
|---|---|---|
| Supported Qualcomm/OEM complete-event interface | **Primary Windows path, blocked** | Obtain an accessible, matching interface/package and its ABI, exact device binding, original-event schema, source ownership, initialization/state effects, lengths, loss and bounded close contract. Demonstrate the target-to-interface association before record access |
| Instrumented Windows producer | **Primary Windows path, blocked** | Obtain actual driver source or a supported extension/callback at the valid producer boundary, with a reviewable build/sign/deploy/rollback path and controlled physical target. WDK availability or an unrelated companion driver is insufficient |
| QMSL V2 callback through QUTS or user transport | **No-go now** | Supply a demonstrated live Wi-Fi endpoint/transport tied to the exact producer, then qualify vendor loading/API compatibility, original-byte extent, upstream validity, live/playback attribution and bounded startup/teardown. A new runtime alone does not meet these conditions |
| Existing firmware diagnostic or QDSS return | **Conditional candidate, no-go now** | Establish that matching-version original diagnostic bytes reach an owned application response before formatting, with an actual source/schema connection, length and loss contract. Catalog entry 25950 is not a qualified DIAG selector |
| Existing ETW/WPP or packet capture | **No complete-event route established** | Identify an actual emitting/indication site that retains the necessary original event and identity fields, then demonstrate owned return and completeness. Existing reduced text or host packet timestamps do not close this gate |
| Documented Windows cross timestamp | **Separate conditional sampling route** | A changed exact build or known-capable matched control must produce a valid supported hardware/QPC result with documented semantics and bounded behavior. This would qualify its own sampling lane, not automatically export packet or firmware events |
| Dedicated Linux mt76/ath12k backend | **Conditional alternate; not selected** | Confirm a compatible physical adapter, host/OS and firmware, and explicitly select this additional backend project. Pin/review relevant current source (including the previously identified mt76 delta), supply a buildable bounded producer copy and run a controlled physical qualification. Source availability alone is insufficient |
| Nested IHV controls, ART2 factory-test or packet-log activation | **Deferred** | Explicitly reopen this scope and provide an operation-specific contract resolving state effects, validity, lifetime, loss and exact selector/framing. Existing one-byte status, fixed control bytes or a factory-test mailbox do not establish a timing operation |

For Windows producer instrumentation, the selected copy point remains before WMI
header removal/normalization at `0x168d7c` in the pinned driver. This is a static
integration location, not permission or a method to access live kernel memory.
The [source lifetime](../tsf/hif-receive-buffer-producer.md) and
[receive shutdown](../tsf/receive-shutdown-contract.md) findings still constrain
any implementation supplied by the driver owner.

## Work enabled and work still gated

S4 producer implementation and S5 live acquisition remain blocked on the
external access prerequisite above. When a route reopens, its operation dossier
must define initialization, every state effect, ABI and selector namespace,
producer spans, owned return, loss visibility, deadlines/cancel/close and cleanup
failure behavior. A reviewed finite experiment and its actual result are then
required; reopening a route does not itself pass G1a or G1b.

The coordinator reports that S3 diagnostic replay is implemented and reviewed,
with five profiles and 15 passing focused tests. S8 passed its
12-run local host profile (300,000 record calls, fixed per-reader/pooled p99 and
invariant/workload/cleanup checks); this is not a consumer SLA or clock-accuracy
claim. Its verifier's process/provenance rejection gaps were corrected and the
unchanged original evidence still passed; all four calls above 1 ms remain
recorded. The downstream suite passed 64 tests. S9's nine-file local patch was preserved, hash-verified and validated
against its pinned base without publication. These independent results do not
enable a live radio provider, hardware-to-QPC conversion, node synchronization,
UTC accuracy or system discipline. See the [current ledger](../overview/gap-closure-ledger.md).

The prior private acquisition campaign remains quarantined. Deferred IHV work
stays deferred. Reset, suspend and roam remain preparation only. A new route
cannot retroactively resolve old unmatched reports or prove their drain.

## Validation and rollback

This decision and status refresh require relative-link/navigation tests,
knowledge-index tests and regeneration, diagram consistency and whitespace
checks. No hardware test is appropriate while these route prerequisites are
unmet. Reverting the documentation/index changes restores the earlier handoff;
no device, vendor package or runtime state changed.

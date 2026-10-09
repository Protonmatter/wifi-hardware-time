# Hypotheses, rejected shortcuts and lessons

This ledger focuses on interpretations that changed the research direction. “Supported” always names its scope; “rejected” refers to the tested model or inspected route, not every possible Wi-Fi implementation. The [detailed correction ledger](../knowledge/assumptions-and-corrections.md) retains the lower-level cases and evidence links.

[Guide](README.md) · [Timeline](timeline.md) · [Results](results-and-validation.md) · [Next steps](next-steps.md)

## Hypotheses that held within their tested scope

| Hypothesis | Evidence and result | Boundary that still matters |
|---|---|---|
| The exact Qualcomm build exposes useful diagnostic TSF observations | Repeated captures, the 138-request original campaign, counted bound runs and 139-request persistent smoke | Diagnostic visibility is not full event identity or independently known capture time; [acquisition](../acquisition/README.md) |
| Retaining a process/device session can support repeated pending-to-success requests | One persistent session handled 139 requests and closed normally | One idle smoke; report wait remained; failure paths and persistent long/load runs remain open; [smoke](../acquisition/persistent-tsf-smoke-2026-10-08.md) |
| Exact host-window constraints can produce useful conditional station-TSF intervals | Feasible affine and rate-envelope results on screened idle/load/smoke inputs | Assumptions remain explicit; a systematic physical bias can pass internal consistency; [mathematics](../clock-models/tsf-mathematics.md) |
| Delaying finalization improves event-time information | All 7,492 tested one-second grid points across the two hours and smoke settled below 1 ms in half-width under current replay policy | Later samples are required; this is neither every possible event nor independent physical accuracy; [results](results-and-validation.md) |
| Software ownership/rejection work is useful before a live source exists | Owned synthetic records, broker races, strict decoders and lifecycle tests established application contracts | A synthetic source cannot qualify the firmware producer; [broker](../evidence/raw-event-response-broker.md) |
| Vendor software contains actual copy paths worth tracing | QUTS byte-array allocation and native receive copies; current QMSL original-byte callback path | Wi-Fi binding, framing, source loss and bounded teardown remain separate; [vendor findings](../adapters/qualcomm-archive-transport-findings.md) |

## Hypotheses contradicted by tests or exact-path inspection

| Earlier hypothesis | What challenged it | Corrected conclusion / next decision |
|---|---|---|
| A successful IOCTL returns or fences a fresh timing tuple | Counters arrived asynchronously; the inspected send path can succeed with accepted work queued | Completion and capture are distinct; [action-4 contract](../tsf/action4-completion-and-report-contract.md) |
| The next report belongs to our request | Unmatched groups quarantined a repeat; scans produced extra report groups without private commands | Require association evidence and account for foreign reports; [scan results](../acquisition/scan-tsf-results-2026-10-03.md) |
| A short request call means a promptly available timestamp | Historical reader delays were about 1.6–2 seconds | Use recorded availability and elapsed coverage; [causal replay](../clock-models/causal-provider-replay.md) |
| The SoC counter can directly stand in for the QPC domain | Fixed nominal-rate compatibility failed in all three retained corrected analyses | No shared-oscillator or direct-domain claim; [corrected comparisons](../overview/postmerge-corrections-2026-10-08.json) |
| Freshness screening and a tight affine fit prove the physical window | A synthetic capture 5 ms before every window remained accepted; bounded-rate variation can leave the affine interval | Conditional bounds only; keep the weaker rate model separately; [campaign assumptions](../acquisition/tsf-host-bound-results.md#assumptions-behind-the-bound) |
| Stable cursor plus two equal copies proves a safe ring snapshot | Publication order and two finite-model schedules yielded counterexamples | Need writer/publication/lifetime guarantees; [ring investigation](../memory-ring/timing-boundary-investigation-2026-10-03.md) |
| Copying the wrapper preserves the original event | Temporary wrappers contain pointers whose pointees are reused or freed | Copy the actual bytes while valid; [management lifetime](../adapters/qualcomm-management-timing-producer.md) |
| A raw record is hidden behind the selected ETW numeric text | All 88 inspected selected payloads ended at one NUL without extended items | Rejected for those records only; [byte audit](../tsf/saved-trace-byte-audit.md) |
| A persistent worker automatically achieves one-second sampling | Requested one-second slots achieved median 2.005 s and maximum 4.009 s gaps | Measure cadence; research report lifecycle before decoupling; [smoke](../acquisition/persistent-tsf-smoke-2026-10-08.md) |
| An adjacent-pair retrospective maximum bounds every first-available settlement | Delayed/reordered availability and overlapping windows require different bracket selection | Report actual settled-grid maximum separately; [post-merge policy](../overview/postmerge-corrections-2026-10-08.md) |

## Interpretations that were simply off target

These were errors of meaning or unsupported claims, rather than failed hardware experiments. They should not be carried forward as plausible current explanations.

- **QMSL `FTM_*` means IEEE Fine Timing Measurement.** That prefix is factory test mode in this API family. A specific ranging method needs its own contract. [Vendor corrections](../knowledge/assumptions-and-corrections.md#vendor-packages-and-application-returns).
- **`ullTimestamp` is the local receive counter; `ullHostTimestamp` is a hardware receive timestamp.** The former is the peer's beacon/probe timestamp; the latter follows Windows host/cache timing. [BSS serialization](../adapters/qualcomm-bss-serialization.md), [host-time trace](../adapters/windows-bss-host-time.md).
- **Nanosecond pcapng formatting supplies radio timestamp accuracy.** The inspected live path offered host timestamps and Ethernet packets. [Capture assessment](../acquisition/packet-capture-and-elevation.md).
- **A fixed-pattern response proves the timing producer.** Eight returned test bytes validate one transport operation, not another selector or firmware event. [Positive control](../evidence/device-service-positive-control.md).
- **A named API, import library, catalogue message or matching-sized structure supplies the runtime implementation and schema.** Those are distinct evidence layers; normalization can pad missing bytes and identifier namespaces differ. [QMSL queue](../adapters/qmsl-diagnostic-queue.md), [TSF report contract](../tsf/action4-completion-and-report-contract.md).
- **The median-derived 740-us value was a worst-case guarantee, or unrecorded synthetic counts proved coverage.** Those claims were withdrawn. Typical timing cannot establish a maximum and missing execution evidence cannot establish a test result. [Roadmap correction](../overview/persistent-tsf-next-steps.md#6-change-mathematics-only-through-a-separately-verified-contract).
- **“Every event” or “99% coverage” can be quoted without its event grid and availability boundary.** The first is a finite settled-grid result; the high coverage used an earlier boundary than real reader arrival. Current coverage also includes the integer-estimate rounding allowance. [Version comparison](results-and-validation.md#why-older-numbers-differ).

## Assumptions still open, rather than proven wrong

| Assumption | Present evidence | What would decide it |
|---|---|---|
| Each action-4 TSF capture falls inside its stated host window | Good internal consistency and screened request/report association; constant bias remains invisible | Independently justified capture semantics or a qualified cross timestamp |
| TSF stays within the declared ±200-ppm rate prior and one epoch | No continuity break in retained accepted data; the prior is an assumption | Independent rate/phase evidence under the claimed operating conditions |
| Station TSF matches the intended AP/link clock closely enough | Zero violations in coarse cache checks | Independent station/AP offset and continuity measurement with uncertainty |
| Complete live firmware bytes can be exported through a supported route | Static producers, copies and candidate returns | Attributable real owned record, schema, loss and lifecycle qualification |
| Cancellation/stop establishes firmware drain | Normal host cleanup and offline failure tests | A bounded source/driver contract and separately authorized real failure evidence |
| Shared AP implies sub-ms cross-device synchronization | Protocol motivation only | Combined station/AP and capture/conversion error budget measured on controlled peers |

802.1AS, AirPlay/PTP-like timing and future beacon prediction are separate possible protocol/reference investigations. None is evidence that this Qualcomm route already implements a shared time service. They are not a reason to silently change the selected platform or treat cached beacon prediction as a receive-time measurement.

## Practical research rules earned by these results

Preserve failed attempts and original outputs; never repair a result by relabelling its deadline after collection. Rehash exact inputs when builds change. Keep captured, logged, received and admitted time distinct. State the denominator and observation interval. Use `unknown` where attribution or loss is unobservable. Retain raw/provisional results and append a versioned settlement. Separate software review and CI from live and physical qualification. Each of these rules has a concrete failure or correction above; the next experiments should test the unresolved assumptions directly.

# AP-side reference design for a Windows QPC timing claim

The proposed reference must measure AP TSF at a Windows QPC event independently
of the candidate Wi-Fi counter fit. AP instrumentation alone cannot provide
that result. This design therefore requires both an AP-to-reference link and
an independently qualified reference-to-QPC link. Neither is available as a
qualified capability in the retained evidence.

Design ID: `WHT-G1-REF-1`, under [package revision 1](README.md). All hardware,
physical access, firmware support, calibration and numeric allocations below
are requirements or proposals, not observed capabilities. There are no setup,
transmit, capture, driver-loading or clock-control commands in this document.

## Clock domains and required interfaces

| Symbol / interface | Meaning and record | Evidence needed before use |
|---|---|---|
| Q | Selected Windows host QPC and its frequency/boot identity | QPC metadata and immutable host scope; do not substitute FILETIME or Linux system time |
| C / I-CQ | Candidate Wi-Fi counter and its fresh QPC relation | OEM Q04-Q08 contract and attributed raw capture; local TSF identity and relation to AP are separate facts |
| A / I-CA | Selected AP/link TSF and candidate-to-AP relation | AP/link identity, firmware epoch, actual timestamp point, synchronization/offset behavior and bound; nominal clock rate is insufficient |
| R / I-AR | Independent reference counter and AP-TSF-to-reference measurement | Common event captured in A and R, explicit edge/placement, bounded delay and units, calibration and age/rate limits |
| H / I-HR | Independent host-side hardware counter with a reference event input | Capture of the same reference event in H and R; device/driver contract and bounded physical delay, with independent record attribution |
| I-HQ | H-to-Windows-QPC relationship | Supported fresh hardware/QPC capture and stated error; this is an additional unqualified prerequisite, not an assumed Ethernet or GPIO capability |

The candidate and reference paths are:

```text
Candidate: Q <-> C <-> A  => candidate AP-TSF estimate at Q
Reference: Q <-> H <-> R <-> A  => independently measured AP TSF at Q
```

The reference must not use C's fitted offset/rate, the candidate estimate or its
residuals as calibration input. R need not be UTC: the selected claim is AP TSF,
not UTC. R must have a documented independent uncertainty and stable identity.
Sharing Q as the event coordinate is necessary; assuming independent errors or
cancelling common errors without a derivation is not permitted.

## Preferred reference mechanism: a common physical event

A reviewable hardware pulse/edge source would feed a qualified AP TSF latch, R
and H. Each endpoint records the same numbered event before transport buffering.
Per-branch cable, fanout, threshold and edge-placement delays need individual
calibration and uncertainty. Record which physical edge is used; an interrupt
handler's host timestamp is not a hardware latch unless its delay is bounded.

This design is conditional on accessible, supported AP/host capture interfaces.
No laptop timing pin, AP TSF latch or Windows external-timestamp API is assumed.
Linux [PHC infrastructure](https://docs.kernel.org/driver-api/ptp.html) describes
external-event features on capable devices, but that does not establish the
selected AP, H or Windows interface. If any physical edge or bridge is absent,
the reference design is blocked; installing a collector does not complete it.

For every I-AR, I-HR and I-HQ record, retain raw values, units/widths, clock and
firmware/boot epochs, original source span, sequence identity, status/validity,
loss counters, acquisition time and delivery/availability time. Cross-endpoint
matching must survive duplicate, missing, wrapped and out-of-order records.
One shared sequence name in independently generated software logs is insufficient.

Use bracketed reads only when the contract proves where the actual latch lies
within those brackets. For a direct H/Q capture, Microsoft's
[interface structure](https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/ns-iphlpapi-interface_hardware_crosstimestamp)
identifies the driver-provided fields. It does not prove a particular device's
counter identity, support or error. Equal reported host endpoints still need
the paired-capture error bound.

## RF alternative when no AP latch is accessible

A separately instrumented receiver can relate an actual AP frame event to R,
provided the AP's TSF timestamp insertion and RF event point are known and bounded.
Record the exact frame/exchange ID, retry, link, PHY, timestamp-field semantics,
AP firmware epoch, receiver event point and propagation/correction uncertainty.
If offset and propagation are inseparable, a calibrated two-way exchange or a
common physical reference is required; RTT alone does not solve that ambiguity.

[Radiotap TSFT](https://radiotap.org/fields/TSFT.html) describes a receive-side MAC
event. It does not identify the AP's TX instant or pair a remote receiver with
Windows QPC. A host PCAP timestamp, cached BSS pair, or software-inserted beacon
timestamp is not an adequate substitute. The selected AP/receiver implementation
must be pinned and reviewed; see the
[openwifi and other source caveats](../replacement-timestamp-acquisition.md#ap-side-acquisition-and-alternative-hardware).
I-HQ remains necessary for this RF alternative. Any unavailable RF placement,
propagation/asymmetry bound or reference-to-QPC bridge blocks independent validation.

## Error-budget proposal and reference independence

The following ceilings are a proposed design allocation for the unchanged
10 us target. They are not measurements, a qualified error budget, or new
evaluator defaults. Actual evidence values are currently unknown. Never copy
these ceilings into an evidence JSON as if measured.

| Existing Gate 2 term | Proposed ceiling, us | Must include |
|---|---:|---|
| `event_placement_us` | 2 | Candidate read/latch placement and quantization, plus C-to-A synchronization/offset transfer and reference-point correction |
| `pairing_us` | 2 | Complete C-to-Q pairing error, including bracket half-width and any additional capture error |
| `rate_error_times_age_us` | 1 | Candidate propagation between the actual capture window and event Q_i, with a justified rate bound, hidden-age allowance and expiry; settled backward propagation uses event-to-capture distance, not capture-to-delivery delay |
| `asymmetry_us` | 1 | Uncovered directional RF/path effects in the candidate exchange; zero only with a justified non-applicability argument |
| `epoch_changes_us` | 0, conditional | Fail closed on reset, roam, clock-domain/link or unknown continuity; no timestamp may span an unresolved transition |
| `reference_us` | 2 | Combined I-AR, I-HR, I-HQ measurement/calibration, quantization, rate/age/interpolation and attribution uncertainty of the independent reference |

Allocated total: 8 us, leaving 2 us unallocated margin. Each subterm belongs in
exactly one line, with a derivation and source; do not allocate 2 us separately
to each reference interface. Use a conservative sum of compatible upper bounds.
Do not combine statistical spreads as deterministic limits or use root-sum-square
without a justified probabilistic claim. If the AP transfer is inseparable from
an existing term, explain the combined bound without omitting or double counting it.

The reference path must establish its own age and rate limits. A small fitted
residual between A and R, or between H and Q, is not that bound. Demonstrate
calibration provenance, capture placement, counter semantics and independent
checks; do not tune reference calibration using the candidate validation residuals.

At a hypothetical 200 ppm rate bound, the proposed candidate age allocation of
1 us allows at most 5 ms event-to-capture distance before other accounting. For
immediate estimates, delay before Q_i consumes that age allowance. For settlement,
bound each contributing observation at Q_i using its capture window and a valid
forward/backward propagation rule; a fresh sample delivered quickly after a much
later capture is not necessarily close to the earlier event. Delivery/publication
delay is also checked against the return deadline, separately from drift growth.
This calculation
does not qualify that prior physically, mandate a polling rate, or establish that
the vendor can acquire at that rate. A justified capture/rate/expiry contract is
still required. If the design cannot fit these allocations, return it for review;
do not silently narrow the existing prior or relax the target.

## Comparison record and failure handling

At each declared QPC event Q_i, retain the candidate estimate A_hat(Q_i), its
conditional interval, model/source IDs, actual source age, publication mode,
evidence cutoff and consumer-visible return time. Declare immediate or settled
publication before acquisition. Immediate output may use only records whose
admission/availability time is at or before Q_i. Settled output may use later
records only if admitted by its recorded cutoff, and must be returned by its
predeclared finite deadline; retain the initial provisional/unavailable result.
Reference interpolation after Q_i cannot extend either candidate cutoff.
Separately derive A_ref(Q_i) and U_ref(Q_i) only from the reference chain.
Report signed residual A_hat(Q_i) - A_ref(Q_i), its reference uncertainty and
condition/session. A reference built with later observations must be labeled
offline interpolation; it must not become a claim of online availability.
Freeze model structure, admission/expiry rules, tuning choices and the holdout
protocol before acquisition. If a static learned fit is proposed, freeze its
coefficients after the declared training phase and before holdout evaluation.
If adaptive capture-driven updates are proposed, freeze their algorithm and
record every update's sources and availability time; only eligible observations
at the declared cutoff may update that estimate. Independent reference values,
validation residuals and future candidate records must not leak into candidate
training/tuning or an earlier estimate. A retrospective fit can be reported as
offline analysis only, separately from immediate or deadline-bounded settlement.
This preserves the existing [availability and settlement distinctions](../settled-timestamps.md).

Reject or mark unavailable any comparison with stale data, missing event matches,
unbounded path delay, unaccounted loss, mixed epochs, unknown validity or reference
uncertainty. Preserve it in the denominator and reason ledger. Do not drop load
tails, subtract a fitted bias after seeing validation results, or compare the
candidate to a reference inferred from that same candidate fit.

Current result: all hardware-dependent interfaces above are proposed or
unqualified. An offline design review can establish completeness of the dossier;
only separately authorized acquisition and independent evidence can establish
their actual operation. See [acceptance criteria](acceptance-criteria.md) before
any future operation is proposed.

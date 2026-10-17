# Microsecond-class feasibility: gated verdict

Question: can this TSF stack provide accurate microsecond-class time?

Answer: no from the current action-4 path, and no candidate replacement path
currently qualifies. The evaluator in
`research/clock_models/microsecond_feasibility.py` (schema
`wht/microsecond-feasibility-v1`) encodes the gates below so the verdict is
reproducible offline. Running it with no evidence prints the baseline
evaluation and exits 2:

```text
python -m research.clock_models.microsecond_feasibility
verdict: killed_at_gate1_no_qualified_capture_path
physical_bound_proven: false
```

This page records a software evaluation of documented evidence. No new live
hardware experiment was run for it.

## Gate 0: predeclared claim

Versioned separately from the sub-millisecond acceptance gate so that gate is
never silently tightened. Default profile: target plus or minus 10 us
(allowed targets 1, 10, 50 us), reference `ap_tsf`, conditions idle and load,
scope one adapter, driver and host until separately qualified. Invalid
targets, references, missing conditions, or an unstated scope are rejected.

## Gate 1: capture path with a known read point

A candidate qualifies only with all four properties: known read point,
bounded pairing to QPC, fresh (not cached), and attributable to a specific
event. Documented baseline on the qualified Qualcomm profile:

| Candidate | Qualified | Blocker |
|---|---|---|
| Windows hardware cross-timestamp | No | No demonstrated `INTERFACE_HARDWARE_CROSSTIMESTAMP` path for this TSF source |
| NDIS packet timestamp | No | Capability queries fail on the qualified driver |
| Beacon TSF with local RX | No | Cached pair: unknown cache age, different RX reference point |
| RX descriptor PPDU words (+0x60/+0x68) | No | Units, clock domain and packet identity unknown |
| FTM raw event times | No | Only aggregate RTT exposed; raw t1 to t4 unavailable |

Kill criterion applied: with no qualified path, microsecond class is not
available on this adapter through any tested route. The honest product
remains the conditional sub-millisecond interval (settled median half-width
133-164 us, capture-window floor about 127 us). A future candidate reopens
Gate 1 only with live evidence for all four properties; static analysis
alone cannot supply freshness or pairing bounds.

## Gate 2: independent reference and error budget

Required terms, each bounded in microseconds: event placement, pairing,
rate error times age, asymmetry, epoch changes, and the reference itself.
An unknown term is reported in `unknown_terms` with a null total; it is
never treated as zero. The baseline budget is entirely unknown, so Gate 2
fails independently of Gate 1. No second station, AP-side read, or traceable
external reference exists in the retained qualification yet.

## Gate 3: qualification against the reference

Measured residuals against the named reference must satisfy
max absolute residual at or below the Gate 0 target, with a qualified
capture path and a complete within-target budget. Residuals are reported
separately from model half-widths; a narrow model width can never pass
Gate 3 by itself (covered by a regression test). Even a passing offline
evaluation keeps `physical_bound_proven: false`: it only states that the
supplied evidence is consistent with the profile and is ready for live
confirmation under the stated conditions.

## What reopens this

1. A vendor-supported or otherwise demonstrated capture path with a known
   event point and a bounded, fresh pairing to QPC on this adapter.
2. An independent reference with its own stated uncertainty.
3. Matched idle and load runs against the predeclared profile, preserving
   all attempts, gaps and tails, with residuals published separately from
   model widths.

Until then: conditional sub-millisecond intervals, honestly labeled, are
the deliverable. Do not narrow the 200 ppm prior, the screen window, or
the `J = 25` us jump allowance to make medians look microsecond-class.

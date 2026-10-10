# TSF-to-QPC mathematics and qualification boundaries

The current implementation computes exact conditional intervals relating a station TSF counter to Windows QPC. It preserves event QPC, distinguishes capture time from sample availability, and reports both immediate provisional and later settled results. Interval width is meaningful only when the declared source, capture, rate and continuity assumptions hold; consistency is not independent accuracy calibration.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Current model interpretation. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__clock-models__tsf-mathematics.md).
<!-- /research-history -->

## Quantities and assumptions

| Symbol | Meaning and unit |
|---|---|
| `F` | QPC frequency, ticks per second |
| `Q` | Application event/query time, QPC ticks |
| `T_i` | Reported integer TSF, microseconds |
| `L_i` | QPC immediately before actual action-4 submission |
| `U_i` | Original driver timestamp of the associated report, QPC ticks |
| `C_i` | QPC when terminal I/O completion was observed |
| `D_i` | Reader receipt of the delay record, the last required report-group record |
| `A_i` | Availability boundary used by the arrival-aware replay |

The model assumes a continuous TSF epoch, a valid report association and a true capture inside the stated host window. It assumes an instantaneous TSF rate within plus or minus 200 ppm of nominal. A further station/AP equality assumption is needed to label the estimate as AP-referenced. These are not all proven by the current equipment. No mapping to UTC is provided.

`fractions.Fraction` carries exact arithmetic through the mathematical core. Presentation rounding must not be confused with the exact result. Integer quantization widens the TSF value to `[T_i, T_i + 1]` us and the QPC window to `[L_i, U_i + 1]` ticks.

## Screening is a separate prerequisite

[sample_screen.py](../../research/clock_models/sample_screen.py) first normalizes receipts and classifies a complete recording. Persistent receipts require linked session evidence; legacy receipt meanings remain unchanged. The screen uses command action, record ordering, vdev agreement, delay arithmetic, a 2,000-us acceptance window and a separate 100-ppm freshness check. That screening threshold is not the 200-ppm model prior and is not an empirical calibration of oscillator behavior.

Foreign groups are counted. A foreign report replacing a missing own report inside the same acceptance window is a residual attribution risk; a numerical consistency check cannot establish request identity. Current full-recording screening is offline. Calling `CausalProvider.ingest()` alone does not implement causal online acquisition admission.

## Rate-only envelope

[rate_bound.py](../../research/clock_models/rate_bound.py) defines nominal rate `r = 1,000,000 / F` us/tick, minimum `a = r * (1 - 200/1,000,000)` and maximum `b = r * (1 + 200/1,000,000)`.

For a query after the sample window, one sample implies:

```text
lower_i(Q) = T_i     + a * (Q - (U_i + 1))
upper_i(Q) = T_i + 1 + b * (Q - L_i)
```

For settlement queries that can precede or lie inside a window, the implementation switches slopes according to the sign of the time difference:

```text
x_low  = Q - (U_i + 1)
x_high = Q - L_i
lower_i(Q) = T_i     + (a if x_low  >= 0 else b) * x_low
upper_i(Q) = T_i + 1 + (b if x_high >= 0 else a) * x_high
```

These envelopes allow bounded rate variation; they do not assume one constant rate over the whole recording.

## Causal provider: check before update

[causal_provider.py](../../research/clock_models/causal_provider.py) queries only at or after the latest incorporated availability time, which is at least one tick after each sample window. It summarizes the epoch by:

```text
c_low  = max_i(T_i     - a * (U_i + 1))
c_high = min_i(T_i + 1 - b * L_i)
lower(Q) = c_low  + a * Q
upper(Q) = c_high + b * Q
```

Before changing these values, a new sample is tested against the frozen prior model. There must be a feasible capture point in its widened window:

```text
earliest = max(L_i,       (T_i     - c_high) / b)
latest   = min(U_i + 1,   (T_i + 1 - c_low)  / a)
compatible iff earliest <= latest
```

Arrival times must be ordered and successive capture windows must not overlap. Incompatibility latches `invalid` until an explicit epoch reset. No usable sample yields `acquiring`.

The midpoint and half-width are:

```text
midpoint = (lower + upper) / 2
half_width = (upper - lower) / 2
```

Integer estimates round with `floor(midpoint + 1/2)`. The returned conservative uncertainty is `half_width + 1/2` microsecond, covering every midpoint rounding phase. The `tracking` state compares this returned uncertainty against 1,000 us; equality or a larger value is `stale`. The uniform allowance keeps expiry monotone between sample updates. The exact interval and its half-width remain available separately. This corrects the earlier state test on half-width alone, which could report tracking while the integer estimate's uncertainty reached the threshold. Historical replay outputs retain their original convention; the [review reconciliation](../overview/pr-reconciliation-2026-10-08.md) records the revised comparison.

With no new sample, the current half-width grows at `(b-a)/2` per QPC tick: 200 us per host second for the 200-ppm prior. This is model uncertainty growth, not measured physical drift. Actual worst gaps and report age matter; median spacing cannot establish a worst-case guarantee.

## Availability and the denominator

[replay_causal_provider.py](../../research/clock_models/replay_causal_provider.py) currently uses:

```text
A_i = max(D_i, C_i, U_i + 1)
```

`U_i` remains the driver's original timestamp; delivery time does not replace it. This formula represents the documented reader/completion boundary and excludes later queueing, IPC and ingestion latency. An eventual live API must timestamp the boundary it actually exposes and version any changed semantics.

Arrival-aware coverage uses a declared elapsed interval, including acquiring, tracking, stale and invalid states. The smoke replay used first-request QPC through last-request QPC plus the existing five-second listen interval. That produced 302.999421 seconds rather than exactly the configured 300 seconds. Analyses must publish the denominator and not remove identity or delivery delays to inflate coverage.

## Settlement and retrospective bounds

[settle.py](../../research/clock_models/settle.py) preserves the original event `Q`. It first restricts candidates to samples available by the requested time. The earlier sample must have widened capture end `U_i + 1 <= Q`; the later sample must have capture start `L_i > Q`. It chooses the nearest eligible sample on each side. A window straddling the event establishes neither side. Without an eligible earlier sample the result is unbracketed; without an eligible later sample it is pending. Future unavailable samples cannot change a historical result.

The settled interval is the intersection of those two general rate envelopes:

```text
lower_settled = max(lower_earlier(Q), lower_later(Q))
upper_settled = min(upper_earlier(Q), upper_later(Q))
```

An empty intersection is inconsistent. The settled record is derived evidence; it must not overwrite raw QPC or the originally issued provisional result. Settlement adds latency to finalization, not that amount of error to the preserved event time.

The retrospective rate-only checker evaluates every covered consecutive-pair interval. It checks piecewise-linear endpoints, slope-change points and crossings to find the exact maximum half-width between sampled event-grid points. Its result is limited to covered intervals, not startup, arbitrary future times or an unbounded holdover. Capture windows overlapping an event, or out-of-order availability, can require nonadjacent bracket samples. Settlement now intersects an overlapping sample only when it was already available by the reported settlement cutoff; it never supplies a bracket side. The retrospective consecutive-pair maximum remains distinct from the actual settled-grid maximum and does not bound every first-available result.

## Optional affine polygon: stronger assumption

[bracket_bound.py](../../research/clock_models/bracket_bound.py) assumes one constant rate and offset in a selected span. With recentered values `y_i`, lower window `l_i`, widened upper window `u_i`, rate `r` and offset `c`, it intersects:

```text
a <= r <= b
y_i - r*u_i <= c <= y_i + 1 - r*l_i
```

The current implementation enumerates candidate boundary intersections using exact fractions, retains feasible vertices, and takes prediction extrema over them. Settlement's optional affine estimate uses samples available by the returned `settled_at_qpc`, inside the surrounding 60-second span, with at least three samples and observations on both sides. A later query cannot use later evidence while reporting an earlier estimation time. Replay reports the affine estimate count and share separately from all settled events. The separate retrospective sliding-span analysis has its own 60-second windows and 10-second step.

This narrower constant-rate result is labeled as a stronger-assumption estimate. It does not replace the rate-only result. Exact polygon clipping is a proposed optimization, not an implemented change; equivalence must be proven against this reference before replacement. Bounded-wander estimates require an explicit, independently qualified wander parameter.

## Version 3 policies

These policies are opt-in. Every historical default and published result is unchanged.

**Phase-jump allowance (`wht/causal-provider-v2`, `wht/settlement-v3`).** In an infrastructure network the station rewrites its TSF to the access point's beacon value, so the TSF is not a smooth rate-bounded trajectory at microsecond scale. The v3 envelope assumes only that over any interval the TSF advance lies within the rate prior times the elapsed QPC time, widened by `J` microseconds on each side:

    lower_i(Q) = T_i     - J + (a or b) * (Q - (U_i + 1))
    upper_i(Q) = T_i + 1 + J + (b or a) * (Q - L_i)

The default `J = 25` us is six 102.4 ms beacon periods at 40 ppm relative drift, rounded up. It is a declared prior, not a measurement, and adds `J` to every half-width.

**Nearby-sample settlement (`wht/settlement-v3`).** The bracket rule and settle time are unchanged. The result additionally intersects the envelope of every sample available by the reported cutoff whose window lies within 10 seconds of the event. A farther sample with a narrow window can be tighter than the nearest one with a wide window.

**Learned-rate model (`wht/wander-model-v1`).** A stronger, labeled assumption: across the trailing 60 seconds and the holdover to the query, the TSF rate stays within the exact constant-rate interval of the trailing samples widened by `wander_ppm` (the replay harness uses 2). A common offset exists for rate `r` exactly when every ordered sample pair satisfies `r * (L_j - U_i - 1) <= T_j - T_i + 1 + 2J`. The model interval is intersected with the guaranteed interval and never replaces it. Each new sample is first checked against the model (out of sample); any holdout violation is evidence that the assumption failed. The replay applies the same continuity invalidations and historical-capture skips as the causal replay (a diagnostic precedes equal-availability samples).

**Explicit ETW flush.** Real-time trace delivery waits for the one-second flush timer. With `--etw-flush` the persistent campaign calls `ControlTraceW(EVENT_TRACE_CONTROL_FLUSH)` after each completion, so a sample becomes available in milliseconds. Availability semantics (`A_i = max(D_i, C_i, U_i + 1)`) are unchanged; only `D_i` arrives sooner.

None of this narrows the capture window, which sets a floor of about half its width (about 127 us at the median smoke width). Locating the read point inside the window needs an independent reference or a different capture path.

## What the current results mean

<!-- tsf-headlines:smoke -->
**Current retained smoke analysis:** 139 recorded requests, 138 offline-screened samples; **92.862589%** tracking coverage under the conditional integer-estimate uncertainty threshold. **297/297** event-grid points settled, with median/max rate-only half-widths of 280.429/614.883 us and median wait 2.341 s. [Versioned results and source pins](../overview/postmerge-corrections-2026-10-08.json). This is offline-screened replay of the retained capture, not online admission or calibrated AP/UTC accuracy.
<!-- /tsf-headlines:smoke -->

A stable unmodeled capture bias can remain numerically consistent. Multi-device synchronization additionally needs both devices' errors and station/AP relationships in one budget; two individually sub-millisecond estimates do not automatically imply sub-millisecond pairwise alignment. Independent source/reference validation is therefore a separate gate in the [roadmap](../overview/persistent-tsf-next-steps.md).

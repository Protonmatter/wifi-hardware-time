# Causal TSF provider: design contract

This follow-up turns the rate-only TSF bound into tested code and builds a causal provider: given samples as they become available, it returns a TSF interval for any later QPC instant, using only information available by then, and withdraws its sub-millisecond status when that interval becomes too wide. It is offline research code replayed against the two counted runs of the [bound campaign](../acquisition/tsf-host-bound-results.md); application integration in `userspace-clock` is a later step.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__overview__2026-10-08-causal-provider-design.md).
<!-- /research-history -->

**Status:** design approved with five contract tightenings from review, 2026-10-08. Stacked on PR #4 at `64da8f2`.

## Contents

- [Acceptance statement](#acceptance-statement)
- [Assumptions](#assumptions)
- [Contract](#contract)
- [Modules and tests](#modules-and-tests)
- [Out of scope](#out-of-scope)

## Acceptance statement

Under the declared capture, rate and continuity assumptions, the provider returns an interval using only information available at the specified input boundary, and withdraws its sub-millisecond status when that interval becomes too wide.

## Assumptions

- **Causal capture:** each reported TSF was captured inside its window `[lower_qpc, upper_qpc]`.
- **Bounded rate:** at every instant the TSF advances at a rate within 200 ppm of nominal relative to QPC, with no unmodelled phase steps. No constant-rate model is assumed.
- **Continuity:** samples within one epoch come from one continuous TSF; an established continuity or identity failure ends the epoch.
- **Quantization:** TSF is an integer microsecond counter and QPC an integer tick counter, so each window is widened by one tick and each value by one microsecond.

## Contract

**1. Capture time and availability are separate.** Each input carries its capture window, its TSF value and a separate `available_qpc`. In the arrival-aware mode, availability is no earlier than the reader-thread receipt (`received_qpc`) of the last record the sample needs (its `delay` record) and no earlier than its request's completion QPC (the earliest the receipt could exist). This is availability at the recorded reader boundary; queueing, validation and provider ingestion latency remain for downstream integration.

**2. No future knowledge from screening.** The provider accepts already-qualified samples and uses each only from its availability time. In this change, samples are qualified by the existing offline screen over the complete recording, so results are labelled **causal clock-model replay conditioned on offline sample screening**. Fully online admission would need an incremental screening policy and tests that delayed or contradictory records cannot change earlier decisions.

**3. Self-consistency is a pre-update feasibility test.** Before a new sample is incorporated, the model from earlier available samples is frozen, and the test asks whether the sample's quantized TSF interval can occur at some instant inside its capture window under that model and the rate limits. The result is recorded first; only a compatible sample then updates the model. An incompatible sample falsifies the combined assumptions and input history without identifying which assumption failed; a compatible one supports consistency without validating capture timing.

**4. States, thresholds and recovery.**

| State | Meaning |
|---|---|
| `acquiring` | No usable sample in the current epoch |
| `tracking` | Conditional uncertainty below 1,000 us |
| `stale` | Conditional uncertainty at or above 1,000 us |
| `invalid` | Incompatible constraints, or an established continuity or identity failure; latched until an explicit reset starts a new epoch |

A missed sample lets uncertainty grow into `stale`; a new compatible sample may restore `tracking`. Each estimate returns the interval endpoints, the exact midpoint and half-width, an integer-microsecond estimate with an uncertainty expanded to cover rounding, the query QPC, the last availability, the epoch, a reason and the conditions. Arithmetic is exact internally. Queries earlier than the latest availability are refused.

Review reconciliation makes the returned uncertainty exactly `half_width + 1/2` microsecond. This uniform conservative rounding allowance, rather than half-width alone, governs both state and the exact expiry used by replay. Historical reports use their recorded implementation; revised results are recorded separately.

**5. Separate result modes and exact coverage.**

- **Reproduction modes:** the retrospective rate-only bound (consecutive samples on both sides of a gap), and the causal bound with availability at the report's ETW timestamp. Both should reproduce the earlier review's figures.
- **Arrival-aware mode:** availability at the recorded reader boundary; it produces its own results and is not required to match.
- **Coverage** is integrated exactly from availability and expiry boundaries over a declared interval: from the first request to the end of the last request's listening interval, so it includes initial acquisition and the tail. It is also reported over the earlier review's interval for comparison.
- **Every output records** input hashes, source revision, rate limit, quantization, screening policy, interval boundaries and all self-consistency results. That includes screened-out samples that carry a report.

## Modules and tests

| Module | Responsibility | Key tests |
|---|---|---|
| `research/clock_models/rate_bound.py` | Rate limits, per-sample envelope, retrospective gap bound | Truth containment for a variable-rate clock within 200 ppm; quantization; exact maximum inside gaps against a dense check |
| `research/clock_models/causal_provider.py` | Epochs, ingestion with pre-update feasibility, states, estimates | Exact stale boundary; recovery on a new sample; latched invalid on an injected incompatible sample that never influences the model; delayed delivery and variable-rate clocks stay consistent; refused queries into the past; rounding coverage |
| `research/clock_models/replay_causal_provider.py` | Three modes over a run folder; exact coverage; metadata | Exact coverage on synthetic gaps; availability from the last required record and request completion |

## Out of scope

- New live collection.
- Online sample admission (see contract item 2).
- Shortening request spacing or the trace flush timer to raise coverage.
- `userspace-clock` integration.

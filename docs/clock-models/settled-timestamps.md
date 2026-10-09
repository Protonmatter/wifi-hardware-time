# Two-phase TSF timestamps: current settlement policy

Record an event's raw QPC and provisional result immediately, then append a derived settled interval when sufficient already-available evidence brackets the event. Current retained replay settled all 7,492 points on three declared one-second grids below 1 ms in conditional rate-only half-width. This finite, offline-screened result does not establish a universal event guarantee, online admission or calibrated AP/UTC accuracy.

**Updated interpretation, 2026-10-09:** [Research account](../research-history/README.md) · [Result versions](../research-history/results-and-validation.md) · [Previous page](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__clock-models__settled-timestamps.md). Original component JSON remains in [the historical settlement directory](settled-timestamps-2026-10-08/).

## How current settlement works

1. Preserve the raw event QPC, clock/epoch identity and immutable provisional result. Do not overwrite the original timestamp when later information arrives.
2. Find a complete bracket using samples available by the settlement cutoff. A true-before sample has widened capture end `upper + 1 <= event`; a true-after sample has `lower > event`. A capture overlapping the event supplies neither side.
3. Under `wht/settlement-v2`, already-available overlapping envelopes can narrow an existing complete bracket. Record the contributing sequences. Later queries must not retroactively use evidence unavailable at the returned settlement time.
4. Return explicit `settled`, `pending`, `unbracketed` or `inconsistent` outcomes under the settlement contract. Causal-provider stale/invalid state and acquisition epoch changes remain distinct inputs; absence of a bracket is not a fabricated result.
5. Report the conditional rate-only interval. Any separately provided affine estimate adds constant rate over the surrounding span and uses only evidence available by the settlement cutoff. Disclose its actual count/subset.

The implementation is [settle.py](../../research/clock_models/settle.py); [mathematics](tsf-mathematics.md) and [post-merge corrections](../overview/postmerge-corrections-2026-10-08.md) define quantization, availability and policy. Samples here were admitted by a full-recording offline screen. This research implementation is not itself the maintained live consumer boundary.

## Corrected retained results

Source: corrected fields of [postmerge-corrections-2026-10-08.json](../overview/postmerge-corrections-2026-10-08.json), source commit `0f41db0175e3601e899c51143b46bb8b3df02135`.

| Measure | Idle hour | Loaded hour | Persistent smoke |
|---|---:|---:|---:|
| Settled / event-grid points | 3,598 / 3,598 | 3,597 / 3,597 | 297 / 297 |
| Conditional rate-only half-width, median / max, us | 308.456 / 894.669 | 324.908 / 766.954 | 280.429 / 614.883 |
| Wait until settlement, median / max, seconds | 3.112 / 8.029 | 3.347 / 7.823 | 2.341 / 4.989 |
| Affine estimate available / grid points | 3,595 / 3,598 | 3,595 / 3,597 | 295 / 297 |

These are conditional interval half-widths at the sampled event grid, not measured physical errors. Integer-estimate uncertainty carries an additional conservative 0.5-us allowance. Retrospective consecutive-pair maxima are a different statistic and do not cap every nonadjacent first-available settlement. For example, the loaded-hour retrospective figure is 785.584 us, while its actual settled-grid maximum here is 766.954 us.

The [first review](../overview/pr-reconciliation-2026-10-08.md) corrected bracket sides and availability semantics. The [subsequent version](../overview/postmerge-corrections-2026-10-08.md) permitted available overlapping envelopes to narrow an already complete bracket. Original inputs and published result files were preserved through both. Read the [version table](../research-history/results-and-validation.md#why-older-numbers-differ) before comparing old quantiles.

## Appropriate use and unresolved limits

This design is useful for research event logs and retrospective correlation where later refinement is acceptable. An immediate decision must use the provisional state and uncertainty, including stale/unavailable outcomes. Settlement waits here end at the recorded reader boundary, not the time a real consumer completed admission and returned an API response.

Capture inside the host windows, the ±200-ppm prior, no unmodelled phase steps and continuous source identity remain assumptions. AP-referenced use additionally needs an independently bounded station/AP relationship. Shared-AP cross-device use requires a combined error budget. UTC needs its own reference chain. A tight interval or zero internal inconsistencies cannot establish those links.

Persistent operation did not automatically remove delivery wait: the smoke achieved median 2.005-second gaps. Improved scheduling/coverage requires a supported association/lifecycle contract and new evidence; the old speculation that a one-second persistent sampler would automatically solve this is not a measured result.

## Reproduce and continue

With authorized original private inputs, the read-only command is:

```powershell
python research/clock_models/replay_causal_provider.py <PRIVATE_RUN_DIRECTORY> --mode settle
```

Pin code and input hashes; use the matching historical revision when reproducing an old output. Public tests establish software behavior, not recreation of unavailable private captures. Next work is [longer persistent qualification, online admission, live failure evidence and independent timing validation](../research-history/next-steps.md).

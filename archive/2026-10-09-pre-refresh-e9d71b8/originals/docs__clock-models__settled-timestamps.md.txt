# Two-phase TSF timestamps: settled results

> Historical report: the original source pins and JSON outputs are preserved. See the [2026-10-08 review reconciliation](../overview/pr-reconciliation-2026-10-08.md) for corrected threshold, settlement, and diagnostic results on the same retained captures.

Waiting a few seconds turns the live clock's intermittent sub-millisecond status into a sub-millisecond bound for every event. An event's QPC is recorded at once; when the next sample captured after it has arrived, the event is settled from the samples on both sides. Across the two counted hour-long runs, every one of 7,195 events (one per second) settled below 1 ms, typically about 310 to 325 us, after a median wait of about 3 seconds. These are bounds computed from measured traces under stated assumptions, conditioned on offline sample screening.

## Contents

- [How settling works](#how-settling-works)
- [Results](#results)
- [How to use it](#how-to-use-it)
- [What this shows and what it does not](#what-this-shows-and-what-it-does-not)
- [Reproduce](#reproduce)

**Terms:** the **conditional rate-only bound** is the rate-only bound (TSF rate within 200 ppm of nominal at every instant). The **best estimate** additionally assumes one constant rate within the surrounding 60 seconds. See the [causal provider replay](causal-provider-replay.md), the [design contract](../overview/2026-10-08-causal-provider-design.md) and the [glossary](../glossary.md).

## How settling works

1. **Stamp:** record the event's QPC. Until it settles, the [causal provider](../../research/clock_models/causal_provider.py) gives a provisional interval and state.
2. **Settle** ([`settle.py`](../../research/clock_models/settle.py)): once the first sample captured after the event has arrived, intersect the bounds implied by that sample and the last sample before the event. Only samples available at settle time are used.
3. **States:**
   - `settled`: the conditional rate-only interval is available;
   - `pending`: the bracketing sample has not arrived;
   - `unbracketed`: no earlier sample exists in the epoch;
   - `inconsistent`: the two sides cannot both hold under the assumptions.
4. **Best estimate:** the [window polygon](../../research/clock_models/bracket_bound.py) over samples within ±30 s that are available at settle time, reported separately and labelled with its stronger assumption.

Sample availability is the recorded arrival time at the controller (the reader receipt of the sample's last record, never before its request completed), as in the arrival-aware replay.

## Results

Events were placed every second from the first capture to the last, each settled at its earliest possible time.

| | Idle (`ac08a44962b0`) | Load (`04ddf1083b85`) |
|---|---:|---:|
| Events / settled | 3,598 / 3,598 | 3,597 / 3,597 |
| Settled below 1,000 us | 100% | 100% |
| Wait until settled: median / p90 / p99 / max (s) | 3.112 / 4.560 / 5.173 / 8.029 | 3.347 / 4.732 / 5.770 / 7.823 |
| **Conditional rate-only half-width: median / p90 / p99 (us)** | **308.5 / 447.4 / 578.7** | **324.9 / 463.1 / 585.3** |
| Retrospective consecutive-pair maximum half-width (us; different from settlement) | 894.669 | 785.584 |
| Best-estimate half-width: median / p90 / p99 / max (us) | 126.6 / 154.0 / 193.8 / 309.7 | 130.2 / 161.7 / 204.3 / 244.0 |

The worst-at-any-instant figure is the exact retrospective maximum over every instant, not only the one-second grid. Pinned outputs with input hashes and source revision `ef8adf0` are in [`settled-timestamps-2026-10-08/`](settled-timestamps-2026-10-08/).

## How to use it

- **Event correlation, logs and measurement records:** use settled timestamps and report the conditional rate-only interval. Every event in these runs settled below 1 ms within about 8 seconds.
- **Cross-device correlation (research hypothesis):** sharing an access point does not establish a qualified common clock. Independently bound each station-to-AP relationship and include both capture/conversion uncertainties in a combined error budget before comparing device events. This implementation supplies no calibrated cross-device capability.
- **Decisions needed immediately:** use the provisional value with its state and uncertainty, and treat `stale` as not sub-millisecond.

## What this shows and what it does not

**Shows:** with today's hardware and acquisition, and under the stated assumptions, every event can receive a sub-millisecond TSF bound a few seconds after it happens.

**Does not show:**

- **Capture timing.** Each TSF is assumed to be captured inside its window.
- **The station-to-AP TSF link.** It is assumed, not measured.
- **Accuracy against UTC.**
- **Online sample admission.** Samples were screened offline over the complete recording.
- **Settle latency inside an application.** It is measured only to the controller's reader boundary.

A persistent sampler at about one-second spacing would shorten the waits and tighten the conditional bound.

## Reproduce

With the private run folders under `artifacts/`:

```powershell
python research/clock_models/replay_causal_provider.py artifacts/BoundCampaign-ac08a44962b0/idle --mode settle
python research/clock_models/replay_causal_provider.py artifacts/BoundCampaign-04ddf1083b85/load --mode settle
```

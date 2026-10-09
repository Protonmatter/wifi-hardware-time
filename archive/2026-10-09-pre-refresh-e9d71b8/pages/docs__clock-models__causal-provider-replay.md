# Causal TSF provider: replay results

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__clock-models__causal-provider-replay.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

> Historical report: the original source pins and JSON outputs are preserved. See the [2026-10-08 review reconciliation](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/pr-reconciliation-2026-10-08.md) for corrected threshold, settlement, and diagnostic results on the same retained captures.

Replaying the two counted hour-long runs through the causal provider confirms the earlier review's figures exactly, and adds the arrival-aware result a live application would face. When each sample is used only from the moment the controller actually received it, the provider kept a sub-millisecond interval for **78.7% of the idle hour and 72.4% of the loaded hour**. The rest was explicitly flagged `stale`. The cause is delivery delay: samples became available a median of about 2 seconds after capture. No sample was inconsistent with its predecessors. These are bounds computed from measured traces under stated assumptions, labelled as a causal clock-model replay conditioned on offline sample screening.

## Contents

- [What was replayed](#what-was-replayed)
- [Results](#results)
- [Why arrival-aware coverage is lower](#why-arrival-aware-coverage-is-lower)
- [Self-consistency](#self-consistency)
- [What this shows and what it does not](#what-this-shows-and-what-it-does-not)
- [Reproduce](#reproduce)

**Terms:** `tracking` means the provider's conditional uncertainty is below 1,000 us; `stale` means it is at or above that. **Availability** is when a sample may first be used. See the [design contract](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/2026-10-08-causal-provider-design.md) and the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## What was replayed

- **Runs:** `BoundCampaign-ac08a44962b0/idle` and `BoundCampaign-04ddf1083b85/load`, the counted runs of the [bound campaign](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/tsf-host-bound-results.md); 1,276 and 1,210 accepted samples.
- **Code:** [`rate_bound.py`](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/rate_bound.py), [`causal_provider.py`](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/causal_provider.py) and [`replay_causal_provider.py`](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/clock_models/replay_causal_provider.py) at commit `9c9dea2`.
- **Assumptions:** causal capture inside each window; a TSF rate within 200 ppm of nominal at every instant with no unmodelled phase steps; continuity within the epoch; integer counters widened by one tick and one microsecond.
- **Screening:** samples were qualified by the existing offline screen over the whole recording, not by an online admission policy.
- **Coverage interval:** from the first request to the end of the last request's listening interval, so it includes initial acquisition and the tail. The earlier review's interval (first to last sample availability) is reported alongside.

## Results

| Mode | Availability | Idle | Load |
|---|---|---:|---:|
| Retrospective rate-only bound, maximum (us) | samples on both sides of each gap | 894.669 | 785.584 |
| Causal, maximum just before the next sample (us) | one tick after the report's ETW timestamp | 1,742.482 | 1,347.739 |
| Causal, coverage over the review's interval | same | 99.440% | 99.223% |
| Causal, coverage over the declared interval | same | 99.423% | 99.206% |
| **Arrival-aware, maximum just before the next sample (us)** | reader receipt of the delay record, and request completion | **1,978.711** | **1,731.643** |
| **Arrival-aware, coverage over the declared interval** | same | **78.690%** | **72.417%** |
| Arrival-aware, stale intervals / longest (s) | same | 841 / 3.30 | 979 / 3.22 |
| Incompatible samples | all modes | 0 | 0 |

The first three rows reproduce the earlier review's values exactly. The arrival-aware rows are new, and were not required to match.

## Why arrival-aware coverage is lower

| | Idle | Load |
|---|---:|---:|
| Availability after capture window, median (s) | 1.956 | 1.978 |
| p95 (s) | 2.069 | 2.068 |
| Maximum (s) | 2.200 | 3.019 |

Under the 200 ppm limit, the half-width grows by about 200 us per second after the last sample (the 400 ppm spread between the slowest and fastest allowed rates). With samples about 3 seconds apart, waiting 2 more seconds for each one to arrive pushes the interval past 1,000 us for part of most gaps. The delay matches the roughly 1.6-second report delivery measured in the earlier [latency audit](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/acquisition/private-acquisition-latency.md), and is consistent with ETW real-time delivery under the session's 1-second flush timer. Shortening request spacing or delivery latency would raise coverage; both need new collection and are out of scope here.

## Self-consistency

Before each sample was incorporated, the frozen model from earlier samples was asked whether that sample's TSF could occur anywhere in its capture window. All 2,486 accepted samples were compatible. The three screened-out late reports (idle sequence 590; load sequences 16 and 106) were checked without being ingested and were also compatible. That is consistent with their being genuine late copies of our reports.

Compatibility supports the assumptions but cannot validate capture timing: a constant capture delay would still pass.

## What this shows and what it does not

**Shows:** given the stated assumptions and this offline screening, a provider using only information available at the recorded reader boundary keeps a conditional sub-millisecond interval for about three-quarters of each hour. It explicitly withdraws that status for the rest.

**Does not show:**

- Online sample admission. Screening ran over the complete recording.
- Delivery latency after the reader thread, inside the controller and an application.
- Capture timing, the station-to-AP TSF link, or accuracy against UTC.
- An uninterrupted sub-millisecond guarantee.

## Reproduce

With the private run folders under `artifacts/`:

```powershell
python research/clock_models/replay_causal_provider.py artifacts/BoundCampaign-ac08a44962b0/idle --mode all
python research/clock_models/replay_causal_provider.py artifacts/BoundCampaign-04ddf1083b85/load --mode all
```

The pinned outputs, with input hashes, source revision and interval boundaries, are in [`causal-provider-replay-2026-10-08/`](https://github.com/Protonmatter/wifi-hardware-time/tree/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/clock-models/causal-provider-replay-2026-10-08).

# Causal TSF provider: current replay interpretation

Arrival-aware replay produces useful conditional station-TSF/QPC intervals and explicitly becomes stale when the uncertainty reaches 1 ms. Corrected tracking coverage is 78.632051% for the retained idle hour, 72.349583% for the loaded hour and 92.862589% for the persistent idle smoke. Samples were screened over complete recordings before causal replay; this is not a demonstrated live admission pipeline or calibrated AP clock.

**Updated interpretation, 2026-10-09:** [Research account](../research-history/README.md) · [Result versions](../research-history/results-and-validation.md) · [Previous page](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__clock-models__causal-provider-replay.md). Original component outputs remain in [the historical replay directory](causal-provider-replay-2026-10-08/).

## Source and boundary

Use the corrected fields in [postmerge-corrections-2026-10-08.json](../overview/postmerge-corrections-2026-10-08.json), with source `0f41db0175e3601e899c51143b46bb8b3df02135`. The [first review comparison](../overview/pr-reconciliation-2026-10-08.json) preserves why original coverage was slightly higher: it did not include the conservative 0.5-us rounding allowance in the returned integer estimate's uncertainty.

The availability boundary is the recorded reader receipt of the last required record, no earlier than request completion and the report boundary. It is separate from the capture window. Queueing, online admission, provider ingestion and application IPC after that boundary still require measurement. The replay interval includes initial acquisition and the declared tail, not just the span between accepted samples.

## Corrected retained results

| Measure | Idle hour | Loaded hour | Persistent smoke |
|---|---:|---:|---:|
| Accepted / requested samples | 1,276 / 1,277 | 1,210 / 1,212 | 138 / 139 |
| Tracking coverage | 78.632051% | 72.349583% | 92.862589% |
| Maximum interval half-width immediately before a subsequent sample, us | 1,978.711 | 1,731.643 | 1,348.809 |
| Same boundary metric for integer-estimate uncertainty, us | 1,979.211 | 1,732.143 | 1,349.309 |

The two maximum rows differ by 0.5 us. They are not whole-run/tail suprema. Tracking uses the integer-estimate uncertainty, with equality at 1,000 us classified stale. Exact rational intervals are preserved until display. All three retained analyses report no continuity break; absence in these recordings does not prove that future epochs cannot change.

## Why delivery changes the result

The original hour-run replay measured median availability delays of 1.956/1.978 seconds after the capture window. At the assumed 200-ppm rate limit, uncertainty can grow by about 200 us per second. An estimate that looks sub-millisecond at logging time can therefore be stale when the reader can use it. The older 99.440%/99.223% figures used one tick after ETW logging over the review interval; they are not current reader or application availability.

The later persistent smoke retained its report wait and achieved median 2.005-second request gaps. Its higher coverage is a useful short-run result, not a controlled like-for-like performance proof or persistent long-run/load qualification. [Original smoke](../acquisition/persistent-tsf-smoke-2026-10-08.md).

## Current rules and assumptions

- The rate-only model assumes capture within each host window, rate within ±200 ppm at every instant and continuity within the epoch. It does not assume a constant affine rate.
- Before ingesting a sample, the frozen prior model checks feasibility. Consistency can reject incompatible data but cannot detect every systematic capture bias.
- Current arrival-order policy processes availability first, with defined ties and explicit skipped late historical captures. Screening discontinuity invalidates only once the necessary evidence is available.
- `acquiring`, `tracking`, `stale` and `invalid` are explicit states. Invalid remains latched until reset under the contract; a later wide tolerance does not reopen a broken epoch.
- Station-to-AP alignment, full firmware clock/link identity and independent physical/UTC accuracy remain unqualified.

See the [mathematics](tsf-mathematics.md), [design](../overview/2026-10-08-causal-provider-design.md) and [post-merge policies](../overview/postmerge-corrections-2026-10-08.md). The numerical provider consumes accepted samples; it does not establish acquisition provenance by itself.

## Reproduction and next step

With authorized access to the private original run folders, run the existing read-only replay CLI against each selected folder:

```powershell
python research/clock_models/replay_causal_provider.py <PRIVATE_RUN_DIRECTORY> --mode all
```

Record the exact source revision and input hashes. To reproduce an old output, use its original pinned source; a current replay may intentionally implement newer policies. Public-only checks can run the software suite but cannot recreate private measurements from their digests alone.

The next implementation dependency is [causal online admission](../research-history/next-steps.md), alongside longer persistent qualification and separate failure/physical validation. For events that can wait, read [two-phase settlement](settled-timestamps.md).

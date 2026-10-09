# TSF-to-host bound: preview on saved action-4 samples

Applying the new window-bound analysis to six already saved campaign runs gives a proven worst-case TSF error of 143 to 296 microseconds over each run, both idle and under CPU load. Every one of the 18 action-4 windows is below 1 ms on its own. The SoC counter fails the shared-QPC-domain test in every run. This is a preview: the saved runs predate the new attribution screening, so the result is conditional until the live campaign repeats it with that screening in place.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Dated evidence or historical plan. This dated report or plan retains its original evidence and execution scope; later results and publication status are in the research account. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__clock-models__tsf-host-bound-preview.md).
<!-- /research-history -->

## Contents

- [Scope](#scope)
- [Results per run](#results-per-run)
- [Other findings](#other-findings)
- [What this does and does not show](#what-this-does-and-does-not-show)
- [Reproduce](#reproduce)

**Terms:** a **window** is the host QPC interval from just before a private action-4 request to the driver's trace timestamp for the matching report. The **proven half-width** is the worst-case TSF error at any instant in the analyzed span, given that every capture happened inside its window. See the [design](../overview/2026-10-07-tsf-host-bound-design.md) and the [glossary](../glossary.md).

## Scope

- **Evidence:** the six mixed runs of campaign `ecfaed68f20e` (2026-10-02), three idle and three with the campaign's SHA-256 CPU workload. Each run holds three action-4 and eight action-3 observations over about 24 seconds.
- **Method:** [`analyze_bound_run.py legacy`](../../research/clock_models/analyze_bound_run.py), which applies the 100 ppm freshness band, the exact window polygon with a 200 ppm rate prior, and the SoC domain test.
- **No new acquisition**, request, trace or device operation was performed for this preview.

## Results per run

| Run | Bundle | Window widths (us) | Proven half-width at each sample (us) | Worst case over run (us) | TSF-to-QPC rate interval (ppm) | SoC fixed-rate gap (us) |
|---|---|---|---|---:|---|---:|
| idle-mixed-1 | `c470b4f2f8f9` | 397.0, 355.6, 585.9 | 199.0, 178.3, 293.5 | 293.5 | -63.7 to -23.0 | 364.9 |
| idle-mixed-2 | `3c9bf04e2151` | 284.6, 546.3, 213.8 | 142.8, 125.9, 107.4 | 142.8 | -55.1 to -35.2 | 688.0 |
| idle-mixed-3 | `662948be1d41` | 571.7, 238.7, 260.7 | 286.4, 119.9, 130.9 | 286.4 | -65.5 to -31.0 | 566.6 |
| workload-mixed-1 | `2672a4a16208` | 612.1, 254.6, 347.3 | 296.1, 127.8, 174.2 | 296.1 | -66.5 to -27.6 | 492.5 |
| workload-mixed-2 | `33f39f9fe89b` | 259.3, 274.8, 585.3 | 130.2, 137.9, 293.2 | 293.2 | -59.9 to -25.1 | 434.2 |
| workload-mixed-3 | `84796ad0adf9` | 739.5, 240.4, 259.4 | 291.4, 130.2, 120.7 | 291.4 | -66.2 to -32.1 | 603.5 |

- The worst case over a run is reached at the run's first or last instant, as the analysis guarantees for a convex half-width.
- Every run's rate interval overlaps -55 to -35 ppm. That is the combined offset of the access point's clock and the laptop's QPC source, not either crystal's error alone.
- All 18 action-4 samples passed the freshness band; none were rejected.

## Other findings

- **SoC is not in the QPC domain at a fixed 10 ticks per unit.** No single offset fits all three windows in any run; the gap ranges from 364.9 to 688.0 us within about 24 seconds. The SoC shortcut in the design is unlikely to apply, and the window method is the main route.
- **Action-3 TSF values advance with host time.** All 48 action-3 observations passed the same 100 ppm freshness band as action 4, so their TSF values do not behave like a frozen cache. That does not establish when action 3 samples TSF, and the live campaign still uses action 4 only.
- **Scan-triggered reports carry the same vdev as ours** (vdev 0), but lack the `command` record that every one of our requests produces. The [sample screen](../../research/clock_models/sample_screen.py) classifies on that structure; on two saved runs it accepted all three action-4 samples and classified the eight action-3 groups as other activity.

## What this does and does not show

**It shows** that, if each action-4 capture happened inside its host window, the station TSF is bounded to within about 300 us at any instant of these runs, idle or under CPU load.

**It does not show:**

- **Attribution under scans.** Foreign-report classification and own-loss accounting did not run during these captures. The old controller stopped on any unsolicited report instead.
- **Long-run behaviour.** Each run lasted about 24 seconds with three samples. Drift, TSF adjustments and lifecycle effects over an hour are untested.
- **The access point link.** Station TSF equal to access point TSF remains an assumption, with only a coarse check available on this equipment.
- **Accuracy against UTC** or any independent reference.

The live campaign in the [implementation plan](../overview/2026-10-07-tsf-host-bound-plan.md) is designed to close the first two gaps.

## Reproduce

From the repository root, with the saved campaign under `artifacts/`:

```powershell
python research/clock_models/analyze_bound_run.py legacy artifacts/QualcommCampaign-ecfaed68f20e/idle-mixed-1/evidence.json
```

Repeat for each of the six run folders. The command reads only the saved bundle and prints JSON; it writes nothing.

# Clock relationship analysis: tools

These tools compare saved counter observations with host timing and test competing conversion models. They can reveal inconsistent assumptions and prediction limits, but cannot establish the physical sampling instant from a good fit. Treat their output as conditional research evidence, not calibrated uncertainty or an enabled clock conversion.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Tool guide. Use the linked account for goals, result versions, failed assumptions and remaining qualification gates. [Current account](../../docs/research-history/README.md) · [Timeline](../../docs/research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/research__clock_models__README.md).
<!-- /research-history -->

## Files

| File | Role |
|---|---|
| [analyze_bound_run.py](analyze_bound_run.py) | Offline run analysis and predeclared idle/load evaluation using actual source, trace, duration and workload evidence. |
| [sample_screen.py](sample_screen.py) | Full-recording structural/association/freshness screening, rejected/foreign accounting and versioned continuity policy; not a qualified online admission state machine. |
| [bracket_bound.py](bracket_bound.py) | Exact rational affine window constraints; adds a constant-rate assumption within the analyzed span. |
| [rate_bound.py](rate_bound.py) | Exact bounded-rate envelopes and retrospective bounds without the affine constant-rate assumption. |
| [causal_provider.py](causal_provider.py) | Availability-aware numerical provider, pre-update feasibility, exact interval/rounding uncertainty, expiry and explicit states. |
| [replay_causal_provider.py](replay_causal_provider.py) | Read-only retained-run replay in causal, arrival-aware, retrospective and settlement modes; preserves declared denominators and policy metadata. |
| [settle.py](settle.py) | Two-phase event-time settlement using available true-before/true-after brackets and eligible overlapping envelopes. |
| [soc_domain_test.py](soc_domain_test.py) | Quantization-aware SoC/QPC compatibility diagnostic; compatibility is not proof of a shared oscillator. |
| [beacon_consistency.py](beacon_consistency.py) | Coarse AP-cache consistency against model bounds; not an independent station/AP accuracy test. |
| [analyze_clock_pairing_hypothesis.py](analyze_clock_pairing_hypothesis.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [analyze_observation_quality.py](analyze_observation_quality.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Current numerical results and policy changes](../../docs/research-history/results-and-validation.md), [mathematics](../../docs/clock-models/tsf-mathematics.md), [causal replay](../../docs/clock-models/causal-provider-replay.md) and [settlement](../../docs/clock-models/settled-timestamps.md).
- [Findings and procedures](../../docs/clock-models/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

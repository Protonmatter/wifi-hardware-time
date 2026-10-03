# Clock relationship analysis: tools

These tools compare saved counter observations with host timing and test competing conversion models. They can reveal inconsistent assumptions and prediction limits, but cannot establish the physical sampling instant from a good fit. Treat their output as conditional research evidence, not calibrated uncertainty or an enabled clock conversion.

## Files

| File | Role |
|---|---|
| [analyze_clock_pairing_hypothesis.py](analyze_clock_pairing_hypothesis.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [analyze_observation_quality.py](analyze_observation_quality.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](../../docs/clock-models/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

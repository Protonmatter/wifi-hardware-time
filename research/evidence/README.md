# Evidence export and validation: tools

These tools package saved observations and check that their fields, identities and declared limits agree. The resulting evidence format helps another application reject incomplete or inconsistent inputs. Structural validation does not authenticate an experiment, establish fresh sampling or grant permission to treat raw counter values as accurate time.

## Files

- [hardware_observation.py](hardware_observation.py): validate a TSF evidence selection and return an owned diagnostic record; no qualified clock profile yet.
| File | Role |
|---|---|
| [export_clock_evidence.py](export_clock_evidence.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [validate_research_bundle.py](validate_research_bundle.py) | Offline analysis/model or file transformation; see the tool header for inputs. |

## Read before running

- [Findings and procedures](../../docs/evidence/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

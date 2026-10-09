# Evidence export and validation: tools

These tools package saved observations and check that their fields, identities and declared limits agree. The resulting evidence format helps another application reject incomplete or inconsistent inputs. Structural validation does not authenticate an experiment, establish fresh sampling or grant permission to treat raw counter values as accurate time.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** A QUTS client-owned byte return is now located statically. Keep client ownership, server publication, firmware identity and timing accuracy as separate qualification states. See [current findings](../../docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

- [hardware_observation.py](hardware_observation.py): validate a TSF evidence selection and return an owned diagnostic record; no qualified clock profile yet.
| File | Role |
|---|---|
| [export_clock_evidence.py](export_clock_evidence.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [validate_research_bundle.py](validate_research_bundle.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [sync_tsf_headlines.py](sync_tsf_headlines.py) | Read-only drift check or explicit `--write` refresh of declared headline blocks from versioned retained results; [runbook](../../docs/overview/postmerge-corrections-2026-10-08.md#reproducible-headline-publication). |

## Read before running

- [Findings and procedures](../../docs/evidence/README.md).
- [Operations and current admission state](../../docs/overview/OPERATIONS.md).
- [Glossary](../../docs/glossary.md) and [migration guide](../../docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

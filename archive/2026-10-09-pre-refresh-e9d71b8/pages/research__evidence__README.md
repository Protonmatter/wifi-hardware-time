# Evidence export and validation: tools

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/research__evidence__README.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

These tools package saved observations and check that their fields, identities and declared limits agree. The resulting evidence format helps another application reject incomplete or inconsistent inputs. Structural validation does not authenticate an experiment, establish fresh sampling or grant permission to treat raw counter values as accurate time.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** A QUTS client-owned byte return is now located statically. Keep client ownership, server publication, firmware identity and timing accuracy as separate qualification states. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

## Files

- [hardware_observation.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/evidence/hardware_observation.py): validate a TSF evidence selection and return an owned diagnostic record; no qualified clock profile yet.
| File | Role |
|---|---|
| [export_clock_evidence.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/evidence/export_clock_evidence.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [validate_research_bundle.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/evidence/validate_research_bundle.py) | Offline analysis/model or file transformation; see the tool header for inputs. |
| [sync_tsf_headlines.py](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/research/evidence/sync_tsf_headlines.py) | Read-only drift check or explicit `--write` refresh of declared headline blocks from versioned retained results; [runbook](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/postmerge-corrections-2026-10-08.md#reproducible-headline-publication). |

## Read before running

- [Findings and procedures](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/evidence/README.md).
- [Operations and current admission state](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/OPERATIONS.md).
- [Glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md) and [migration guide](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/repository-layout.md).
- Keep outputs in ignored `artifacts/`. A successful command is not a timing-accuracy claim.

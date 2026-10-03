# Research delivery: evidence contract, lifecycle and predictive checks

This delivery record describes the initial offline portion of the approved roadmap.
It does not complete the application clock runtime or promote the hardware path
to calibrated timing. Existing FTM changes were preserved. No service installation
or network listener was introduced. No new hardware experiment occurred during
this initial offline stage; the subsequent [live campaign results](acquisition-campaign-2026-10-02-results.md)
record the later hardware work separately. Publication is tracked in Git history.

## Added/modified files in this work package

Research repository:

- `tools/export_clock_evidence.py`: bounded saved-capture normalization and receipts.
- `tools/validate_research_bundle.py`: strict portable v1 contract validator.
- `tools/observation_lifecycle.py`: conservative offline epoch/invalidation model.
- `experiments/qualcomm/analyze_observation_quality.py`: rational within-run and rate-transfer holdout analysis.
- `tests/test_export_clock_evidence.py`, `tests/test_evidence_contract.py`, `tests/test_lifecycle_evidence.py`, `tests/test_observation_quality.py`: positive, negative and regression tests.
- `fixtures/synthetic/clock-evidence-v1.json`, `fixtures/synthetic/clock-evidence-v1-rejections.json`: synthetic interchange fixtures.
- `docs/evidence-contract.md`: format, semantics, provenance, CLI and publication limits.
- `docs/qualification/lifecycle-matrix.md`, `docs/qualification/qualcomm-observation-matrix.md`, `docs/qualification/backend-and-reference-next-steps.md`, this delivery record: results and unresolved gates.
- `docs/superpowers/plans/2026-10-02-research-to-userspace-clock.md`, `README.md`: progress and navigation.

Downstream repository (branch `research-adoption-contract`):

- `tools/validate_research_bundle.py`, `tests/test_research_contract.py`: local contract reader and independent tests.
- `fixtures/clock-evidence-v1.json`, `fixtures/clock-evidence-v1-rejections.json`: locally mirrored fixture snapshot.
- `.github/workflows/offline-contract.yml`: offline Python 3.11 contract workflow; not run on hosted CI yet.
- `docs/contracts/research-evidence-v1.md`, `docs/contracts/clock-record-v1.md`, `docs/design/measurement-clock-v1.md`, `docs/qualification/consumer-targets.md`: usage and next runtime design.
- `README.md`: actual implemented status and links. `RESEARCH_BASELINE.md` remains unchanged.

## Review and verification

An independent read-only reviewer found two P2 issues: incomplete contract checks
before quality analysis, and failure to recompute the input-map bundle identity.
Both were reproduced in regression tests, fixed and retested. The quality loader
and exporter now use the same strict research-side contract reference; downstream
has a local copy, with no cross-checkout runtime import. Final corrections and
the whole-run rate-transfer addition were verified by tests, not a second review.

The review deliberately did not qualify live firmware drain, continuity, physical
accuracy, authenticated provenance or a production runtime. Those limitations
are retained in the contract and lifecycle documentation. Hosted CI and Linux
hardware were not used for this work package.

Verification commands from the parent workspace:

```powershell
python -m compileall -q wifi-hardware-time/tools wifi-hardware-time/experiments wifi-hardware-time/tests userspace-clock/tools userspace-clock/tests
python -m unittest discover -s wifi-hardware-time/tests -v
python -m unittest discover -s userspace-clock/tests -v
git -C wifi-hardware-time diff --check
git -C userspace-clock diff --check
```

The optional research driver-fixture test additionally needs
`WIFI_TIME_DRIVER_FIXTURE` pointing to the exact locally owned SYS file. It was
supplied during final local verification; no proprietary file is included.
The shared validator and fixture file digests were compared across repositories.
Two actual saved-run exports (12 and 11 observations) passed downstream validation;
both report `conversion_qualified: false`, `utc_qualified: false`.

The next implementation decision is the host-only clock API/toolchain and consumer
targets. The next hardware research step is a bounded repeat/load matrix with
explicit late-report and continuity handling. Neither depends on inventing an
accuracy bound from the current TSF fit.

# Read saved TSF observations through an owned diagnostic API

The new reader retrieves raw TSF values from saved evidence and returns independent application-owned records. It validates the whole capture before selecting a sample and preserves unknown timing semantics. This is useful for replay and integration testing; it does not read the live adapter, establish sample freshness or enable a hardware clock.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__tsf__tsf-evidence-reader.md).
<!-- /research-history -->

## Contents

- [Run and use](#run-and-use)
- [Record meaning](#record-meaning)
- [Rejection and ownership](#rejection-and-ownership)
- [Validation and limits](#validation-and-limits)

## Run and use

Python 3.11+; no elevation, extra dependency or network access. From the research
repository root, use the shipped synthetic example or a locally retained bundle:

```powershell
python research/tsf/read_tsf_evidence.py fixtures/synthetic/clock-evidence-v1.json --sequence 1
python research/tsf/read_tsf_evidence.py fixtures/synthetic/clock-evidence-v1.json --require-clock-input
```

The first command succeeds with a record labelled `synthetic` and
`diagnostic-only`. The second deliberately exits 1 with
`clock_input_unqualified`; no current profile qualifies for clock use.

```python
from pathlib import Path
from research.tsf.read_tsf_evidence import load_observations

records = load_observations(Path("fixtures/synthetic/clock-evidence-v1.json"))
raw_tsf = int(records[0]["tsf_raw"])
assert records[0]["clock_input_eligible"] is False
```

- Input: one existing `wifi-clock-evidence/v1` JSON file, at most 1 MiB.
- `--sequence`: optional one-based sample number; default returns all samples.
- Output: JSON on stdout only. No file or system writes; no rollback needed.
- Exit 0: diagnostic replay completed; 1: invalid/unavailable input or rejected
  clock requirement; 2: malformed CLI arguments.
- Missing files and rejected evidence produce structured errors without records.
  Keep hardware replay outputs private, like their source evidence.

## Record meaning

TSF is the Wi-Fi counter; SoC is the separately reported system-on-chip counter;
QPC is the host interval counter. An epoch normally describes continuity, but
the input format's `capture-0` label does not prove a physical hardware epoch.

| Output | Interpretation |
|---|---|
| `tsf_raw`, `soc_raw`, `global_tsf_raw` | Canonical decimal strings, preserving integer precision; not nanosecond conversions |
| `action`, `soc_semantics` | Preserve cached/unknown versus capture-requested-not-atomic distinctions |
| `storage_bits=64`, `meaningful_bits=null` | Storage representation is known; meaningful hardware width is not promoted |
| `counter_unit`, `counter_rate_hz=null` | Raw ticks remain unqualified; no fitted slope is treated as calibration |
| `host_qpc` | Request-before, request-completed and report-log observations, plus QPC frequency |
| `sample_age_ns`, `sampling_interval_qpc`, `external_uncertainty_ns` | Null: reading a saved file does not establish physical sample age, a sample bracket or an error bound |
| `source_binding`, `continuity`, `association` | Anonymized bundle-local source and unverified continuity/request-window association |
| `bundle_sha256`, `capture_key` | Content-scoped replay identity; not a live device identity, firmware epoch or authentication |
| `clock_input_eligible=false` | Hard-coded disposition of this supported profile, not a caller-controlled qualification flag |

The older `bundle_id` hashes the declared input-digest map. The additional
`bundle_sha256` covers the entire canonical supplied bundle, including observations.
This detects content differences when comparing receipts; neither hash proves
that the supplied evidence was actually measured. The reported `evidence_kind`
is preserved from validated input, not independently authenticated.

## Rejection and ownership

`validate_observation(record: dict) -> dict` in
`research/evidence/hardware_observation.py` takes exactly `schema`, `bundle` and
`sequence`, with schema `tsf-evidence-selection/v1`. It validates the entire
existing bundle before returning the selected diagnostic record. Extra quality
claims, unsupported builds, broken sample ordering and invalid existing-contract
fields reject with `ValueError` and a stable reason code.

The file reader also rejects duplicate JSON keys, nonfinite values, malformed
encoding, oversized input and incomplete JSON. It cannot recognize physical
loss or stale reports that the source evidence did not disclose. Such unknowns
remain disqualifying for clock use, even when diagnostic replay succeeds.

Every output has detached nested provenance. Mutating one output does not alter
the input or another output. Callers of the pure dict API must not concurrently
mutate the input during validation; the file reader owns its parsed input.
This is application-copy isolation, not proof of concurrent driver-memory safety.

## Validation and limits

- Eleven new tests cover owned copies, complete-bundle checks, action semantics,
  content identity, existing negative fixtures, strict JSON and CLI outcomes.
- Offline integration replayed 138 historical hardware observations across 12
  retained captures. Zero were promoted to qualified clock inputs.
- No live TSF request, firmware command, trace, registry change or clock write.
- No native getter, firmware transaction ID, fresh hardware/QPC bracket or
  downstream hardware provider is added.

See the [transport decision](../adapters/qualcomm-minimal-transport-contract.md)
and [complete-record gate](../evidence/raw-timestamp-export-gate.md). Reusing the
existing validator preserves that format's limits; a future qualified profile
requires separate evidence and review, not flipping a flag in this record.

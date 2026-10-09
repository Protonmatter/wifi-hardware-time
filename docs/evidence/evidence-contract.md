# Clock evidence contract v1

This contract defines how experimental observations are packaged and rejected when incomplete or inconsistent. It preserves raw values, source identity and acquisition limits so downstream software can inspect evidence without assuming accuracy. Passing validation confirms the document follows this format; it does not authenticate the experiment or qualify a clock conversion.

<!-- research-history:2026-10-09 -->
**Research context (2026-10-09):** Scoped technical reference. Build-specific findings and operational prerequisites retain their stated scope. [Current account](../research-history/README.md) · [Timeline](../research-history/timeline.md) · [Previous version](../../archive/2026-10-09-pre-refresh-e9d71b8/pages/docs__evidence__evidence-contract.md).
<!-- /research-history -->

**Key terms:** A schema defines allowed fields and types. Canonical encoding produces consistent bytes for hashing. A hash is a content fingerprint; matching it does not prove that a measurement is accurate. See the [glossary](../glossary.md).

## Contents

- [Format and claims](#format-and-claims)
- [Export and validate](#export-and-validate)
- [Fixtures and downstream ownership](#fixtures-and-downstream-ownership)

Status: implemented offline experimental contract. This
is an observation interchange format, not a clock API or a qualification grant.
Downstream adoption must pin the actual source revision and artifact digests.

## Format and claims

One UTF-8 JSON document contains exactly `manifest` and `observations`. Export
uses sorted keys, compact separators and a final newline. Readers reject unknown
fields instead of silently accepting a future schema. Maximum bundle file size
for the validator/analysis CLIs is 1 MiB; 1–12 observations are supported.

The manifest fixes `schema` to `wifi-clock-evidence/v1` and qualification to
`experimental-observation-only`. It contains:

| Field | Meaning |
|---|---|
| `evidence_kind` | Declared `synthetic` or `hardware-observation`; not authenticated by the reader |
| `bundle_id` | SHA-256 of the canonical `input_sha256` map; verified by the reader |
| `input_sha256` | Hashes of session, decoded records, request records and adapter endpoint snapshots; raw files stay local |
| `source` | Base Git commit, working-tree inventory digest, exporter digest and `publication_status: local-unreviewed` |
| `driver_sha256` | Exact qualified Qualcomm build; other builds are rejected |
| `source_id`, `epoch_id` | `source-0`, `capture-0`, scoped by bundle ID; never global node or boot identities |
| `continuity` | `unverified-between-observations`; endpoint snapshots do not prove continuity |
| `association` | `request-window-no-firmware-id`; not a firmware completion identifier |
| `counter_width`, `counter_unit` | 64 and `raw-ticks-unqualified` |
| `qpc_frequency_hz` | Positive canonical decimal string |
| `trace_loss`, `adapter_endpoints_up` | Must be false and true respectively to admit this bounded capture |

Each observation contains sequence, action, raw TSF/SoC/global-TSF, host request
start/completion/report-QPC values, SoC semantics, and null sampling interval and
external uncertainty. All counter/frequency values are canonical decimal strings;
sequence/action/width are small JSON integers. Booleans, floating counters,
leading zeros, negative values and overflows are rejected.

For action 3, SoC semantics are `cached_or_unknown`; action 4 uses
`capture_requested_not_atomic`. A cached SoC value remains useful raw evidence,
but cannot be used as a fresh simultaneous clock pair. Accordingly, **all v1
bundles have conversion qualification false and UTC qualification false**.

## Export and validate

From this repository, no elevation is needed:

```powershell
python research/evidence/export_clock_evidence.py artifacts/<saved-run> artifacts/<new-bundle>.json
python research/evidence/validate_research_bundle.py artifacts/<new-bundle>.json
```

The exporter requires `session.json`, `raw-timing.jsonl`, `request.json` or the
numbered request files, and `adapter-before.json`/`adapter-after.json`. It checks
the planned count/action sequence, typed QPC/counters, exact build/interface,
zero trace loss, successful completion/handle close, ordered nonoverlapping
windows, one command/report/SoC/delay group per window, matching vdev, modulo
delay arithmetic and increasing TSF. Missing metadata is a rejection, not an
assumed default success. Interface indexes and vdev are used locally, not exported.

The source manifest fingerprints the current tracked and nonignored untracked
file inventory, including new source files. The base commit alone does not
describe a dirty working tree. An inventory digest identifies content but cannot
reconstruct it; retain the corresponding patch/source snapshot for reproduction.

Output paths must be new; no overwrite is permitted. Exit 0 means completed
export/validation; exit 1 means invalid evidence or I/O failure; argparse usage
errors use exit 2. A write failure can leave a partial new file: do not consume it;
choose a fresh output path on retry. No device state changes or operational rollback
are required. CLI tools perform no network calls or driver operations.

The historical exporter function name `export_sanitized` means fixed-field
selection, not automatic publication approval. Numeric timings and hashes still
require publication review. Input evidence hashes are not signatures; a bundle
can be forged or coherently edited. The export receipt hashes the entire output;
verify that receipt when transporting a reviewed bundle. Bundle ID binds the
input digest map, not independently the normalized observation content.

## Fixtures and downstream ownership

`fixtures/synthetic/clock-evidence-v1.json` is wholly synthetic. Its request data
is constructed in tests, including a deliberately ignored extra string. Eight
negative mutations in `clock-evidence-v1-rejections.json` exercise rejected
schemas, loss, build, false accuracy, sequence, counter regression, lossy numbers
and false simultaneous-latch claims. They contain no raw hardware trace.

A v1 reference validator and the two fixture files are copied into
`userspace-clock` as a local versioned handoff. Each checkout executes its own
copy without importing a neighboring repository. This intentionally duplicates
the small contract reference across repository boundaries; compare file digests
when updating it and rerun each repository's tests. It is not the experimental
capture harness and does not initialize a production provider.

On publication, downstream must pin the actual research revision and artifact
digests after review. The synthetic fixture's `local-unreviewed` source field
describes its generation snapshot; publishing a synthetic fixture does not
authenticate a hardware observation or turn it into a qualified clock.

# FTM aggregation and TSF delivery: exact-build follow-up

> **Archive — not current operating instructions.** Historical documentation at [e9d71b843651](https://github.com/Protonmatter/wifi-hardware-time/commit/e9d71b84365122ff2640e240b20fc1dbb834388a). Relative links are rebased for reading. [Exact original bytes](../originals/docs__ftm__ftm-result-provenance.md.txt) · [Archive index](../README.md) · [Current research](../../../docs/research-history/README.md).

Why can a successful ranging result contain no measurements, and what does its variance field mean? Saved-record replay matches the driver’s sample selection and aggregation, including empty results. The field named variance is not qualified as statistical variance, and the separate counter-report path supplies no absolute clock mapping.

<!-- historical-context:2026-10-04 -->
**Historical context (2026-10-04):** QXDM WLAN RTT definitions are a new schema lead. They have not been matched to a complete live four-event export from this adapter. See [current findings](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/knowledge/current-findings.md).
<!-- /historical-context -->

FTM (Fine Timing Measurement) is Wi-Fi ranging; RTT is round-trip time. TSF is the Wi-Fi timer, and QPC is the Windows host counter. An RVA locates instructions within the exact binary. See the [glossary](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/glossary.md).

## Contents

- [Why success can accompany zero measurements](#why-success-can-accompany-zero-measurements)
- [The raw variance field is not qualified as variance](#the-raw-variance-field-is-not-qualified-as-variance)
- [Replay evidence](#replay-evidence)
- [TSF command payload and report handoff](#tsf-command-payload-and-report-handoff)

Analysis date: 2026-10-02. This work used the saved captures and static ARM64
driver disassembly. It did not initiate a new FTM exchange, private request,
adapter restart, register operation, or clock adjustment.

The installed `qcwlanhmt8380.sys` SHA-256 was rechecked as
`ca884ce1a22113194f3c467f36abc39afb0c137e5a7a8e2697420438b21e4115`.
All RVAs below apply only to that file. They are analysis references, not call
targets. Raw binaries, disassembly, traces and endpoint identifiers remain local.

## Why success can accompany zero measurements

The routine identified by its `RttPopulateWdiRspParams` diagnostic string starts
at RVA `0x1462a0`. It builds an 80-byte internal WDI result; that is distinct
from the 104-byte userspace callback record. The inspected paths establish:

| RVAs | Operation |
|---|---|
| `0x146410`–`0x146438` | Copy target status independently of the sample selection |
| `0x14643c`–`0x146538` | Sort and filter two eight-slot signed RTT arrays; `INT32_MIN` marks an empty/rejected slot |
| `0x14653c`–`0x146578` | Count remaining entries in the two arrays |
| `0x14663c`–`0x1466cc` | Compute each signed integer mean, truncating toward zero; substitute `-1` for an empty array |
| `0x1466cc`–`0x1466dc` | Select the lower mean and the corresponding count; ties select array 0 |
| `0x146710`–`0x146724` | Clear the auxiliary field when the selected count is zero |

The driver's diagnostics call the arrays `ch0` and `ch1`. This analysis does
not equate those labels with RF channel numbers or independently calibrated
antenna measurements.

An empty array gets a mean of -1, which is lower than a real nonnegative mean.
The resulting selected count is zero even if the other array has entries.
This explains the saved empty callback records, but does not explain why the
firmware produced the underlying entries.

For example, one saved post-filter log group contains eight `INT32_MIN` slots
in `ch0`, and `[0, INT32_MIN, ...]` in `ch1`. The means used for selection are
`-1` and `0`. The selected count is zero, RTT is `-1`, and the auxiliary field
is zero, matching the callback. The other zero-count callback replayed here
has the same pattern. These are not evidence of a negative propagation time.

The existing nonzero-count guard remains necessary. A nonzero count establishes
that the result contains selected entries, not that those entries are accurate.
This investigation does not justify substituting the other array into an
application result or changing the live driver.

## The raw variance field is not qualified as variance

At `0x146580`–`0x146624`, the driver computes two truncated signed means,
weights them by their counts, and divides the combined numerator by the total
count using **unsigned** 64-bit division. It writes that result to internal
offset `0x28`. No squared deviations occur in this inspected calculation.

For all ten replayed records, this quantity matches callback offset `0x20`,
currently exposed by the decoder as `reported_rtt_variance_raw`. This is strong
exact-run evidence for its provenance, not a complete proof of every OS
marshalling path. Its existing field name is retained for compatibility, with
the added flag `rtt_variance_semantics_validated: false`. Do not take its square
root, use it as a confidence interval, or promote it to timing uncertainty.

The offline model also retains the unsigned-division behavior for negative
combined numerators. That edge case is covered synthetically; it was not
observed in the ten replayed records.

## Replay evidence

`PrintRttResults` is called after filtering (`0x146870`); its routine at
`0x145968` prints each array as eight signed integers. The offline model accepts
these post-filter arrays only. It does not reconstruct pre-filter firmware
samples, the filter threshold arithmetic, or the entire WDI state machine.

| Saved run | Records | Callback count / RTT / auxiliary matched |
|---|---:|---:|
| `WifiFtm-83d68ef1a7aa` | 4 | 4/4 |
| `WifiFtm-89003fb1ba0a` | 5 | 5/5 |
| `WifiFtm-43963cbc551c` | 1 | 1/1 |

Each log group had exactly eight entries per array. Groups were paired with
the ordered single-target callback files in their saved run. This is an
offline ordered replay, not firmware transaction-ID correlation. The saved
trace health records report no lost events or buffers.

ETL SHA-256 values, in the same order:

```text
49a2c27b03405202399094bbae6f514f4bff7ee0c7bd0f659978778407bb648c
7ec0ec66188b12fc17c603eab53b17385b443dabdc3c154ac3003a2eb627f363
4627df00842b1be22cdf07a29a894b9e6cdec3d9bbc9fe40865c5a3d962180ff
```

The four numeric cases from the first run are retained in
`tests/test_ftm_selection.py`, alongside synthetic empty-array, tie, signed
rounding, unsigned-division, and invalid-input cases. Run from the repository:

```powershell
python -m compileall -q research tests
python -m unittest discover -s tests -v
```

The model in `research/ftm/model_ftm_selection.py` is a pure importable
research function, requires no elevation or new dependencies, and performs no
I/O. Invalid input raises `ValueError`; it does not install a component or
require an operational rollback.

## TSF command payload and report handoff

Tracing the allocator resolves the previously unaccounted-for tail of the
20-byte command payload:

1. `0x195638` requests 20 bytes from allocator `0x168bd8`.
2. `0x168c24`–`0x168c2c` zeroes the payload through the memory-fill routine.
3. `0x19568c`–`0x1956a0` writes a tag-length-value (TLV) header `0x018a0010`, vdev and action to
   offsets 0, 4 and 8. The remaining eight bytes remain zero on this path.
4. `0x1956b8`–`0x1956c8` submits command `0x5012`, length 20.

There is no host QPC sample or caller transaction token in this payload. That
does not exclude lower transport metadata; it means this command cannot alone
establish a QPC-to-hardware sampling instant.

The report handler at `0x216b00` copies the vdev, TSF, SoC and global-TSF
fields and logs the wide counters. At `0x216c00`–`0x216c08`, it subtracts the
low SoC word from the low TSF word using 32-bit arithmetic. At
`0x216c30`–`0x216c48`, the examined indirect callback receives the vdev byte
and this difference, not the full counter pair. The temporary report object
is subsequently freed. This particular handoff is not a userspace clock-pair
API, and the modulo difference must not be treated as an absolute clock offset.
Other possible downstream paths have not been exhaustively excluded.

The older public firmware header referenced in [sources](https://github.com/Protonmatter/wifi-hardware-time/blob/e9d71b84365122ff2640e240b20fc1dbb834388a/docs/overview/sources.md) has a
shorter command structure; it cannot establish the meaning of the Windows
payload's extra zero bytes. We do not assign them undocumented semantics.

Exact firmware sampling, simultaneous latching and independent-reference
accuracy remain unresolved. The useful advance is that both an FTM result
ambiguity and the TSF host handoff are now constrained by specific code paths
and, for FTM, replay against saved measurements.

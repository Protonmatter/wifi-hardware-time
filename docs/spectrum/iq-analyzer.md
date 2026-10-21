# Finite I/Q spectrum analyzer

This tool draws a spectrum and a waterfall from one finite raw I/Q recording. It is the host half of a WCN7850 (FastConnect 7800) spectrum sensor. It does not capture from the radio. A working spectral export from `qcwlanhmt8380.sys` is not established in this repository, so a capture file has to be produced elsewhere and then analyzed here.

Power is dBFS relative to a full-scale complex tone. `rf_calibrated` and `physical_bound_proven` stay false. A QPC stamp in the header is stored, not checked against the samples, and it does not identify which sample inside the buffer was the radio's read point.

## Capture file

`wht/iq-capture-v1` is an ASCII header, a blank line, then little-endian int16 I/Q pairs:

```text
schema: wht/iq-capture-v1
sample_rate_hz: 20000000
center_hz: 5180000000
qpc_start: 1000000
qpc_hz: 10000000
chip: WCN7850

<int16 I, int16 Q, ...>
```

`sample_rate_hz` and `center_hz` are required. `qpc_start` and `qpc_hz` are recorded together or not at all. `chip` is a label, not a detected identity. At most 20,000,000 complex samples and a 4,096-byte header (including the blank line) are accepted. The reader rejects oversized inputs before allocating their payload. The CLI stores samples as compact int16 pairs, rather than one Python complex object per sample. The recording must remain unchanged while being read; size checks cannot establish capture provenance or detect every concurrent in-place rewrite.

## Run

```text
python -m research.spectrum.analyze_iq capture.iq --fft-size 4096 --output-dir artifacts/spectrum
```

Outputs, under the chosen directory:

| File | Contents |
|---|---|
| `spectrum.json` | Existing median peak/floor, maximum-spectrum peak, temporal coverage, selection counts, detection limits, and unqualified-RF/clock flags |
| `spectrum.csv` | `frequency_hz,median_dbfs,max_dbfs`: median and maximum over selected frames for each bin |
| `waterfall.ppm` | One colored row per analyzed frame, ordered by sample offset; equal row spacing does not mean equal elapsed time |

The FFT length is a power of two from 256 to 65536. Captures shorter than one FFT are rejected. Exit status is `0` on success and `1` for rejected input or an I/O failure. No radio, driver, service, network, or host-clock sampling operation is performed.

## Bounded screening and frame selection

The original selector transformed at most 32 half-hop frames distributed across the capture. At 20 million samples with a 4096-point FFT, their nonoverlapping spans contained only 131,072 samples (0.65536%). A synthetic burst at 200,000..204,999 (10..10.25 ms at 20 MHz) fell between those frames. This is a software counterexample, not an RF observation.

Three approaches were considered:

| Approach | Benefit | Limit |
|---|---|---|
| More uniformly spaced frames | Small change, deterministic cost | Retains blind time gaps and can miss the same kind of burst |
| FFT every half-hop frame | Broad spectral time coverage | Up to 156,249 Python FFTs at the minimum FFT size for an accepted capture, instead of 32; changes the execution budget substantially |
| Whole-capture energy screening, then selected FFTs | Inspects every sample for broadband energy and prioritizes elevated intervals while retaining 32 FFTs | Energy is a heuristic; it cannot establish complete spectral detection |

The third approach is used:

1. Scan **every sample** once for mean-square complex magnitude (`I*I + Q*Q`) in consecutive blocks of `fft_size / 4` samples. Include and normalize the last partial block by its actual length.
2. Use the lower median block energy as the background reference. A block is a candidate only when its energy is strictly greater than four times that reference (about 6.02 dB). For zero background, any nonzero block qualifies. These are raw int16 squared units, not calibrated RF power or statistical detection confidence.
3. Combine contiguous candidate blocks into intervals. Rank intervals by their strongest block; break equal-energy ties by earlier sample offset. Retain at most 16 interval representatives in a bounded heap. For an interval at least one FFT long, center on the strongest block and constrain the window to stay inside that interval. Center a shorter interval within its FFT window. Clamp all windows to the capture endpoints. A long burst therefore does not consume every priority slot.
4. For long captures, give every slot not used by a priority window to distributed background frames, including the first and final full windows. There are at least 16 background frames; one priority window leaves 31 background frames. Remove duplicates and fill any remaining slots from a distributed grid. Sort the result by sample offset. At most 32 FFTs are executed.
5. If the complete half-hop grid plus a final tail-aligned window fits within 32 frames, transform that entire grid instead. Its FFT spans cover all samples, including a non-hop-aligned tail.

With no candidate intervals, long captures retain a full 32-frame distributed grid. Prioritizing bursts trades some uniform sampling density for energy-guided windows; on some inputs, the largest gap outside FFT spans increases relative to the original selector. The coverage metadata exposes this tradeoff rather than promising a smaller worst-case blind interval.

Working storage for selection is one energy value per block, the bounded interval heap, and at most 32 starts. There are at most 312,500 energy blocks for accepted inputs. Computing the lower median sorts those block energies; it does not sort or retain a second copy of all complex samples. Work is bounded by `O(N + B log B + 32 F log F)` for sample count `N`, block count `B`, and FFT size `F`. The CLI's compact capture payload is at most 80 MB; reading it can temporarily require another payload-sized buffer. FFT/result memory depends on `32 * F`, not capture length. Direct callers choosing the legacy list representation additionally allocate one Python complex object per sample. These are structural bounds, not a wall-clock timeout or a guaranteed process-memory ceiling across Python implementations. No native FFT library or new dependency is required.

## Metadata and interpretation

`wht/iq-spectrum-v1` retains the existing fields and adds coverage and maximum-spectrum fields. The first two CSV columns keep their meanings; consumers requiring exactly two columns must accept the new third column. `read_capture(path)['samples']` preserves its mutable-list interface. The CLI uses the additive `read_capture(path, compact=True)` option, whose sample collection is a read-only sequence supporting indexing, slicing and iteration.

- `peak_hz`, `peak_dbfs`, and `median_floor_dbfs` still describe the median over the selected FFT frames. `max_peak_hz` and `max_peak_dbfs` describe the maximum over those same frames. A brief burst can disappear from the median even when selected, so inspect `max_dbfs` and the waterfall too. Neither aggregate is an estimate of time occupancy or a whole-capture spectral maximum.
- `temporal_coverage.energy_screened_samples` and `energy_coverage_fraction` report the energy pass (the entire accepted recording). `fft_unique_samples` and `fft_coverage_fraction` count the union of selected FFT window spans; overlapping samples count once. Hann endpoints have zero weight, so span coverage is not uniform detection sensitivity.
- `max_unanalyzed_gap_samples` and `max_unanalyzed_gap_s` describe the largest time gap outside FFT spans. `frame_starts_samples` and `frame_start_offsets_s` identify each waterfall row. `waterfall_rows_uniform_time` reports whether adjacent start offsets actually have identical sample spacing (also true for a single row). `capture_duration_s`, `fft_window_duration_s`, and all time offsets use the file's declared sample rate. They are relative sample coordinates, not qualified QPC timestamps.
- `frame_selection` reports the strategy, block size/count, lower-median raw energy reference, fourfold threshold, input/FFT resource ceilings, and candidate/selected/omitted interval counts. On long captures, selected counts are retained priority representatives; omitted intervals may happen to overlap distributed frames but did not get a priority slot. On short exhaustive captures, all candidate intervals lie within analyzed spans. Priority starts are listed separately.
- `detection_limitations` is included in every JSON result. `power_units` stays `dBFS`; `rf_calibrated`, `physical_bound_proven`, `hardware_acquisition_established`, and `host_clock_timestamping_established` stay false. Header stamps and chip labels do not change those flags.

## Detection limits

Full energy screening **does not mean full FFT analysis**. Weak or very short bursts may be diluted below the block threshold. Constant-energy changes in frequency content can be invisible to broadband screening. A high duty cycle raises the background reference; equal-energy interference replacing a signal can also evade selection. More than 16 candidate intervals compete for priority; weaker intervals can be omitted. One representative does not describe every spectral change inside a long interval. Bursts at Hann-window edges can be attenuated. Quiet output is therefore not evidence that interference is absent.

The fixtures cover a burst between the old frames, the one-second 20 MHz counterexample, narrowband bursts over a clean tone and seeded noise, silence, continuous tones, partial tails, several FFT sizes and capture lengths, selection-budget overflow, deterministic repetition, and an intentionally missed constant-energy frequency change. They qualify software behavior on synthetic inputs only.

## Offline validation and rollback

Run from the repository root:

```text
python -m compileall -q research tests
python -m unittest discover -s tests -p test_iq_spectrum.py -v
python -m unittest discover -s tests -v
python research/evidence/build_knowledge_index.py --check
```

Generate artifacts with the command above and read back the JSON coverage and frame starts, the CSV maximum column, and the PPM dimensions/pixel payload. Preserve a capture's source and generation parameters separately; the format does not attest them. Rollback consists of restoring the analyzer, its tests, this document and the two generated knowledge indexes to the prior revision, then regenerating outputs in a separate directory. There is no device state to roll back. Existing output filenames are overwritten when reused; partial output files can remain after an I/O failure.

A 20 MHz capture has one complex sample every 50 ns. That spacing describes the radio bandwidth. It becomes a timestamp only when a later capture path pairs the buffer to host QPC and locates the read point inside it.

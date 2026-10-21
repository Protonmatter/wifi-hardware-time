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

`sample_rate_hz` and `center_hz` are required. `qpc_start` and `qpc_hz` are recorded together or not at all. `chip` is a label, not a detected identity. At most 20,000,000 complex samples are accepted.

## Run

```text
python -m research.spectrum.analyze_iq capture.iq --fft-size 4096 --output-dir artifacts/spectrum
```

Outputs, under the chosen directory:

| File | Contents |
|---|---|
| `spectrum.json` | Peak frequency and dBFS, bin width, frame count, and the unqualified-RF flags |
| `spectrum.csv` | Median dBFS of each FFT bin |
| `waterfall.ppm` | One colored row per analyzed frame |

The FFT length is a power of two from 256 to 65536. Frames hop by half that length. At most 32 frames are transformed, spread across the capture, so a long recording still returns without requiring a native FFT library.

A 20 MHz capture has one complex sample every 50 ns. That spacing describes the radio bandwidth. It becomes a timestamp only when a later capture path pairs the buffer to host QPC and locates the read point inside it.

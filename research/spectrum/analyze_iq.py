"""Spectrum and waterfall for one finite raw I/Q capture. Offline only.

The capture is little-endian int16 I/Q with a text header. Power is dBFS
against a full-scale complex tone. Nothing here calibrates dBm, names the
WCN7850 read point, or pairs samples to QPC beyond a stamp the file already
carries. This module does not talk to a radio.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import argparse
import json
import math
import statistics

CAPTURE_SCHEMA = 'wht/iq-capture-v1'
SUMMARY_SCHEMA = 'wht/iq-spectrum-v1'
FULL_SCALE = 32767
MAX_SAMPLES = 20_000_000
MAX_FRAMES = 32
_HEADER_KEYS = frozenset({'schema', 'sample_rate_hz', 'center_hz', 'qpc_start', 'qpc_hz', 'chip'})


def _positive_int(value: str, name: str) -> int:
    try:
        number = int(value, 10)
    except ValueError as error:
        raise ValueError(f'{name} must be an integer') from error
    if number <= 0:
        raise ValueError(f'{name} must be positive')
    return number


def write_capture(path: Path, pairs, *, sample_rate_hz: int, center_hz: int,
                  qpc_start: int | None = None, qpc_hz: int | None = None, chip: str | None = None) -> None:
    """Write one capture. pairs is a sequence of (I, Q) integers in the int16 range."""
    header = [f'schema: {CAPTURE_SCHEMA}', f'sample_rate_hz: {sample_rate_hz}', f'center_hz: {center_hz}']
    if (qpc_start is None) != (qpc_hz is None):
        raise ValueError('qpc_start and qpc_hz are recorded together')
    if qpc_start is not None:
        header += [f'qpc_start: {qpc_start}', f'qpc_hz: {qpc_hz}']
    if chip is not None:
        if not chip or any(character in chip for character in ':\n'):
            raise ValueError('chip must be a single-line label')
        header.append(f'chip: {chip}')
    body = bytearray()
    for i_value, q_value in pairs:
        if type(i_value) is not int or type(q_value) is not int or not -32768 <= i_value <= 32767 or not -32768 <= q_value <= 32767:
            raise ValueError('I/Q samples must be int16')
        body += int(i_value).to_bytes(2, 'little', signed=True)
        body += int(q_value).to_bytes(2, 'little', signed=True)
    path.write_bytes(('\n'.join(header) + '\n\n').encode('ascii') + body)


def read_capture(path: Path) -> dict:
    raw = path.read_bytes()
    marker = raw.find(b'\n\n')
    if marker < 0:
        raise ValueError('Capture header must end with a blank line')
    try:
        text = raw[:marker].decode('ascii')
    except UnicodeError as error:
        raise ValueError('Capture header must be ASCII') from error
    fields = {}
    for line in text.splitlines():
        if not line or ':' not in line:
            raise ValueError('Capture header line must be key: value')
        key, value = line.split(':', 1)
        key, value = key.strip(), value.strip()
        if key in fields or key not in _HEADER_KEYS:
            raise ValueError(f'Unexpected capture header field {key}')
        fields[key] = value
    if fields.get('schema') != CAPTURE_SCHEMA:
        raise ValueError(f'Capture schema must be {CAPTURE_SCHEMA}')
    sample_rate_hz = _positive_int(fields['sample_rate_hz'], 'sample_rate_hz')
    center_hz = _positive_int(fields['center_hz'], 'center_hz')
    qpc_start = qpc_hz = None
    if 'qpc_start' in fields or 'qpc_hz' in fields:
        if 'qpc_start' not in fields or 'qpc_hz' not in fields:
            raise ValueError('qpc_start and qpc_hz are recorded together')
        qpc_start = int(fields['qpc_start'], 10)
        qpc_hz = _positive_int(fields['qpc_hz'], 'qpc_hz')
        if qpc_start < 0:
            raise ValueError('qpc_start must be non-negative')
    payload = raw[marker + 2:]
    if len(payload) % 4:
        raise ValueError('I/Q payload must be whole int16 pairs')
    count = len(payload) // 4
    if count == 0 or count > MAX_SAMPLES:
        raise ValueError(f'Capture must contain 1 to {MAX_SAMPLES} complex samples')
    samples = []
    for offset in range(0, len(payload), 4):
        i_value = int.from_bytes(payload[offset:offset + 2], 'little', signed=True)
        q_value = int.from_bytes(payload[offset + 2:offset + 4], 'little', signed=True)
        samples.append(complex(i_value, q_value))
    return dict(sample_rate_hz=sample_rate_hz, center_hz=center_hz, qpc_start=qpc_start, qpc_hz=qpc_hz,
                chip=fields.get('chip'), samples=samples)


def _fft(values: list[complex]) -> list[complex]:
    n = len(values)
    if n < 2 or n & (n - 1):
        raise ValueError('FFT length must be a power of two')
    out = list(values)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            out[i], out[j] = out[j], out[i]
    length = 2
    while length <= n:
        angle = -2.0 * math.pi / length
        step = complex(math.cos(angle), math.sin(angle))
        for start in range(0, n, length):
            twiddle = 1 + 0j
            half = length // 2
            for k in range(half):
                even = out[start + k]
                odd = out[start + k + half] * twiddle
                out[start + k] = even + odd
                out[start + k + half] = even - odd
                twiddle *= step
        length *= 2
    return out


def _hann(n: int) -> list[float]:
    return [0.5 - 0.5 * math.cos(2.0 * math.pi * i / n) for i in range(n)]


def _frame_indexes(count: int, fft_size: int) -> list[int]:
    hop = fft_size // 2
    last = count - fft_size
    if last < 0:
        raise ValueError(f'Capture is shorter than the {fft_size}-point FFT')
    starts = list(range(0, last + 1, hop))
    if len(starts) <= MAX_FRAMES:
        return starts
    if MAX_FRAMES == 1:
        return [0]
    picked = []
    for index in range(MAX_FRAMES):
        position = round(index * (len(starts) - 1) / (MAX_FRAMES - 1))
        if not picked or picked[-1] != starts[position]:
            picked.append(starts[position])
    return picked


def spectrum(samples: list[complex], sample_rate_hz: int, center_hz: int, fft_size: int) -> dict:
    if fft_size < 256 or fft_size > 65536 or fft_size & (fft_size - 1):
        raise ValueError('fft_size must be a power of two from 256 to 65536')
    window = _hann(fft_size)
    coherent = sum(window) / fft_size
    rows = []
    for start in _frame_indexes(len(samples), fft_size):
        frame = samples[start:start + fft_size]
        transformed = _fft([sample * window[i] / FULL_SCALE for i, sample in enumerate(frame)])
        shifted = transformed[fft_size // 2:] + transformed[:fft_size // 2]
        rows.append([20.0 * math.log10(max(abs(bin_value) / (fft_size * coherent), 1e-12)) for bin_value in shifted])
    width = len(rows[0])
    median = [statistics.median(row[bin_index] for row in rows) for bin_index in range(width)]
    peak_bin = max(range(width), key=median.__getitem__)
    bin_hz = sample_rate_hz / fft_size
    frequencies = [center_hz + (index - fft_size // 2) * bin_hz for index in range(width)]
    return dict(frequencies_hz=frequencies, median_dbfs=median, rows_dbfs=rows,
                peak_hz=frequencies[peak_bin], peak_dbfs=median[peak_bin], frames=len(rows), bin_hz=bin_hz)


def _color(dbfs: float) -> tuple[int, int, int]:
    stops = ((8, 12, 48), (0, 90, 200), (20, 190, 120), (240, 210, 40), (220, 40, 30))
    t = min(1.0, max(0.0, (dbfs + 120.0) / 120.0))
    position = t * (len(stops) - 1)
    index = min(int(position), len(stops) - 2)
    mix = position - index
    left, right = stops[index], stops[index + 1]
    return tuple(int(left[channel] + (right[channel] - left[channel]) * mix) for channel in range(3))


def write_waterfall(path: Path, rows: list[list[float]]) -> None:
    height, width = len(rows), len(rows[0])
    pixels = bytearray()
    for row in rows:
        for value in row:
            pixels += bytes(_color(value))
    path.write_bytes(f'P6\n{width} {height}\n255\n'.encode('ascii') + pixels)


def analyze(capture: dict, fft_size: int) -> dict:
    result = spectrum(capture['samples'], capture['sample_rate_hz'], capture['center_hz'], fft_size)
    return dict(schema=SUMMARY_SCHEMA, chip=capture['chip'], sample_rate_hz=capture['sample_rate_hz'],
                center_hz=capture['center_hz'], qpc_start=capture['qpc_start'], qpc_hz=capture['qpc_hz'],
                samples=len(capture['samples']), fft_size=fft_size, frames=result['frames'], bin_hz=result['bin_hz'],
                peak_hz=result['peak_hz'], peak_dbfs=round(result['peak_dbfs'], 3),
                median_floor_dbfs=round(statistics.median(result['median_dbfs']), 3),
                rf_calibrated=False, physical_bound_proven=False,
                scope='dBFS of a finite I/Q capture; not calibrated RF power and not a QPC timestamp',
                _plot=result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--fft-size', type=int, default=4096)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        capture = read_capture(args.capture)
        summary = analyze(capture, args.fft_size)
        plot = summary.pop('_plot')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / 'spectrum.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        with (args.output_dir / 'spectrum.csv').open('w', encoding='utf-8') as stream:
            stream.write('frequency_hz,median_dbfs\n')
            for frequency, power in zip(plot['frequencies_hz'], plot['median_dbfs']):
                stream.write(f'{frequency:.3f},{power:.6f}\n')
        write_waterfall(args.output_dir / 'waterfall.ppm', plot['rows_dbfs'])
        print(json.dumps(dict(peak_hz=summary['peak_hz'], peak_dbfs=summary['peak_dbfs'], frames=summary['frames'])))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f'Spectrum rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

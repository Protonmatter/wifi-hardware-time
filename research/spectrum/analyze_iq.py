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
from array import array
from collections.abc import Iterator, Sequence
import heapq
import json
import math
import os
import statistics
from typing import overload

CAPTURE_SCHEMA = 'wht/iq-capture-v1'
SUMMARY_SCHEMA = 'wht/iq-spectrum-v1'
FULL_SCALE = 32767
MAX_SAMPLES = 20_000_000
MAX_FRAMES = 32
MAX_HEADER_BYTES = 4096
ENERGY_RATIO = 4.0
_HEADER_KEYS = frozenset({'schema', 'sample_rate_hz', 'center_hz', 'qpc_start', 'qpc_hz', 'chip'})


class _IQSamples(Sequence[complex]):
    """Compact int16 storage; only requested FFT slices become complex lists."""

    def __init__(self, values: array) -> None:
        self.values = values

    def __len__(self) -> int:
        return len(self.values) // 2

    @overload
    def __getitem__(self, index: int) -> complex: ...

    @overload
    def __getitem__(self, index: slice) -> list[complex]: ...

    def __getitem__(self, index: int | slice) -> complex | list[complex]:
        if isinstance(index, slice):
            return [self[position] for position in range(*index.indices(len(self)))]
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return complex(self.values[2 * index], self.values[2 * index + 1])

    def __iter__(self) -> Iterator[complex]:
        values = iter(self.values)
        return (complex(i, q) for i, q in zip(values, values))


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


def read_capture(path: Path, *, compact: bool = False) -> dict:
    """Read finite int16 I/Q; compact mode avoids a capture-sized complex list.

    The default preserves the existing mutable-list API. The bounded CLI uses
    compact=True and only materializes the requested FFT slices as complex lists.
    """
    # Inspect a bounded header before allocating storage for a bounded payload.
    with path.open('rb') as stream:
        raw = stream.read(MAX_HEADER_BYTES + 1)
    marker = raw.find(b'\n\n')
    if marker < 0 or marker + 2 > MAX_HEADER_BYTES:
        raise ValueError(f'Capture header must end with a blank line within {MAX_HEADER_BYTES} bytes')
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
    values = array('h')
    with path.open('rb') as stream:
        # Recheck the header so replacement between opens cannot silently change it.
        if stream.read(marker + 2) != raw[:marker + 2]:
            raise ValueError('Capture header changed while reading')
        payload_bytes = os.fstat(stream.fileno()).st_size - stream.tell()
        if payload_bytes % 4:
            raise ValueError('I/Q payload must be whole int16 pairs')
        count = payload_bytes // 4
        if count == 0 or count > MAX_SAMPLES:
            raise ValueError(f'Capture must contain 1 to {MAX_SAMPLES} complex samples')
        try:
            values.fromfile(stream, count * 2)
        except EOFError as error:
            raise ValueError('Capture payload truncated while reading') from error
        if stream.read(1):
            raise ValueError('Capture payload grew while reading')
    if sys.byteorder != 'little':
        values.byteswap()
    samples: Sequence[complex] = _IQSamples(values)
    if not compact:
        samples = list(samples)
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


def _frame_indexes(count: int, fft_size: int, limit: int = MAX_FRAMES) -> list[int]:
    hop = fft_size // 2
    last = count - fft_size
    if last < 0:
        raise ValueError(f'Capture is shorter than the {fft_size}-point FFT')
    frame_count = last // hop + 1 + bool(last % hop)
    if frame_count <= limit:
        starts = list(range(0, last + 1, hop))
        if starts[-1] != last:
            starts.append(last)
        return starts
    if limit == 1:
        return [0]
    return [(index * last + (limit - 1) // 2) // (limit - 1) for index in range(limit)]


def _select_frames(samples: Sequence[complex], fft_size: int) -> tuple[list[int], dict]:
    """Screen all samples, retaining at most 16 elevated-energy interval peaks.

    Energy is a broadband heuristic, not a classifier or a calibrated detector.
    One representative per contiguous above-threshold interval prevents a long
    strong burst from consuming every priority slot. Equal scores prefer earlier
    intervals. The quarter-FFT blocks include the final partial block.
    """
    count = len(samples)
    uniform = _frame_indexes(count, fft_size)
    block_size = fft_size // 4
    energies = array('d')
    total = 0.0
    for index, sample in enumerate(samples):
        total += sample.real * sample.real + sample.imag * sample.imag
        if (index + 1) % block_size == 0:
            energies.append(total / block_size)
            total = 0.0
    if count % block_size:
        energies.append(total / (count % block_size))
    # Lower median keeps a half-active recording's quiet half as the reference.
    baseline = sorted(energies)[(len(energies) - 1) // 2]
    threshold = baseline * ENERGY_RATIO
    priority_budget = MAX_FRAMES // 2
    strongest: list[tuple[float, int]] = []
    candidate_count = 0
    best: tuple[float, int] | None = None
    interval_start = 0

    def retain(peak: tuple[float, int], begin: int, end: int) -> None:
        nonlocal candidate_count
        candidate_count += 1
        if end - begin >= fft_size:
            # Keep the window inside a long energy interval where possible.
            start = min(max(-peak[1] - fft_size // 2, begin), end - fft_size)
        else:
            # Center short intervals instead of putting their onset at the peak.
            start = (begin + end - fft_size) // 2
        start = max(0, min(count - fft_size, start))
        candidate = (peak[0], -start)
        if len(strongest) < priority_budget:
            heapq.heappush(strongest, candidate)
        elif candidate > strongest[0]:
            heapq.heapreplace(strongest, candidate)

    for block, energy in enumerate(energies):
        if energy > threshold:
            offset = block * block_size
            center = offset + min(block_size, count - offset) // 2
            candidate = (energy, -center)
            if best is None:
                interval_start = offset
            if best is None or candidate > best:
                best = candidate
        elif best is not None:
            retain(best, interval_start, block * block_size)
            best = None
    if best is not None:
        retain(best, interval_start, count)

    last = count - fft_size
    exhaustive = last // (fft_size // 2) + 1 + bool(last % (fft_size // 2)) <= MAX_FRAMES
    if exhaustive:
        starts = uniform
        selected_count = candidate_count
        priority_starts = []
    else:
        priority_starts = sorted({-candidate[1] for candidate in strongest})
        selected_count = len(strongest)
        if not priority_starts:
            starts = uniform
        else:
            # Spend every unneeded priority slot on distributed background coverage.
            background_budget = MAX_FRAMES - len(priority_starts)
            starts = set(_frame_indexes(count, fft_size, background_budget) + priority_starts)
            available = [start for start in uniform if start not in starts]
            needed = MAX_FRAMES - len(starts)
            if needed == 1:
                starts.add(available[len(available) // 2])
            elif needed > 1:
                starts.update(available[index * (len(available) - 1) // (needed - 1)]
                              for index in range(needed))
            starts = sorted(starts)
    return starts, dict(strategy='whole-capture-energy-plus-distributed-frames',
                        screening_block_samples=block_size, screening_blocks=len(energies),
                        baseline_mean_square=baseline,
                        energy_threshold_ratio=ENERGY_RATIO, candidate_intervals=candidate_count,
                        selected_intervals=selected_count, omitted_intervals=candidate_count - selected_count,
                        priority_frame_starts_samples=priority_starts, max_frames=MAX_FRAMES,
                        max_capture_samples=MAX_SAMPLES, max_header_bytes=MAX_HEADER_BYTES)


def _temporal_coverage(count: int, fft_size: int, starts: list[int], rate: int) -> dict:
    covered = end = largest_gap = 0
    for start in starts:
        largest_gap = max(largest_gap, start - end)
        covered += max(0, start + fft_size - max(start, end))
        end = max(end, start + fft_size)
    largest_gap = max(largest_gap, count - end)
    return dict(capture_duration_s=count / rate, energy_screened_samples=count,
                energy_coverage_fraction=1.0, fft_unique_samples=covered,
                fft_coverage_fraction=covered / count, max_unanalyzed_gap_samples=largest_gap,
                max_unanalyzed_gap_s=largest_gap / rate, fft_window_duration_s=fft_size / rate,
                frame_starts_samples=starts, frame_start_offsets_s=[start / rate for start in starts],
                waterfall_rows_uniform_time=len({right - left for left, right in zip(starts, starts[1:])}) <= 1)


def spectrum(samples: Sequence[complex], sample_rate_hz: int, center_hz: int, fft_size: int) -> dict:
    if fft_size < 256 or fft_size > 65536 or fft_size & (fft_size - 1):
        raise ValueError('fft_size must be a power of two from 256 to 65536')
    if not 0 < len(samples) <= MAX_SAMPLES:
        raise ValueError(f'Capture must contain 1 to {MAX_SAMPLES} complex samples')
    if sample_rate_hz <= 0 or center_hz <= 0:
        raise ValueError('sample_rate_hz and center_hz must be positive')
    starts, selection = _select_frames(samples, fft_size)
    window = _hann(fft_size)
    coherent = sum(window) / fft_size
    rows = []
    for start in starts:
        frame = samples[start:start + fft_size]
        transformed = _fft([sample * window[i] / FULL_SCALE for i, sample in enumerate(frame)])
        shifted = transformed[fft_size // 2:] + transformed[:fft_size // 2]
        rows.append([20.0 * math.log10(max(abs(bin_value) / (fft_size * coherent), 1e-12)) for bin_value in shifted])
    width = len(rows[0])
    median = [statistics.median(row[bin_index] for row in rows) for bin_index in range(width)]
    maximum = [max(row[bin_index] for row in rows) for bin_index in range(width)]
    peak_bin = max(range(width), key=median.__getitem__)
    max_peak_bin = max(range(width), key=maximum.__getitem__)
    bin_hz = sample_rate_hz / fft_size
    frequencies = [center_hz + (index - fft_size // 2) * bin_hz for index in range(width)]
    return dict(frequencies_hz=frequencies, median_dbfs=median, max_dbfs=maximum, rows_dbfs=rows,
                peak_hz=frequencies[peak_bin], peak_dbfs=median[peak_bin], frames=len(rows), bin_hz=bin_hz,
                max_peak_hz=frequencies[max_peak_bin], max_peak_dbfs=maximum[max_peak_bin],
                temporal_coverage=_temporal_coverage(len(samples), fft_size, starts, sample_rate_hz),
                frame_selection=selection)


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
                max_peak_hz=result['max_peak_hz'], max_peak_dbfs=round(result['max_peak_dbfs'], 3),
                temporal_coverage=result['temporal_coverage'], frame_selection=result['frame_selection'],
                detection_limitations=[
                    'Whole-capture energy screening is not whole-capture FFT coverage.',
                    'Weak, sub-block, or constant-energy frequency changes may evade energy selection.',
                    'A high duty cycle can raise the baseline and hide activity; no calibrated detection threshold.',
                    'Only the strongest elevated-energy intervals fit the priority frame budget.',
                    'One FFT per prioritized interval does not characterize its entire duration or bandwidth.',
                    'Hann weighting suppresses frame edges; FFT coverage counts window spans, not equal sensitivity.',
                    'Median and maximum spectra describe selected frames, not time-weighted occupancy or all-sample peaks.',
                    'Waterfall rows are chronological selected frames; use offsets for unequal time gaps.',
                    'Sample offsets use the declared sample rate; no hardware acquisition or host-clock accuracy is proven.'
                ],
                power_units='dBFS', rf_calibrated=False, physical_bound_proven=False,
                hardware_acquisition_established=False, host_clock_timestamping_established=False,
                scope='dBFS of a finite I/Q capture; not calibrated RF power and not a QPC timestamp',
                _plot=result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--fft-size', type=int, default=4096)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        capture = read_capture(args.capture, compact=True)
        summary = analyze(capture, args.fft_size)
        plot = summary.pop('_plot')
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / 'spectrum.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        with (args.output_dir / 'spectrum.csv').open('w', encoding='utf-8') as stream:
            stream.write('frequency_hz,median_dbfs,max_dbfs\n')
            for frequency, power, maximum in zip(plot['frequencies_hz'], plot['median_dbfs'], plot['max_dbfs']):
                stream.write(f'{frequency:.3f},{power:.6f},{maximum:.6f}\n')
        write_waterfall(args.output_dir / 'waterfall.ppm', plot['rows_dbfs'])
        print(json.dumps(dict(peak_hz=summary['peak_hz'], peak_dbfs=summary['peak_dbfs'], frames=summary['frames'],
                              max_peak_hz=summary['max_peak_hz'], max_peak_dbfs=summary['max_peak_dbfs'])))
        return 0
    except (OSError, ValueError, KeyError) as error:
        print(f'Spectrum rejected: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

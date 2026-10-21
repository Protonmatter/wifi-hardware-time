import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import csv
import math
import random
import struct
import tempfile
import unittest
from research.spectrum.analyze_iq import CAPTURE_SCHEMA, analyze, main, read_capture, write_capture, spectrum

FULL_SCALE = 32767
RATE = 2_048_000
FFT = 1024
CENTER = 5_180_000_000


def tone(bins: int, count: int, amplitude: float = 0.5):
    step = 2.0 * math.pi * bins / FFT
    pairs = []
    for index in range(count):
        angle = step * index
        pairs.append((int(round(amplitude * FULL_SCALE * math.cos(angle))),
                      int(round(amplitude * FULL_SCALE * math.sin(angle)))))
    return pairs


def burst_pairs(count, bursts, background=0.0):
    """Deterministic on-bin background plus (start, length, bin, amplitude) bursts."""
    for index in range(count):
        value = background * FULL_SCALE * complex(math.cos(2 * math.pi * 3 * index / FFT),
                                                  math.sin(2 * math.pi * 3 * index / FFT))
        for start, length, bin_index, amplitude in bursts:
            if start <= index < start + length:
                angle = 2 * math.pi * bin_index * index / FFT
                value += amplitude * FULL_SCALE * complex(math.cos(angle), math.sin(angle))
        yield round(value.real), round(value.imag)


class SpectrumTests(unittest.TestCase):
    def capture(self, pairs, *, compact=False, **header):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'capture.iq'
        write_capture(path, pairs, sample_rate_hz=RATE, center_hz=CENTER, **header)
        return read_capture(path, compact=compact)

    def test_on_bin_tone_lands_on_its_frequency(self):
        capture = self.capture(tone(10, FFT * 2), qpc_start=1000, qpc_hz=10_000_000, chip='WCN7850')
        summary = analyze(capture, FFT)
        self.assertEqual(summary['peak_hz'], CENTER + 10 * RATE / FFT)
        self.assertAlmostEqual(summary['peak_dbfs'], 20.0 * math.log10(0.5), delta=0.4)
        self.assertFalse(summary['rf_calibrated'])
        self.assertFalse(summary['physical_bound_proven'])
        self.assertEqual(summary['chip'], 'WCN7850')
        self.assertEqual(summary['qpc_start'], 1000)

    def test_negative_frequency_tone(self):
        capture = self.capture(tone(-15, FFT))
        self.assertEqual(analyze(capture, FFT)['peak_hz'], CENTER - 15 * RATE / FFT)

    def test_short_burst_between_uniform_frames_is_visible(self):
        # Old starts near this interval are 8192 and 16896; neither sees 12000..12300.
        capture = self.capture(burst_pairs(FFT * 256, [(12000, 300, 37, 0.7)], 0.01))
        summary = analyze(capture, FFT)
        plot = summary['_plot']
        self.assertGreater(max(row[FFT // 2 + 37] for row in plot['rows_dbfs']), -20)
        self.assertIn('max_dbfs', plot)
        self.assertGreater(plot['max_dbfs'][FFT // 2 + 37], -20)
        self.assertLess(plot['median_dbfs'][FFT // 2 + 37], -60)
        # One priority interval should leave 31 distributed background frames.
        self.assertLessEqual(summary['temporal_coverage']['max_unanalyzed_gap_samples'], len(capture['samples']) / 30)

    def test_clean_tone_and_silence_do_not_report_energy_bursts(self):
        for amplitude in (0.0, 0.02, 0.5):
            with self.subTest(amplitude=amplitude):
                summary = analyze(self.capture(tone(3, FFT * 64 + 19, amplitude)), FFT)
                self.assertIn('frame_selection', summary)
                self.assertEqual(summary['frame_selection']['candidate_intervals'], 0)
                self.assertEqual(summary['temporal_coverage']['energy_coverage_fraction'], 1.0)
                starts = summary['temporal_coverage']['frame_starts_samples']
                gaps = [right - left for left, right in zip(starts, starts[1:])]
                self.assertLessEqual(max(gaps) - min(gaps), 1)
                if amplitude:
                    self.assertAlmostEqual(summary['peak_dbfs'], 20 * math.log10(amplitude), delta=0.1)

    def test_coverage_counts_union_and_trailing_samples(self):
        # Three half-hop frames cover exactly 2048 samples, not 3072.
        summary = analyze(self.capture(tone(3, 2048)), FFT)
        self.assertIn('temporal_coverage', summary)
        coverage = summary['temporal_coverage']
        self.assertEqual(coverage['fft_unique_samples'], 2048)
        self.assertEqual(coverage['fft_coverage_fraction'], 1)
        self.assertEqual(coverage['max_unanalyzed_gap_samples'], 0)
        self.assertTrue(coverage['waterfall_rows_uniform_time'])
        for count in (FFT, FFT + 1, FFT * 16 + 7, FFT * 64 + 17):
            with self.subTest(count=count):
                result = analyze(self.capture(tone(3, count)), FFT)
                coverage = result['temporal_coverage']
                starts = coverage['frame_starts_samples']
                self.assertLessEqual(len(starts), 32)
                self.assertEqual(starts, sorted(set(starts)))
                self.assertEqual(starts[0], 0)
                self.assertEqual(starts[-1] + FFT, count)
                self.assertEqual(coverage['energy_screened_samples'], count)
                covered = set()
                for start in starts:
                    covered.update(range(start, start + FFT))
                self.assertEqual(coverage['fft_unique_samples'], len(covered))
                self.assertAlmostEqual(coverage['fft_coverage_fraction'], len(covered) / count)
                ordered = sorted(covered)
                largest_gap = max(b - a - 1 for a, b in zip([-1] + ordered, ordered + [count]))
                self.assertEqual(coverage['max_unanalyzed_gap_samples'], largest_gap)

    def test_final_partial_screening_block_can_select_a_burst(self):
        count = FFT * 64 + 17
        summary = analyze(self.capture(burst_pairs(count, [(count - 17, 17, -21, 0.8)])), FFT)
        self.assertIn('frame_selection', summary)
        self.assertEqual(summary['frame_selection']['candidate_intervals'], 1)
        self.assertEqual(summary['frame_selection']['selected_intervals'], 1)
        self.assertEqual(summary['temporal_coverage']['energy_screened_samples'], count)

    def test_multiple_narrowband_bursts_survive_with_frequency_identity(self):
        capture = self.capture(burst_pairs(FFT * 256,
            [(12000, 2048, 37, 0.6), (42000, 2048, -43, 0.4)], 0.01))
        result = analyze(capture, FFT)
        self.assertIn('max_dbfs', result['_plot'])
        for bin_index, amplitude in ((37, 0.6), (-43, 0.4)):
            self.assertAlmostEqual(result['_plot']['max_dbfs'][FFT // 2 + bin_index],
                                   20 * math.log10(amplitude), delta=0.3)
        self.assertEqual(result['frame_selection']['candidate_intervals'], 2)
        self.assertEqual(result['frame_selection']['omitted_intervals'], 0)

    def test_narrowband_burst_over_seeded_noise_is_visible(self):
        rng = random.Random(7800)
        pairs = [(round(rng.gauss(0, 100)), round(rng.gauss(0, 100))) for _ in range(FFT * 128)]
        quiet = analyze(self.capture(pairs), FFT)
        self.assertEqual(quiet['frame_selection']['candidate_intervals'], 0)
        burst = tone(-39, FFT * 2, 0.3)
        for index, (i, q) in enumerate(burst, 12000):
            pairs[index] = (pairs[index][0] + i, pairs[index][1] + q)
        active = analyze(self.capture(pairs), FFT)
        self.assertEqual(active['frame_selection']['candidate_intervals'], 1)
        self.assertAlmostEqual(active['_plot']['max_dbfs'][FFT // 2 - 39],
                               20 * math.log10(0.3), delta=0.2)

    def test_bursts_across_screening_boundaries_and_fft_sizes(self):
        for fft_size in (256, 4096, 65536):
            for shift in (-3, 0, 3):
                with self.subTest(fft_size=fft_size, shift=shift):
                    count = fft_size * 40 + 13
                    start = fft_size * 7 + fft_size // 4 + shift
                    samples = [0j] * count
                    for index in range(start, start + fft_size // 8):
                        angle = 2 * math.pi * 17 * index / fft_size
                        samples[index] = FULL_SCALE * 0.7 * complex(math.cos(angle), math.sin(angle))
                    result = spectrum(samples, RATE, CENTER, fft_size)
                    self.assertGreater(result['max_dbfs'][fft_size // 2 + 17], -25)
                    self.assertEqual(result['frame_selection']['candidate_intervals'], 1)
                    self.assertEqual(result['temporal_coverage']['energy_screened_samples'], count)
                    self.assertLessEqual(result['frames'], 32)

    def test_stronger_late_burst_displaces_weaker_priority_candidate(self):
        bursts = [(4096 + index * 4096, 512, 37, 0.1) for index in range(20)]
        bursts.append((120000, 1024, -41, 0.8))
        summary = analyze(self.capture(burst_pairs(FFT * 256, bursts)), FFT)
        self.assertEqual(summary['frame_selection']['candidate_intervals'], 21)
        self.assertEqual(summary['frame_selection']['omitted_intervals'], 5)
        self.assertAlmostEqual(summary['_plot']['max_dbfs'][FFT // 2 - 41],
                               20 * math.log10(0.8), delta=1.0)

    def test_invalid_direct_analysis_inputs_are_rejected(self):
        for fft_size in (0, 255, 257, 131072):
            with self.subTest(fft_size=fft_size), self.assertRaises(ValueError):
                spectrum([0j] * FFT, RATE, CENTER, fft_size)
        for rate, center in ((0, CENTER), (RATE, 0), (-1, CENTER)):
            with self.subTest(rate=rate, center=center), self.assertRaises(ValueError):
                spectrum([0j] * FFT, rate, center, FFT)
        for samples in ([], [0j] * (FFT - 1)):
            with self.assertRaises(ValueError):
                spectrum(samples, RATE, CENTER, FFT)

    def test_int16_extremes_and_negative_index_survive_compact_read(self):
        capture = self.capture([(-32768, 32767), (32767, -32768), (0, -1)])
        self.assertIsInstance(capture['samples'], list)
        compact = self.capture([(-32768, 32767), (32767, -32768), (0, -1)], compact=True)
        self.assertEqual(list(compact['samples']), capture['samples'])
        self.assertEqual(compact['samples'][-1], -1j)
        self.assertEqual(compact['samples'][::-1], capture['samples'][::-1])
        capture['samples'].append(1j)
        self.assertEqual(capture['samples'].pop(), 1j)
        self.assertEqual(list(capture['samples']), [complex(-32768, 32767), complex(32767, -32768), -1j])
        self.assertEqual(capture['samples'][-1], -1j)
        self.assertEqual(capture['samples'][::-1], [-1j, complex(32767, -32768), complex(-32768, 32767)])
        with self.assertRaises(IndexError):
            _ = capture['samples'][3]

    def test_candidate_overflow_is_bounded_and_deterministic(self):
        bursts = [(4096 + index * 4096, 512, 37, 0.5) for index in range(40)]
        capture = self.capture(burst_pairs(FFT * 256, bursts))
        result = analyze(capture, FFT)
        self.assertIn('frame_selection', result)
        selection = result['frame_selection']
        self.assertEqual(selection['candidate_intervals'], 40)
        self.assertEqual(selection['selected_intervals'], 16)
        self.assertEqual(selection['omitted_intervals'], 24)
        self.assertLessEqual(result['frames'], 32)
        again = analyze(capture, FFT)
        self.assertEqual(result, again)

    def test_constant_energy_frequency_change_remains_explicitly_unqualified(self):
        # Equal amplitude changes frequency; broadband energy screening cannot see it.
        pairs = tone(3, FFT * 256, 0.5)
        pairs[12000:12300] = tone(37, 300, 0.5)
        summary = analyze(self.capture(pairs), FFT)
        self.assertIn('detection_limitations', summary)
        self.assertTrue(any('constant-energy' in item for item in summary['detection_limitations']))
        self.assertEqual(summary['frame_selection']['candidate_intervals'], 0)
        self.assertLess(summary['_plot']['max_dbfs'][FFT // 2 + 37], -60)
        self.assertFalse(summary['rf_calibrated'])
        self.assertFalse(summary['physical_bound_proven'])

    def test_one_second_20mhz_counterexample(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'one-second.iq'
        header = b'schema: wht/iq-capture-v1\nsample_rate_hz: 20000000\ncenter_hz: 5180000000\n\n'
        # Sparse synthetic silence avoids materializing 20 million Python objects.
        with path.open('wb') as stream:
            stream.write(header)
            stream.seek(len(header) + 20_000_000 * 4 - 1)
            stream.write(b'\0')
            stream.seek(len(header) + 200000 * 4)
            for index in range(5000):
                angle = 2 * math.pi * 73 * index / 4096
                stream.write(struct.pack('<hh', round(0.5 * FULL_SCALE * math.cos(angle)),
                                         round(0.5 * FULL_SCALE * math.sin(angle))))
        summary = analyze(read_capture(path, compact=True), 4096)
        self.assertGreater(max(row[2048 + 73] for row in summary['_plot']['rows_dbfs']), -8)
        self.assertEqual(summary['temporal_coverage']['energy_screened_samples'], 20_000_000)
        self.assertEqual(summary['temporal_coverage']['capture_duration_s'], 1.0)

    def test_resource_limits_reject_oversized_capture_and_header(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'too-large.iq'
        path.write_bytes(b'x' * 4097 + b'\n\n')
        with self.assertRaisesRegex(ValueError, 'header'):
            read_capture(path)
        header = b'schema: wht/iq-capture-v1\nsample_rate_hz: 10\ncenter_hz: 10\n\n'
        with path.open('wb') as stream:
            stream.write(header)
            stream.seek(len(header) + 20_000_001 * 4 - 1)
            stream.write(b'\0')
        with self.assertRaisesRegex(ValueError, '20000000'):
            read_capture(path)

    def test_short_capture_and_bad_header_are_rejected(self):
        capture = self.capture(tone(1, 100))
        with self.assertRaises(ValueError):
            analyze(capture, FFT)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'bad.iq'
        path.write_bytes(b'schema: wht/iq-capture-v1\nsample_rate_hz: 0\n\n')
        with self.assertRaises(ValueError):
            read_capture(path)
        path.write_bytes(b'schema: other\nsample_rate_hz: 10\ncenter_hz: 10\n\n')
        with self.assertRaisesRegex(ValueError, CAPTURE_SCHEMA):
            read_capture(path)

    def test_cli_writes_summary_csv_and_waterfall(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        capture = root / 'capture.iq'
        write_capture(capture, tone(4, FFT), sample_rate_hz=RATE, center_hz=CENTER)
        code = main([str(capture), '--fft-size', str(FFT), '--output-dir', str(root / 'out')])
        self.assertEqual(code, 0)
        summary = json.loads((root / 'out' / 'spectrum.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['peak_hz'], CENTER + 4 * RATE / FFT)
        self.assertIn('temporal_coverage', summary)
        with (root / 'out' / 'spectrum.csv').open(encoding='utf-8') as stream:
            bins = list(csv.DictReader(stream))
        self.assertEqual(len(bins), FFT)
        self.assertAlmostEqual(float(bins[FFT // 2 + 4]['max_dbfs']), -6.0206, delta=0.01)
        waterfall = (root / 'out' / 'waterfall.ppm').read_bytes()
        header = f'P6\n{FFT} {summary["frames"]}\n255\n'.encode('ascii')
        self.assertTrue(waterfall.startswith(header))
        self.assertEqual(len(waterfall) - len(header), FFT * summary['frames'] * 3)


if __name__ == '__main__':
    unittest.main()

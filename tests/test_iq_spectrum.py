import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import math
import tempfile
import unittest
from research.spectrum.analyze_iq import CAPTURE_SCHEMA, analyze, main, read_capture, write_capture

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


class SpectrumTests(unittest.TestCase):
    def capture(self, pairs, **header):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'capture.iq'
        write_capture(path, pairs, sample_rate_hz=RATE, center_hz=CENTER, **header)
        return read_capture(path)

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
        self.assertTrue((root / 'out' / 'spectrum.csv').read_text(encoding='utf-8').startswith('frequency_hz,'))
        waterfall = (root / 'out' / 'waterfall.ppm').read_bytes()
        self.assertTrue(waterfall.startswith(f'P6\n{FFT} '.encode('ascii')))


if __name__ == '__main__':
    unittest.main()

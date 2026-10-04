"""Offline rejection checks and optional owned Windows image fixtures."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.adapters.inspect_windows_bss_time import (
    IMAGE_HASHES, MAX_IMAGE_BYTES, inspect_image, inspect_images, read_image,
)

SCRIPT = Path(__file__).resolve().parents[1] / 'research/adapters/inspect_windows_bss_time.py'


class WindowsBssTimeTests(unittest.TestCase):
    def test_unknown_images_rejected(self):
        for name in IMAGE_HASHES:
            with self.subTest(image=name), self.assertRaisesRegex(ValueError, 'qualified build'):
                inspect_image(b'not a Windows image', name)

    def test_unsupported_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported image'):
            inspect_image(b'', 'other')

    def test_oversized_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'large.bin'
            with path.open('wb') as stream:
                stream.truncate(MAX_IMAGE_BYTES + 1)
            with self.assertRaisesRegex(ValueError, 'inspection bound'):
                read_image(path)

    def test_cli_does_not_replace_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'existing.json'
            output.write_bytes(b'preserve me')
            result = subprocess.run(
                [sys.executable, str(SCRIPT), '--wificx', 'missing.sys',
                 '--wlanmsm', 'missing.dll', '--output', str(output)],
                capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Output already exists', result.stderr)
            self.assertEqual(output.read_bytes(), b'preserve me')

    def test_cli_rejects_unknown_file_without_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'unknown.bin'
            output = Path(directory) / 'new.json'
            source.write_bytes(b'unknown')
            result = subprocess.run(
                [sys.executable, str(SCRIPT), '--wificx', str(source),
                 '--wlanmsm', str(source), '--output', str(output)],
                capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())

    @unittest.skipUnless(os.environ.get('WIFI_TIME_WIFICX_FIXTURE') and
                         os.environ.get('WIFI_TIME_WLANMSM_FIXTURE'),
                         'Owned Windows image fixtures not configured')
    def test_owned_ranges_and_evidence_limits(self):
        cx = read_image(Path(os.environ['WIFI_TIME_WIFICX_FIXTURE']))
        msm = read_image(Path(os.environ['WIFI_TIME_WLANMSM_FIXTURE']))
        result = inspect_images(cx, msm)
        self.assertFalse(result['runtime_path_qualified'])
        self.assertFalse(result['hardware_pair_export_qualified'])
        self.assertFalse(result['live_capture_performed'])
        for image in result['images']:
            self.assertEqual(image['machine'], '0xaa64')
            self.assertEqual(image['sha256'], IMAGE_HASHES[image['image']])
            self.assertNotIn('path', image)
        self.assertEqual(len(result['images'][0]['ranges']), 13)
        self.assertEqual(result['images'][1]['ranges'][0]['start_rva'], '0x2eb68')
        with self.assertRaisesRegex(ValueError, 'qualified build'):
            inspect_image(cx[:-1] + bytes([cx[-1] ^ 1]), 'wificx')


if __name__ == '__main__':
    unittest.main()

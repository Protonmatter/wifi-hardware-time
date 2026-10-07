import sys
from pathlib import Path
# Resolve repository packages when this file is used as a direct CLI.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest
from research.clock_models.bracket_bound import Window, sliding_bounds
from research.clock_models.beacon_consistency import Beacon, check_beacons

HZ = 10_000_000


def spans():
    windows = [Window(9_000_000 + i * 2_000_000 + 200, 10_000_000 + i * 20_000_000, 10_005_000 + i * 20_000_000)
               for i in range(10)]
    return sliding_bounds(windows, HZ)


class BeaconTests(unittest.TestCase):
    def test_past_beacon_passes(self):
        result = check_beacons([Beacon(50_000_000, 9_000_000 + 4_000_000 - 50_000)], spans())
        self.assertEqual((result['checked'], result['violations']), (1, 0))

    def test_beacon_ahead_of_station_tsf_is_a_violation(self):
        result = check_beacons([Beacon(50_000_000, 9_000_000 + 4_000_000 + 5_000)], spans())
        self.assertEqual(result['violations'], 1)

    def test_beacon_outside_spans_is_unchecked(self):
        result = check_beacons([Beacon(1, 0)], spans())
        self.assertEqual((result['checked'], result['unchecked']), (0, 1))


if __name__ == '__main__':
    unittest.main()

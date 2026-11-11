#!/usr/bin/env python3
"""Offline evidence guards for measured resolution; never infer pixels from labels."""
import unittest
from quality_upgrades import height, valid_measured_height


class Stage3QualityMeasurementTests(unittest.TestCase):
    def test_only_positive_integer_measurements_are_accepted(self):
        self.assertEqual(valid_measured_height(1080), 1080)
        self.assertEqual(valid_measured_height(720), 720)
        for invalid in (None, 0, -1, True, False, "1080", 1080.5, {}, []):
            with self.subTest(invalid=repr(invalid)):
                self.assertIsNone(valid_measured_height(invalid))

    def test_quality_labels_are_not_measurements(self):
        self.assertEqual(height("Example FHD"), 1080)
        self.assertIsNone(valid_measured_height("1080"))
        self.assertIsNone(height("Unknown quality"))


if __name__ == "__main__":
    unittest.main()

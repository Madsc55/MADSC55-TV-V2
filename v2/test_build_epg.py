#!/usr/bin/env python3
"""Offline EPG mapping acceptance: no guessed programme ownership."""
import unittest
from collections import defaultdict
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from build_epg import norm, select_epg_source, programme_in_window


class EPGBuilderMatchingTests(unittest.TestCase):
    def setUp(self):
        self.names = defaultdict(set)
        self.names[norm("Shared TV")].update({"channel.tr", "channel.az"})
        self.names[norm("Unique Station")].add("unique.tr")
        self.schedules = {"channel.tr": [1, 2, 3], "channel.az": [1], "unique.tr": [1]}

    def test_ambiguous_normalized_name_is_not_assigned(self):
        self.assertEqual(select_epg_source("", "Shared TV", "Shared TV", self.names, self.schedules),
                         (None, True))

    def test_exact_tvg_id_takes_precedence_over_name_collision(self):
        self.assertEqual(select_epg_source("channel.az", "Shared TV", "Shared TV",
                                           self.names, self.schedules), ("channel.az", False))

    def test_unique_name_may_be_matched_as_hint(self):
        self.assertEqual(select_epg_source("", "Unique Station", "Unique Station",
                                           self.names, self.schedules), ("unique.tr", False))

    def test_unknown_name_remains_unmatched(self):
        self.assertEqual(select_epg_source("", "Unknown", "Unknown",
                                           self.names, self.schedules), (None, False))

    def test_guide_export_uses_real_utc_offset(self):
        p = ET.Element("programme", start="20261113120000 +0300", stop="20261113130000 +0300")
        begin = datetime(2026, 11, 13, 8, 0, tzinfo=timezone.utc)
        end = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
        self.assertTrue(programme_in_window(p, begin, end))

    def test_guide_export_rejects_invalid_intervals(self):
        begin = datetime(2026, 11, 13, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 11, 14, 0, 0, tzinfo=timezone.utc)
        invalid = [
            ("20261113120000 +1460", "20261113130000 +1460"),
            ("20261113130000 +0000", "20261113120000 +0000"),
            ("20261113120000 +0000", "20261113120000 +0000"),
            ("20261113120000 +0000", ""),
        ]
        for start, stop in invalid:
            with self.subTest(start=start, stop=stop):
                p = ET.Element("programme", start=start, stop=stop)
                self.assertFalse(programme_in_window(p, begin, end))

    def test_conflicting_tvg_name_and_display_are_ambiguous(self):
        self.assertEqual(select_epg_source("", "Unique Station", "Shared TV",
                                           self.names, self.schedules), (None, True))


if __name__ == "__main__":
    unittest.main()

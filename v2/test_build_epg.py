#!/usr/bin/env python3
"""Offline EPG mapping acceptance: no guessed programme ownership."""
import unittest
from collections import defaultdict
from build_epg import norm, select_epg_source


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

    def test_conflicting_tvg_name_and_display_are_ambiguous(self):
        self.assertEqual(select_epg_source("", "Unique Station", "Shared TV",
                                           self.names, self.schedules), (None, True))


if __name__ == "__main__":
    unittest.main()

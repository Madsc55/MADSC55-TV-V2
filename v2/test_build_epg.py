#!/usr/bin/env python3
"""Offline EPG mapping acceptance: no guessed programme ownership."""
import io
import unittest
from collections import defaultdict
from unittest.mock import patch
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from build_epg import norm, select_epg_source, programme_in_window, ingest_xmltv_feed, download


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


    def _feed(self, ids, programme_ids):
        root = ET.Element("tv")
        for cid in ids:
            ET.SubElement(root, "channel", id=cid)
        for cid in programme_ids:
            ET.SubElement(root, "programme", channel=cid, start="20261113000000 +0000",
                          stop="20261113010000 +0000")
        return root

    def test_distinct_declared_channel_ids_remain_eligible(self):
        channels, schedules, collisions = {}, defaultdict(list), set()
        counts = ingest_xmltv_feed(self._feed(["one.tr"], ["one.tr", "undeclared.tr"]),
                                   channels, schedules, collisions)
        self.assertEqual(counts["accepted_programmes"], 1)
        self.assertEqual(counts["rejected_programmes"], 1)
        self.assertEqual(set(channels), {"one.tr"})
        self.assertEqual(len(schedules["one.tr"]), 1)
        self.assertNotIn("undeclared.tr", schedules)
        self.assertFalse(collisions)

    def test_same_id_from_two_feeds_is_not_assigned_to_either_publisher(self):
        channels, schedules, collisions = {}, defaultdict(list), set()
        ingest_xmltv_feed(self._feed(["shared.tr"], ["shared.tr"]),
                          channels, schedules, collisions)
        second = ingest_xmltv_feed(self._feed(["shared.tr", "unique.az"],
                                               ["shared.tr", "unique.az"]),
                                   channels, schedules, collisions)
        self.assertEqual(second["conflicting_ids"], 1)
        self.assertEqual(second["accepted_programmes"], 1)
        self.assertIn("shared.tr", collisions)
        self.assertNotIn("shared.tr", channels)
        self.assertNotIn("shared.tr", schedules)
        self.assertEqual(len(schedules["unique.az"]), 1)
        self.assertEqual(select_epg_source("shared.tr", "Shared", "Shared",
                                           defaultdict(set), schedules), (None, False))

    def test_duplicate_ids_within_single_feed_are_rejected(self):
        channels, schedules, collisions = {}, defaultdict(list), set()
        result = ingest_xmltv_feed(self._feed(["dup.tr", "dup.tr"], ["dup.tr"]),
                                   channels, schedules, collisions)
        self.assertEqual(result["conflicting_ids"], 1)
        self.assertEqual(result["accepted_programmes"], 0)
        self.assertIn("dup.tr", collisions)
        self.assertNotIn("dup.tr", schedules)

    def test_xmltv_dtd_and_internal_entities_are_rejected(self):
        malicious = b'<!DOCTYPE tv [<!ENTITY fake "broadcast">]><tv></tv>'
        with patch("build_epg.urllib.request.urlopen", return_value=io.BytesIO(malicious)):
            with self.assertRaisesRegex(ValueError, "DTD"):
                download("https://epg.example.net/guide.xml")

if __name__ == "__main__":
    unittest.main()

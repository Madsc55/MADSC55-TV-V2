#!/usr/bin/env python3
"""Offline EPG mapping acceptance: no guessed programme ownership."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import timedelta
import build_epg
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

    def test_candidate_epg_is_separate_and_preserves_protected_epg(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "v2").mkdir()
            (root / "v2/epg_sources.json").write_text(json.dumps({
                "sources": ["https://epg.example.org/guide.xml?private=do-not-publish"]
            }))
            live = root / "live.m3u8"
            live.write_text('#EXTM3U\n#EXTINF:-1 tvg-id="unique.tr" tvg-name="Unique Station",Unique Station\nhttps://example.org/live.m3u8\n')
            protected = root / "madsc-epg.xml"
            protected.write_bytes(b"PROTECTED-EMPTY-BASELINE")
            now = datetime.now(timezone.utc)
            fmt = lambda t: t.strftime("%Y%m%d%H%M%S") + " +0000"
            xml = ET.Element("tv")
            channel = ET.SubElement(xml, "channel", id="unique.tr")
            ET.SubElement(channel, "display-name").text = "Unique Station"
            programme = ET.SubElement(xml, "programme", channel="unique.tr",
                                      start=fmt(now-timedelta(minutes=30)),
                                      stop=fmt(now+timedelta(minutes=30)))
            ET.SubElement(programme, "title").text = "Real guide fixture"
            with (patch.object(build_epg, "ROOT", root),
                  patch.object(build_epg, "OUT", protected),
                  patch.object(build_epg, "PLAYLIST", live),
                  patch.object(build_epg, "download", return_value=xml) as download,
                  patch.object(sys, "argv", ["build_epg.py", "--candidate-only"])):
                build_epg.main()
                self.assertEqual(download.call_count, 1)
                candidate = root / "v2/reports/stage-a-epg-candidate.xml"
                self.assertEqual(protected.read_bytes(), b"PROTECTED-EMPTY-BASELINE")
                self.assertEqual(len(ET.parse(candidate).findall("programme")), 1)
                report = json.loads((root / "v2/reports/stage-a-epg-build-report.json").read_text())
                self.assertTrue(report["candidate_only"])
                self.assertEqual(report["status"], "EPG_CANDIDATE_FOR_REVIEW")
                self.assertNotIn("private=do-not-publish", json.dumps(report))
                # Exclusive candidate creation must never overwrite evidence.
                prior = candidate.read_bytes()
                with self.assertRaises(SystemExit):
                    build_epg.main()
                self.assertEqual(candidate.read_bytes(), prior)

    def test_name_only_epg_link_stays_review_hint_not_exact_id(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "v2").mkdir()
            (root / "v2/epg_sources.json").write_text(json.dumps({
                "sources": ["https://epg.example.org/tr.xml"]}))
            live = root / "live.m3u8"
            live.write_text('#EXTM3U\n#EXTINF:-1 tvg-id="unconfirmed.tr" tvg-name="Unique Station",Unique Station\nhttps://example.org/stream.m3u8\n')
            protected = root / "madsc-epg.xml"
            protected.write_bytes(b"DO_NOT_WRITE")
            now = datetime.now(timezone.utc)
            fmt = lambda t: t.strftime("%Y%m%d%H%M%S") + " +0000"
            xml = ET.Element("tv")
            ch = ET.SubElement(xml, "channel", id="official.tr")
            ET.SubElement(ch, "display-name").text = "Unique Station"
            p = ET.SubElement(xml, "programme", channel="official.tr",
                              start=fmt(now-timedelta(minutes=30)),
                              stop=fmt(now+timedelta(minutes=30)))
            ET.SubElement(p, "title").text = "Valid schedule, unproven identity"
            with (patch.object(build_epg, "ROOT", root),
                  patch.object(build_epg, "OUT", protected),
                  patch.object(build_epg, "PLAYLIST", live),
                  patch.object(build_epg, "download", return_value=xml),
                  patch.object(sys, "argv", ["build_epg.py", "--candidate-only"])):
                build_epg.main()
            candidate = ET.parse(root / "v2/reports/stage-a-epg-candidate.xml")
            channel = candidate.find("channel")
            self.assertEqual(channel.get("id"), "unconfirmed.tr")
            self.assertEqual(channel.get("madsc-match-method"), "name-hint")
            report = json.loads((root / "v2/reports/stage-a-epg-build-report.json").read_text())
            self.assertEqual(report["exact_id_matched_entries"], 0)
            self.assertEqual(report["name_hint_matched_entries"], 1)
            self.assertEqual(report["verified_exact_id_channels"], 0)
            self.assertEqual(protected.read_bytes(), b"DO_NOT_WRITE")

    def test_candidate_epg_fails_closed_without_current_programmes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "v2").mkdir()
            (root / "v2/epg_sources.json").write_text(json.dumps({
                "sources": ["https://epg.example.org/guide.xml"]}))
            live = root / "live.m3u8"
            live.write_text('#EXTM3U\n#EXTINF:-1 tvg-id="unique.tr",Unique Station\nhttps://example.org/live.m3u8\n')
            protected = root / "madsc-epg.xml"
            protected.write_bytes(b"PROTECTED")
            xml = ET.Element("tv")
            ET.SubElement(xml, "channel", id="unique.tr")
            ET.SubElement(xml, "programme", channel="unique.tr",
                          start="20200101000000 +0000", stop="20200101010000 +0000")
            with (patch.object(build_epg, "ROOT", root),
                  patch.object(build_epg, "OUT", protected),
                  patch.object(build_epg, "PLAYLIST", live),
                  patch.object(build_epg, "download", return_value=xml),
                  patch.object(sys, "argv", ["build_epg.py", "--candidate-only"])):
                with self.assertRaises(SystemExit):
                    build_epg.main()
            self.assertEqual(protected.read_bytes(), b"PROTECTED")
            self.assertFalse((root / "v2/reports/stage-a-epg-candidate.xml").exists())

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

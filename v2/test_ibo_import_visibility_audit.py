#!/usr/bin/env python3
"""Offline tests for lossless IBO Player count visibility diagnostics."""
import unittest
from ibo_import_visibility_audit import audit


def row(group, name, url):
    return ('#EXTINF:-1 group-title="' + group + '",' + name +
            '\n' + url + '\n').encode("utf-8")


class IboImportVisibilityTests(unittest.TestCase):
    def test_reports_player_mismatch_without_removing_any_record(self):
        data = (b"#EXTM3U\n"
                + row("⭐ FAVORİLER (1)", "Favourite", "https://example.org/one.m3u8")
                + row("🌍 BELGESEL (2)", "Documentary A", "https://example.org/one.m3u8")
                + row("🌍 BELGESEL (2)", "Documentary B", "https://example.org/two.m3u8")
                + row("🗂️ YEDEKLER (1)", "Backup", "https://example.org/three.m3u8"))
        before = data[:]
        report = audit(data, {"BELGESEL": 1, "YEDEKLER": 1})
        self.assertEqual(data, before)
        self.assertEqual(report["total_file_records"], 4)
        documentary = report["categories"]["belgesel"]
        self.assertEqual(documentary["file_records"], 2)
        self.assertEqual(documentary["distinct_urls_inside_category"], 2)
        self.assertEqual(documentary["unaccounted_player_records"], 1)
        self.assertTrue(documentary["header_matches_records"])
        self.assertEqual(report["cross_category_url_groups"], 1)
        self.assertFalse(report["player_count_cause_verified"])
        self.assertEqual(report["malformed_records"], [])

    def test_wrong_header_count_is_separate_from_player_difference(self):
        data = b"#EXTM3U\n" + row("🌍 BELGESEL (19)", "Only one", "https://example.org/1")
        result = audit(data, {"BELGESEL": 0})["categories"]["belgesel"]
        self.assertEqual(result["file_records"], 1)
        self.assertFalse(result["header_matches_records"])
        self.assertEqual(result["unaccounted_player_records"], 1)

    def test_rejects_bad_observed_values(self):
        data = b"#EXTM3U\n" + row("🌍 BELGESEL (1)", "A", "https://example.org/1")
        with self.assertRaises(ValueError):
            audit(data, {"BELGESEL": -1})
        with self.assertRaises(ValueError):
            audit(data, {"BELGESEL": "18"})

    def test_colliding_metadata_identifies_candidates_without_claiming_player_behavior(self):
        data = (b"#EXTM3U\n"
                + ('#EXTINF:-1 tvg-name="TGRT BELGESEL" tvg-id="3915" '
                   'group-title="🌍 BELGESEL (2)",TGRT BELGESEL HD\n'
                   'https://example.org/hd.m3u8\n').encode("utf-8")
                + ('#EXTINF:-1 tvg-name="TGRT BELGESEL" tvg-id="3915" '
                   'group-title="🌍 BELGESEL (2)",TGRT BELGESEL SD\n'
                   'https://example.org/sd.m3u8\n').encode("utf-8"))
        report = audit(data)
        item = report["categories"]["belgesel"]
        self.assertEqual(item["file_records"], 2)
        self.assertEqual(item["distinct_urls_inside_category"], 2)
        self.assertEqual(item["metadata_repeated_tvg_name"]["groups"], 1)
        self.assertEqual(item["metadata_repeated_tvg_name"]["extra_records"], 1)
        self.assertEqual(item["metadata_repeated_tvg_id"]["groups"], 1)
        self.assertEqual(item["metadata_repeated_tvg_name"]["examples"],
                         [["TGRT BELGESEL HD", "TGRT BELGESEL SD"]])
        self.assertFalse(report["player_count_cause_verified"])
        self.assertFalse(report["metadata_repeats_are_ibo_parser_proof"])

    def test_blank_metadata_is_not_flagged_as_duplicate(self):
        data = (b"#EXTM3U\n"
                + row("🌍 BELGESEL (2)", "A", "https://example.org/a")
                + row("🌍 BELGESEL (2)", "B", "https://example.org/b"))
        info = audit(data)["categories"]["belgesel"]
        self.assertEqual(info["metadata_repeated_tvg_name"]["groups"], 0)
        self.assertEqual(info["metadata_repeated_tvg_id"]["groups"], 0)

    def test_identical_urls_inside_category_reported_but_never_removed(self):
        data = (b"#EXTM3U\n" +
                row("🌍 BELGESEL (2)", "A", "https://example.org/1") +
                row("🌍 BELGESEL (2)", "B", "https://example.org/1"))
        report = audit(data)["categories"]["belgesel"]
        self.assertEqual(report["file_records"], 2)
        self.assertEqual(report["repeated_urls_inside_category"], 1)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""One grouped offline test for named Turkish channel metadata search."""
import hashlib
import unittest
from channel_watchlist import canonical, report, NAMES

def playlist(*rows):
    return "#EXTM3U\n" + "".join(
        '#EXTINF:-1 tvg-id="' + tvg + '",' + name + "\n" + url + "\n"
        for tvg, name, url in rows
    )

class ChannelWatchlistTests(unittest.TestCase):
    def test_exact_name_candidates_are_found_without_automatic_av_promotion(self):
        url = "https://example.org/gunes.m3u8"
        src = playlist(("Gunes.tr", "Gunes TV", url),
                       ("Rec.tr", "Rec TV", "https://example.org/rec.m3u8"),
                       ("Other.tr", "Rec TV Extra", "https://example.org/other.m3u8"))
        summary = report([("approved_m3u", src)], "#EXTM3U\n")
        self.assertEqual([row["name"] for row in summary["channels"]], list(NAMES))
        a,b,c = summary["channels"]
        self.assertEqual(a["status"], "EXACT_METADATA_CANDIDATE_NOT_AV_VERIFIED")
        self.assertEqual(a["unique_candidate_url_sha256"],
                         [hashlib.sha256(url.encode()).hexdigest()])
        self.assertEqual(b["matched_source_ids"], ["approved_m3u"])
        self.assertEqual(c["status"], "NO_EXACT_SOURCE_METADATA")
        self.assertNotIn(url, str(summary))
        self.assertFalse(summary["av_verified"])
        self.assertFalse(summary["ibo_device_verified"])

    def test_dedup_between_sources_and_existing_metadata(self):
        url = "https://example.org/rec.m3u8"
        m3u = playlist(("r.tr", "Rec TV", url))
        d = report([("one", m3u), ("two", m3u)], m3u)
        rec = next(row for row in d["channels"] if row["name"] == "Rec TV")
        self.assertEqual(len(rec["unique_candidate_url_sha256"]), 1)
        self.assertEqual(rec["matched_source_ids"], ["one","two"])
        self.assertTrue(rec["already_in_scanned_development_snapshot"])

    def test_similar_or_unrelated_names_are_not_matched(self):
        d = report([("world", playlist(
            ("world", "Rec TV 2", "https://example.org/a.m3u8"),
            ("world", "Sun TV", "https://example.org/b.m3u8")
        ))], "#EXTM3U\n")
        self.assertEqual(len([x for x in d["channels"]
                              if x["status"] == "NO_EXACT_SOURCE_METADATA"]), 3)

    def test_case_and_turkish_spelling_only(self):
        self.assertEqual(canonical("  GÜNEŞ TV "), canonical("Gunes-TV"))
        self.assertNotEqual(canonical("Rec TV"), canonical("Rec TV +"))
        with self.assertRaises(ValueError):
            report([], "#EXTM3U\n", names=("Güneş TV", "Gunes-TV"))

if __name__ == "__main__":
    unittest.main()

import hashlib
import json
import unittest

from v2.yedekler_worldwide_crosswalk import build_crosswalk


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_playlist(rows):
    return ("#EXTM3U\n" + "".join(
        f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n'
        for group, name, url in rows
    )).encode("utf-8")


class WorldwideCrosswalkTests(unittest.TestCase):
    def setUp(self):
        self.urls = [f"https://fixture.example/{i}.m3u8" for i in range(1, 7)]
        self.archive = make_playlist([("YEDEKLER", f"Channel {i}", url)
                                      for i, url in enumerate(self.urls, 1)])
        self.main = make_playlist([
            ("YEDEKLER", "Channel 1", self.urls[0]),
            ("TÜRK ARŞİVİ", "Channel 2", self.urls[1]),
            ("YABANCI ARŞİVİ", "Channel 3", self.urls[2]),
            ("YEDEKLER", "Channel 4", self.urls[3]),
            ("ANA ARŞİV", "Channel 5", self.urls[4]),
            ("ANA ARŞİV", "Channel 6", self.urls[5]),
        ])
        self.state = {
            "source_sha256": hashlib.sha256(self.archive).hexdigest(),
            "total": 6,
            "status": {"1": "TEST", "2": "TURK", "3": "YABANCI", "4": "TEST"},
        }
        self.worldwide = {
            "unique_url_candidates": 3,
            "audio_video_decoded": 1,
            "spoken_language_verified": 0,
            "ibo_player_verified": False,
            "protected_main_playlist_modified": False,
            "candidates": [
                {"url_sha256": sha(self.urls[0]), "status": "VIDEO_AUDIO_DECODED",
                 "decoded": True, "audio": True, "video": True,
                 "evidence_origin": "CURRENT_RUN_FFPROBE_FFMPEG"},
                {"url_sha256": sha(self.urls[1]), "status": "VIDEO_AUDIO_DECODED",
                 "decoded": True, "audio": True, "video": True,
                 "evidence_origin": "PRIOR_RUN_HASH_ONLY_NOT_FRESH"},
                {"url_sha256": sha(self.urls[2]), "status": "PROBE_FAILED_HTTP_NOT_FOUND",
                 "decoded": False, "audio": False, "video": False,
                 "evidence_origin": "CURRENT_RUN_FFPROBE_FFMPEG"},
            ],
        }
        self.historical = {
            "historical_match_url_sha256": [sha(self.urls[0]), sha(self.urls[1])],
            "historical_decoded_url_sha256": [sha(self.urls[0])],
            "ibo_device_verified": False,
            "protected_playlist_modified": False,
        }

    def build(self, **kwargs):
        return build_crosswalk(
            self.archive, self.main, self.state, self.worldwide, self.historical,
            expected_archive_sha256=self.state["source_sha256"],
            expected_archive_total=6, expected_batch_size=4,
            expected_main_inventory={
                "YEDEKLER": 2, "ANA": 2, "TURK": 1,
                "YABANCI": 1, "OTHER": 0, "TOTAL": 6,
            }, expected_worldwide_count=3, expected_worldwide_av_count=1,
            **kwargs,
        )

    def test_exact_hash_crosswalk_separates_current_and_historical_evidence(self):
        summary, crosswalk = self.build()
        counts = summary["counts"]
        self.assertEqual(counts["archive_total"], 6)
        self.assertEqual(counts["worldwide_exact_hash_matches"], 3)
        self.assertEqual(counts["worldwide_not_found"], 3)
        self.assertEqual(counts["source_run_av_decoded"], 1)
        self.assertEqual(counts["prior_run_hash_only_matches"], 1)
        self.assertEqual(counts["matched_but_not_av_decoded"], 1)
        self.assertEqual(counts["historical_exact_hash_matches"], 2)
        self.assertEqual(counts["historical_av_decoded_matches"], 1)
        self.assertEqual(counts["current_yedekler_total"], 2)
        self.assertEqual(counts["current_yedekler_worldwide_matches"], 1)
        self.assertEqual(counts["current_yedekler_source_run_av_decoded"], 1)
        self.assertEqual(counts["current_yedekler_not_in_worldwide_report"], 1)
        self.assertFalse(summary["new_scan_started"])
        self.assertFalse(summary["playlist_written"])
        rendered = json.dumps({"summary": summary, "crosswalk": crosswalk})
        for url in self.urls:
            self.assertNotIn(url, rendered)
        self.assertEqual(len(crosswalk["entries"]), 6)

    def test_protected_copy_of_archive_url_is_preserved(self):
        # Canonical main intentionally contains 838 protected records whose
        # stream URLs also occur in the 18,074-category archive inventory.
        protected = make_playlist([("FAVORITES", "Protected copy", self.urls[0])])
        main_with_protected = self.main + protected.split(b"\\n", 1)[1]
        summary, crosswalk = build_crosswalk(
            self.archive, main_with_protected, self.state, self.worldwide, self.historical,
            expected_archive_sha256=self.state["source_sha256"],
            expected_archive_total=6, expected_batch_size=4,
            expected_main_inventory={
                "YEDEKLER": 2, "ANA": 2, "TURK": 1,
                "YABANCI": 1, "OTHER": 1, "TOTAL": 7,
            }, expected_worldwide_count=3, expected_worldwide_av_count=1)
        self.assertEqual(len(crosswalk["entries"]), 6)
        self.assertEqual(summary["main_inventory"]["OTHER"], 1)
        self.assertFalse(summary["playlist_written"])

    def test_rejects_duplicate_inside_archive_categories(self):
        duplicate = make_playlist([("ANA ARŞİV", "Duplicate record", self.urls[0])])
        duplicate_main = self.main + duplicate.split(b"\\n", 1)[1]
        with self.assertRaisesRegex(ValueError, "Duplicate URL hash within canonical archive"):
            build_crosswalk(
                self.archive, duplicate_main, self.state, self.worldwide, self.historical,
                expected_archive_sha256=self.state["source_sha256"],
                expected_archive_total=6, expected_batch_size=4,
                expected_worldwide_count=3, expected_worldwide_av_count=1)

    def test_rejects_archive_sha_or_state_binding_mismatch(self):
        bad_state = dict(self.state, source_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "state does not bind"):
            build_crosswalk(self.archive, self.main, bad_state, self.worldwide, self.historical,
                            expected_archive_total=6, expected_batch_size=4,
                            expected_worldwide_count=3, expected_worldwide_av_count=1)

    def test_rejects_canonical_category_state_disagreement(self):
        bad_main = make_playlist([
            ("YEDEKLER", "Channel 1", self.urls[0]),
            ("YEDEKLER", "Channel 2", self.urls[1]),
            ("YABANCI ARŞİVİ", "Channel 3", self.urls[2]),
            ("YEDEKLER", "Channel 4", self.urls[3]),
            ("ANA ARŞİV", "Channel 5", self.urls[4]),
            ("ANA ARŞİV", "Channel 6", self.urls[5]),
        ])
        with self.assertRaisesRegex(ValueError, "disagrees"):
            build_crosswalk(self.archive, bad_main, self.state, self.worldwide, self.historical,
                            expected_archive_sha256=self.state["source_sha256"],
                            expected_archive_total=6, expected_batch_size=4,
                            expected_worldwide_count=3, expected_worldwide_av_count=1)

    def test_rejects_duplicate_worldwide_hashes(self):
        bad = dict(self.worldwide)
        bad["candidates"] = self.worldwide["candidates"] + [dict(self.worldwide["candidates"][0])]
        bad["unique_url_candidates"] = 4
        with self.assertRaisesRegex(ValueError, "Duplicate worldwide"):
            build_crosswalk(
                self.archive, self.main, self.state, bad, self.historical,
                expected_archive_sha256=self.state["source_sha256"],
                expected_archive_total=6, expected_batch_size=4,
                expected_worldwide_count=4, expected_worldwide_av_count=1)

    def test_rejects_incomplete_first_batch_status_map(self):
        bad = dict(self.state)
        bad["status"] = {"1": "TEST"}
        with self.assertRaisesRegex(ValueError, "status map"):
            build_crosswalk(self.archive, self.main, bad, self.worldwide, self.historical,
                            expected_archive_sha256=bad["source_sha256"],
                            expected_archive_total=6, expected_batch_size=4,
                            expected_worldwide_count=3, expected_worldwide_av_count=1)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Offline same-URL different-channel review tests; no network or playlist writes."""
import unittest
from discover import entries, discover
from shared_url_identity import normalized_url, summarize_shared_urls


def playlist(*rows):
    return "#EXTM3U\n" + "".join(
        f'#EXTINF:-1 tvg-id="{tvg}" group-title="TR",{name}\n'
        + (f"#EXTVLCOPT:program={program}\n" if program is not None else "")
        + f"{url}\n"
        for tvg, name, url, program in rows
    )


class SharedUrlIdentityTests(unittest.TestCase):
    def test_same_url_different_names_kept_as_review(self):
        url = "https://example.invalid/live.ts?token=private"
        live = playlist(("one.tr", "TRT 1", url, None))
        candidate = playlist(("sport.tr", "TRT Spor", url, None))
        # Candidate dedup remains one URL per downstream scanner contract.
        self.assertEqual(discover([("source", candidate)], live, {"source": "TR"}), [])
        report = summarize_shared_urls(
            [{**x, "source": "MAIN_PLAYLIST"} for x in entries(live)]
            + [{**x, "source": "source"} for x in entries(candidate)])
        self.assertEqual(report["cross_channel_url_collision_count"], 1)
        finding = report["cross_channel_url_collisions"][0]
        self.assertEqual(finding["channels"], ["TRT 1", "TRT Spor"])
        self.assertFalse(finding["broadcast_identity_verified"])
        self.assertFalse(finding["automatic_merge_or_delete_allowed"])
        self.assertNotIn("token=private", str(report))

    def test_identical_records_are_not_new_channels(self):
        url = "https://example.invalid/live.ts"
        text = playlist(("one", "One", url, None))
        report = summarize_shared_urls(list(entries(text)) * 3)
        self.assertEqual(report["cross_channel_url_collision_count"], 0)
        self.assertEqual(report["same_identity_repeated_entries"], 2)

    def test_same_name_different_tvg_id_is_reviewed(self):
        url = "https://example.invalid/live.ts"
        text = playlist(("one.tr", "One", url, None),
                        ("two.tr", "One", url, None))
        report = summarize_shared_urls(list(entries(text)))
        self.assertEqual(report["identity_metadata_conflict_count"], 1)

    def test_program_selectors_appear_as_unverified_multiplex_hints(self):
        url = "https://example.invalid/multiplex.ts"
        text = playlist(("one.tr", "One", url, 101),
                        ("two.tr", "Two", url, 202))
        parsed = list(entries(text))
        self.assertEqual([p.get("program_number") for p in parsed], [101, 202])
        report = summarize_shared_urls(parsed)
        self.assertEqual(report["multiple_program_selector_hint_count"], 1)
        self.assertEqual(report["cross_channel_url_collisions"][0]["program_selectors"], [101, 202])
        self.assertEqual(report["verified_distinct_broadcasts"], 0)

    def test_different_query_parameters_are_distinct_urls(self):
        rows = list(entries(playlist(
            ("a", "A", "https://example.invalid/live.ts?program=1", None),
            ("b", "B", "https://example.invalid/live.ts?program=2", None))))
        self.assertEqual(summarize_shared_urls(rows)["cross_channel_url_collision_count"], 0)

    def test_url_normalization_preserves_path_and_query(self):
        self.assertEqual(normalized_url("HTTPS://EXAMPLE.INVALID/Live.ts?Token=X"),
                         "https://example.invalid/Live.ts?Token=X")

    def test_actual_program_table_is_reported_without_playback_claim(self):
        import json
        import subprocess
        from unittest.mock import patch
        from stream_probe import probe
        payload = {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "programs": [
                {"program_num": 101},
                {"program_num": "202"},
                {"program_num": 101},
            ],
        }
        with patch("stream_probe._public_http_url", return_value=True), \\
             patch("stream_probe.shutil.which", return_value="/usr/bin/ffprobe"), \\
             patch("stream_probe.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, json.dumps(payload), "")) as run:
            result = probe("https://example.invalid/multiplex.ts")
        self.assertIn("-show_programs", run.call_args.args[0])
        self.assertEqual(result["mpegts_program_numbers"], [101, 202])
        self.assertTrue(result["mpegts_multiple_programs_detected"])
        self.assertFalse(result["mpegts_programs_playback_verified"])

    def test_no_program_selector_still_works(self):
        text = playlist(("one", "One", "https://example.invalid/one.ts", None))
        self.assertNotIn("program_number", list(entries(text))[0])


if __name__ == "__main__":
    unittest.main()

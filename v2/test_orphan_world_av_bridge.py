#!/usr/bin/env python3
"""Offline strict orphan-world video/audio reconciliation regression suite."""
import copy
import hashlib
import unittest
from orphan_world_av_bridge import reconcile


def sha(v):
    return hashlib.sha256(v.encode()).hexdigest()


def fixtures():
    rows = []
    for i in range(50):
        good = i == 0
        rows.append({"extinf_sha256": sha("meta-" + str(i)),
                     "candidates": [{"url_sha256": sha("url-" + str(i)),
                                     "status": "VIDEO_AUDIO_DECODED" if good else "PROBE_FAILED_HTTP_FORBIDDEN",
                                     "ffmpeg_video_audio_decoded": good,
                                     "video_stream": good, "audio_stream": good}]})
    rows.extend(copy.deepcopy(rows[:5]))
    o = {"schema": 1, "kind": "FOUR_UPSTREAM_ORPHAN_REPAIR_EVIDENCE_NOT_IBO",
         "orphan_entries": 55, "unique_orphan_metadata_identities": 50,
         "protected_playlist_modified": False, "plain_stream_urls_reported": False,
         "ibo_device_verified": False, "av_acceptance_rule": "FFMPEG_VIDEO_AND_AUDIO_DECODED_ONLY",
         "unique_candidate_urls_historically_or_officially_proven": 50,
         "all_proven_url_candidates_sealed_for_future_retest": 50,
         "unique_candidates_video_audio_verified": 1, "records": rows}
    world_rows = [{"url_sha256": sha("url-" + str(i)),
                   "status": "VIDEO_AUDIO_DECODED", "video": True,
                   "audio": True, "decoded": True} for i in (0, 1)]
    world_rows.append({"url_sha256": sha("other"), "status": "PROBE_FAILED_HTTP_NOT_FOUND",
                       "video": False, "audio": False, "decoded": False})
    w = {"schema": 1, "kind": "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
         "protected_main_playlist_modified": False, "plaintext_url_in_public_report": False,
         "ibo_player_verified": False, "probe_budget_expired": False,
         "unprobed": 0, "probed": 3, "unique_url_candidates": 3,
         "sealed_url_count": 3, "audio_video_decoded": 2, "candidates": world_rows}
    return o, w


class OrphanWorldAVBridgeTests(unittest.TestCase):
    def test_old_video_audio_cannot_substitute_for_current(self):
        a, b = fixtures()
        r = reconcile(a, b)
        self.assertEqual(r["orphan_candidate_hashes_in_world"], 2)
        self.assertEqual(r["orphan_urls_with_prior_ffmpeg_video_audio"], 2)
        self.assertEqual(r["orphan_identities_with_current_ffmpeg_video_audio"], 1)
        self.assertEqual(r["prior_decoded_not_currently_decoded"], 1)
        self.assertEqual(r["prior_decoded_now_failed_statuses"],
                         {"PROBE_FAILED_HTTP_FORBIDDEN": 1})
        self.assertTrue(r["prior_evidence_is_not_current_av"])

    def test_conflicting_current_duplicate_fails(self):
        a, b = fixtures()
        a["records"][-1]["candidates"][0]["status"] = "VIDEO_ONLY"
        with self.assertRaises(ValueError):
            reconcile(a, b)

    def test_fake_current_decoder_success_fails(self):
        a, b = fixtures()
        a["records"][1]["candidates"][0]["ffmpeg_video_audio_decoded"] = True
        with self.assertRaises(ValueError):
            reconcile(a, b)

    def test_false_world_decoder_fails(self):
        a, b = fixtures()
        b["candidates"][1]["audio"] = False
        with self.assertRaises(ValueError):
            reconcile(a, b)

    def test_incomplete_world_or_unsafe_playlist_fails(self):
        a, b = fixtures()
        b["unprobed"] = 1
        with self.assertRaises(ValueError):
            reconcile(a, b)
        a, b = fixtures()
        a["protected_playlist_modified"] = True
        with self.assertRaises(ValueError):
            reconcile(a, b)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Grouped regression tests for immutable no-false-green orphan triage."""
import copy
import hashlib
import unittest

from orphan_evidence_triage import summarize

def sha(s):
    return hashlib.sha256(s.encode()).hexdigest()

def sample():
    data = []
    for i in range(50):
        decoded = i == 0
        items = [] if i == 49 else [{
            "url_sha256": sha("uri-"+str(i)),
            "status": "VIDEO_AUDIO_DECODED" if decoded else "PROBE_FAILED_HTTP_FORBIDDEN",
            "ffmpeg_video_audio_decoded": decoded,
            "video_stream": decoded, "audio_stream": decoded,
        }]
        data.append({
            "source_id": "discevisita-tr" if i < 25 else "onureroz-turk-all",
            "extinf_sha256": sha("meta-"+str(i)),
            "uri_structure": "HTTP_URI_WITHOUT_HOST" if i == 49 else "NO_URI_PROVIDED",
            "candidates": items,
        })
    data.extend(copy.deepcopy(data[:5]))
    return {
        "schema": 1, "kind": "FOUR_UPSTREAM_ORPHAN_REPAIR_EVIDENCE_NOT_IBO",
        "orphan_entries": 55, "unique_orphan_metadata_identities": 50,
        "av_acceptance_rule": "FFMPEG_VIDEO_AND_AUDIO_DECODED_ONLY",
        "protected_playlist_modified": False, "plain_stream_urls_reported": False,
        "ibo_device_verified": False,
        "records": data,
        "unique_candidate_urls_historically_or_officially_proven": 49,
        "all_proven_url_candidates_sealed_for_future_retest": 49,
        "unique_candidates_video_audio_verified": 1,
    }

class OriginalFiftyAnonymousTriageTests(unittest.TestCase):
    def test_completely_checked_originals_remain_failed_until_av(self):
        a = summarize(sample())
        self.assertEqual((a["current_ffmpeg_video_audio_verified"],
                          a["has_candidate_but_current_av_unverified"],
                          a["no_exact_valid_candidate"]), (1,48,1))
        self.assertFalse(a["full_playback_recovery_completed"])
        self.assertEqual(len(a["identities"]), 50)
        self.assertEqual(a["unique_sha256_candidate_urls"], 49)
        self.assertFalse(a["plaintext_url_reported"])
    def test_false_green_status_and_inconsistent_sha_fail(self):
        x=sample()
        x["records"][1]["candidates"][0]["status"] = "VIDEO_AUDIO_DECODED"
        with self.assertRaisesRegex(ValueError, "False current"):
            summarize(x)
        x=sample()
        x["records"][50]["candidates"][0]["status"] = "PROBE_FAILED_NETWORK_TIMEOUT"
        x["records"][50]["candidates"][0]["ffmpeg_video_audio_decoded"] = False
        x["records"][50]["candidates"][0]["video_stream"] = False
        x["records"][50]["candidates"][0]["audio_stream"] = False
        with self.assertRaisesRegex(ValueError, "Contradictory"):
            summarize(x)
    def test_original_occurrences_missing_hard_fail(self):
        x=sample()
        x["records"].pop()
        with self.assertRaisesRegex(ValueError, "55"):
            summarize(x)
    def test_source_metadata_is_not_a_playback_success(self):
        x=sample()
        x["records"][1]["candidates"][0]["status"] = "VIDEO_ONLY"
        x["records"][1]["candidates"][0]["video_stream"] = True
        x["records"][51]["candidates"][0]["status"] = "VIDEO_ONLY"
        x["records"][51]["candidates"][0]["video_stream"] = True
        a=summarize(x)
        self.assertEqual(a["current_ffmpeg_video_audio_verified"],1)
        self.assertEqual(a["candidate_url_status_counts"]["VIDEO_ONLY"],1)
    def test_broken_no_host_reference_never_infers_media_url(self):
        a=summarize(sample())
        x=[i for i in a["identities"] if i["decision"]=="MISSING_EXACT_PUBLIC_STREAM_SOURCE"]
        self.assertEqual(x[0]["no_candidate_original_uri_structures"],["HTTP_URI_WITHOUT_HOST"])
        self.assertNotIn("://",str(a))
    def test_archive_mismatch_rejected(self):
        x=sample()
        x["all_proven_url_candidates_sealed_for_future_retest"]=48
        with self.assertRaisesRegex(ValueError, "archive"):
            summarize(x)

if __name__=="__main__":
    unittest.main()

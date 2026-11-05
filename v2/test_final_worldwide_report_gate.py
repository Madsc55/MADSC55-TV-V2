#!/usr/bin/env python3
"""Grouped offline tamper tests for the final scan encrypted manifest."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from final_worldwide_report_gate import inspect

HASH = "a" * 64

class FinalWorldwideReportGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.name = "final-worldwide-001.sealed"
        self.payload = b"sealing fixture, never a real URL"
        (self.root / self.name).write_bytes(self.payload)
        self.report = {
            "schema": 1,
            "kind": "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
            "protected_main_playlist_modified": False,
            "ibo_player_verified": False,
            "plaintext_url_in_public_report": False,
            "source_metadata_and_audio_track_language_tags_are_not_speech_proof": True,
            "spoken_language_verified": 0,
            "readiness": "REVIEW_REQUIRED",
            "unique_url_candidates": 1,
            "probed": 1, "unprobed": 0, "probe_budget_expired": False,
            "source_success_count": 1, "source_fetch_count": 1,
            "audio_video_decoded": 1,
            "av_status_counts": {"VIDEO_AUDIO_DECODED": 1},
            "metadata_language_route_counts": {"TR_METADATA_HINT": 1},
            "candidates": [{
                "url_sha256": HASH, "source_ids": ["protected-fixture"],
                "name": "Fixture", "language_route": "TR_METADATA_HINT",
                "spoken_language_verified": False, "ibo_player_verified": False,
                "status": "VIDEO_AUDIO_DECODED", "video": True,
                "audio": True, "decoded": True,
            }],
            "sealed_url_count": 1,
            "sealed_artifacts": [{"name": self.name, "count": 1,
                                  "sha256": hashlib.sha256(self.payload).hexdigest()}],
        }
        self.write()

    def write(self):
        (self.root / "final-worldwide-acceptance.json").write_text(json.dumps(self.report))

    def check(self, complete=True):
        self.write()
        return inspect(self.root / "final-worldwide-acceptance.json", require_complete=complete)

    def fails(self, prefix):
        with self.assertRaisesRegex(ValueError, prefix):
            self.check()

    def test_complete_sealed_real_candidate(self):
        self.assertEqual(self.check()["status"], "COMPLETE_AV_COVERAGE_EVIDENCE")

    def test_no_ibo_player_proof(self):
        self.report["ibo_player_verified"] = True
        self.fails("INVALID_PRIVACY_OR_PLAYBACK_PROOF")

    def test_no_plain_url_leak(self):
        self.report["candidates"][0]["url"] = "https://bad.invalid/private"
        self.fails("PLAINTEXT_URL_FIELD")

    def test_no_stream_url_in_name(self):
        self.report["candidates"][0]["name"] = "https://bad.invalid/private"
        self.fails("PLAINTEXT_URL_EXPOSURE")

    def test_missing_sealed_file(self):
        (self.root / self.name).unlink()
        self.fails("SEALED_FILE_MISSING")

    def test_tampered_sealed_digest(self):
        (self.root / self.name).write_bytes(b"modified after manifest hash")
        self.fails("SEALED_CHECKSUM_MISMATCH")

    def test_total_not_equal_manifest(self):
        self.report["sealed_url_count"] = 2
        self.fails("SEALED_TOTAL_MISMATCH")

    def test_missing_provenance(self):
        self.report["candidates"][0]["source_ids"] = []
        self.fails("MISSING_SOURCE_PROVENANCE")

    def test_false_av_decode(self):
        self.report["candidates"][0]["video"] = False
        self.fails("FALSE_AV_DECODE_CLAIM")

    def test_budget_expired_cannot_pass_as_complete(self):
        c = self.report["candidates"][0]
        c.update({"status": "NOT_PROBED_BUDGET", "video": False, "audio": False, "decoded": False})
        self.report.update({"probed": 0, "unprobed": 1, "probe_budget_expired": True,
                            "audio_video_decoded": 0, "av_status_counts": {}})
        self.fails("SOME_URLS_UNPROBED_BUDGET")
        self.assertEqual(self.check(complete=False)["status"], "PARTIAL_AV_COVERAGE_EVIDENCE")

    def test_provenance_counts_and_invalid_origin_rejected(self):
        self.report["evidence_origin_counts"] = {"PRIOR_RUN_HASH_ONLY_NOT_FRESH": 1}
        self.report["candidates"][0]["evidence_origin"] = "PRIOR_RUN_HASH_ONLY_NOT_FRESH"
        self.assertEqual(self.check()["decoded_video_audio"], 1)
        self.report["evidence_origin_counts"] = {"CURRENT_RUN_FFPROBE_FFMPEG": 1}
        self.fails("EVIDENCE_ORIGIN_DISTRIBUTION_MISMATCH")
        self.report["candidates"][0]["evidence_origin"] = "FAKE_FRESH"
        self.fails("INVALID_EVIDENCE_ORIGIN")

    def test_unprobed_cannot_claim_fresh_av_evidence(self):
        self.report["evidence_origin_counts"] = {"CURRENT_RUN_FFPROBE_FFMPEG": 1}
        self.report["candidates"][0]["evidence_origin"] = "CURRENT_RUN_FFPROBE_FFMPEG"
        self.report["candidates"][0].update({
            "status": "NOT_PROBED_BUDGET", "video": False,
            "audio": False, "decoded": False})
        self.report.update({"probed": 0, "unprobed": 1,
                            "probe_budget_expired": True, "audio_video_decoded": 0,
                            "av_status_counts": {}})
        with self.assertRaisesRegex(ValueError, "UNPROBED_MISLABELED"):
            self.check(complete=False)

    def test_all_av_status_classes_reject_inconsistent_flags(self):
        cases = [
            ("VIDEO_AUDIO_STREAMS_ONLY", True, False, False),
            ("VIDEO_ONLY", True, True, False),
            ("AUDIO_ONLY", False, False, False),
            ("NO_AV", False, True, False),
        ]
        for status, video, audio, decoded in cases:
            with self.subTest(status=status):
                self.report["candidates"][0].update(
                    {"status": status, "video": video, "audio": audio,
                     "decoded": decoded})
                self.report["audio_video_decoded"] = 0
                self.report["av_status_counts"] = {status: 1}
                self.fails("INCONSISTENT_AV_STATUS_FLAGS")

    def test_failed_probe_cannot_claim_video_stream(self):
        self.report["candidates"][0].update(
            {"status": "PROBE_UNCONFIRMED", "video": True,
             "audio": False, "decoded": False})
        self.report["audio_video_decoded"] = 0
        self.report["av_status_counts"] = {"PROBE_UNCONFIRMED": 1}
        self.fails("FAILED_PROBE_WITH_AV_FLAGS")

    def test_malformed_evidence_origin_distribution_rejected(self):
        self.report["candidates"][0]["evidence_origin"] = "CURRENT_RUN_FFPROBE_FFMPEG"
        for invalid in (None, [], {"CURRENT_RUN_FFPROBE_FFMPEG": True},
                        {"CURRENT_RUN_FFPROBE_FFMPEG": 0},
                        {"UNKNOWN_ORIGIN": 1}):
            with self.subTest(invalid=invalid):
                self.report["evidence_origin_counts"] = invalid
                self.fails("INVALID_EVIDENCE_ORIGIN_DISTRIBUTION")

    def test_budget_expiry_requires_boolean(self):
        for invalid in (None, 0, 1, "false", [], {}):
            with self.subTest(invalid=invalid):
                self.report["probe_budget_expired"] = invalid
                self.fails("BUDGET_EXPIRY_INCONSISTENT")

    def test_unknown_probe_status_rejected(self):
        self.report["candidates"][0].update(
            {"status": "FABRICATED_SUCCESS", "video": False,
             "audio": False, "decoded": False})
        self.report["audio_video_decoded"] = 0
        self.report["av_status_counts"] = {"FABRICATED_SUCCESS": 1}
        self.fails("UNKNOWN_PROBE_STATUS")

    def test_duplicate_and_invalid_hash_rejected(self):
        self.report["candidates"][0]["url_sha256"] = "bad"
        self.fails("INVALID_CANDIDATE_SHA")

if __name__ == "__main__":
    unittest.main()

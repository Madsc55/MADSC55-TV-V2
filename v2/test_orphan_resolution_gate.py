#!/usr/bin/env python3
"""Single offline regression for immutable orphan resolution accounting."""
import unittest
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
from orphan_resolution_gate import classify_report, main


def fixture():
    records = []
    sources = ("discevisita-tr", "github-auto-24",
               "onureroz-turk-karma", "onureroz-turk-all")
    source_for_index = ([sources[0]] * 17 + [sources[1]] * 19 +
                        [sources[2]] * 8 + [sources[3]] * 6)
    for i in range(50):
        av = i < 5
        candidate = i < 37
        records.append({"source_id": source_for_index[i],
                        "extinf_sha256": ("%064x" % (i+1)),
                        "candidates": ([{"url_sha256": "%064x" % (i+100),
                                         "video_stream": av, "audio_stream": av,
                                         "ffmpeg_video_audio_decoded": av,
                                         "status": "VIDEO_AUDIO_DECODED" if av else "PROBE_FAILED_NOT_PROVEN_DEAD"}]
                                       if candidate else [])})
    for i in (0, 1, 17, 18, 44):
        records.append(dict(records[i]))
    return {"immutable_orphan_identity_guard":
                {"original_source_occurrences": 55,
                 "original_distinct_extinf_identities": 50,
                 "original_occurrences_missing_metadata": 0,
                 "original_source_occurrences_still_present": 55},
            "protected_playlist_modified": False,
            "plain_stream_urls_reported": False,
            "ibo_device_verified": False,
            "all_proven_url_candidates_sealed_for_future_retest": 37,
            "unique_candidate_urls_historically_or_officially_proven": 37,
            "records": records}


class OrphanResolutionGateTests(unittest.TestCase):
    def test_exact_5_32_13_not_falsely_marked_green(self):
        result = classify_report(fixture())
        self.assertEqual(result["video_audio_verified_identities"], 5)
        self.assertEqual(result["candidate_present_av_unverified_identities"], 32)
        self.assertEqual(result["no_valid_candidate_identities"], 13)
        self.assertEqual(result["remaining_unverified_identities"], 45)
        self.assertEqual(result["status"], "RECOVERY_INCOMPLETE_REAL_AV_REQUIRED")
        queues = result["hash_only_identity_work_queues"]
        self.assertEqual(len(queues["video_audio_verified"]), 5)
        self.assertEqual(len(queues["candidate_av_unverified"]), 32)
        self.assertEqual(len(queues["without_valid_candidate"]), 13)
        all_ids = [row["original_extinf_sha256"]
                   for entries in queues.values() for row in entries]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertEqual(len(all_ids), 50)
        self.assertTrue(all(not row["candidate_url_sha256"]
                            for row in queues["without_valid_candidate"]))
        self.assertTrue(all(row["candidate_url_sha256"]
                            for row in queues["candidate_av_unverified"]))
        self.assertTrue(all(all(len(x) == 64 for x in row["candidate_url_sha256"])
                            for entries in queues.values() for row in entries))


    def test_report_only_records_missing_av_but_default_still_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inp = root / "input.json"
            inp.write_text(json.dumps(fixture()), encoding="utf-8")
            out1, out2 = root / "report_only.json", root / "strict.json"
            with patch.object(sys, "argv", ["gate", "--report", str(inp),
                                           "--output", str(out1), "--report-only"]):
                main()
            saved = json.loads(out1.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "RECOVERY_INCOMPLETE_REAL_AV_REQUIRED")
            self.assertEqual(saved["remaining_unverified_identities"], 45)
            self.assertEqual(len(saved["hash_only_identity_work_queues"]["without_valid_candidate"]), 13)
            with patch.object(sys, "argv", ["gate", "--report", str(inp),
                                           "--output", str(out2)]):
                with self.assertRaisesRegex(SystemExit, "RECOVERY_INCOMPLETE"):
                    main()
            self.assertEqual(json.loads(out2.read_text())["remaining_unverified_identities"], 45)

    def test_missing_original_identity_is_hard_error(self):
        r = fixture()
        r["records"].pop()
        with self.assertRaises(ValueError):
            classify_report(r)

    def test_candidate_without_video_audio_is_not_verified(self):
        r = fixture()
        for index in (0, 50):
            r["records"][index]["candidates"][0].update({
                "audio_stream": False, "ffmpeg_video_audio_decoded": False,
                "status": "VIDEO_ONLY"})
        result = classify_report(r)
        self.assertEqual(result["video_audio_verified_identities"], 4)

    def test_legacy_ffprobe_only_not_accepted_as_av(self):
        r = fixture()
        for index in (0, 50):
            r["records"][index]["candidates"][0].update({
                "status": "VIDEO_STREAM_OBSERVED",
                "ffmpeg_video_audio_decoded": False,
                "video_stream": True, "audio_stream": True})
        result = classify_report(r)
        self.assertEqual(result["video_audio_verified_identities"], 4)
        self.assertEqual(result["remaining_unverified_identities"], 46)

    def test_false_decoded_claim_without_audio_rejected(self):
        r = fixture()
        r["records"][0]["candidates"][0]["audio_stream"] = False
        with self.assertRaises(ValueError):
            classify_report(r)

    def test_sealed_candidate_count_must_match_distinct_hashes(self):
        r = fixture()
        r["records"][1]["candidates"][0]["url_sha256"] = r["records"][0]["candidates"][0]["url_sha256"]
        with self.assertRaisesRegex(ValueError, "Original 55/50 identity"):
            classify_report(r)

    def test_source_occurrence_drift_rejected(self):
        r = fixture()
        r["records"][0]["source_id"] = "github-auto-24"
        with self.assertRaisesRegex(ValueError, "per-source occurrence"):
            classify_report(r)

    def test_unrecognized_original_source_rejected(self):
        r = fixture()
        r["records"][0]["source_id"] = "untrusted-publisher"
        with self.assertRaises(ValueError):
            classify_report(r)

    def test_nested_stream_url_rejected(self):
        r = fixture()
        r["records"][0]["candidates"][0]["stream_url"] = "https://example.net/secret.m3u8"
        with self.assertRaises(ValueError):
            classify_report(r)

    def test_report_with_public_plaintext_url_rejected(self):
        r = fixture()
        r["records"][0]["candidates"][0]["url"] = "https://example.net/private.m3u8"
        with self.assertRaises(ValueError):
            classify_report(r)


if __name__ == "__main__":
    unittest.main()

import copy
import unittest

from ibo_device_acceptance import validate_report

def fixture():
    return {
        "schema_version": 1,
        "session_id": "manual-session-001",
        "tested_at": "2026-11-21T09:00:00+01:00",
        "device_model": "user-reported-device",
        "player_app_version": "user-reported-version",
        "playlist_url": "https://raw.githubusercontent.com/Madsc55/MADSC55-TV-V2/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8",
        "playlist_sha256": "a" * 64,
        "ui_checks": {
            "playlist_loaded": True,
            "categories_visible": True,
            "yedekler_visible": True,
            "favorites_visible": True,
            "epg_visible": True,
        },
        "channel_results": [{
            "channel_id": "user-confirmed-exact-channel-id",
            "entry_sha256": "b" * 64,
            "video_observed": True,
            "audio_observed": True,
            "observed_seconds": 30,
            "evidence_refs": ["user-provided-evidence-1"],
        }],
        "errors": [],
        "evidence_refs": ["user-provided-session-evidence"],
    }

class DeviceEvidenceTests(unittest.TestCase):
    def test_complete_evidence_never_auto_accepts_production(self):
        result = validate_report(fixture())
        self.assertEqual(result["status"], "EVIDENCE_COMPLETE_REQUIRES_HUMAN_REVIEW")
        self.assertFalse(result["production_accepted"])
        self.assertFalse(result["device_playback_certified"])

    def test_failures_are_recorded_not_hidden(self):
        report = fixture()
        report["channel_results"][0]["audio_observed"] = False
        report["errors"] = ["No audio on tested channel"]
        result = validate_report(report)
        self.assertEqual(result["status"], "EVIDENCE_RECORDED_WITH_FAILURES")
        self.assertEqual(result["errors_recorded"], 1)
        self.assertFalse(result["production_accepted"])

    def test_rejects_wrong_playlist_and_invalid_digest(self):
        for key, value in (("playlist_url", "https://example.invalid/list.m3u"),
                           ("playlist_sha256", "not-a-digest")):
            report = fixture()
            report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_report(report)

    def test_requires_timezone_aware_timestamp(self):
        report = fixture()
        report["tested_at"] = "2026-11-21T09:00:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            validate_report(report)

    def test_rejects_duplicate_channel_identity(self):
        report = fixture()
        report["channel_results"].append(copy.deepcopy(report["channel_results"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_report(report)

    def test_requires_exact_ui_checks(self):
        report = fixture()
        del report["ui_checks"]["epg_visible"]
        with self.assertRaisesRegex(ValueError, "UI/category/EPG"):
            validate_report(report)

    def test_rejects_truthy_non_boolean_observations(self):
        report = fixture()
        report["channel_results"][0]["video_observed"] = "yes"
        with self.assertRaisesRegex(ValueError, "explicit booleans"):
            validate_report(report)

    def test_rejects_unexpected_fields_that_could_smuggle_raw_streams(self):
        report = fixture()
        report["stream_url"] = "https://example.invalid/live"
        with self.assertRaisesRegex(ValueError, "unexpected"):
            validate_report(report)

if __name__ == "__main__":
    unittest.main()

"""Regression tests for document-platform integration report integrity."""
import unittest
from source_integration_gate import _valid


def valid_report():
    return {
        "schema": 1,
        "kind": "PUBLIC_DOCUMENT_REFERENCES_ONLY",
        "platforms": {
            "scribd": {"queries": 0},
            "slideshare": {"queries": 2},
            "internet-archive": {"queries": 3},
        },
        "references": [],
        "errors": [],
        "playback_verified": False,
        "validated_m3u_source_count": 0,
    }


class DocumentPlatformValidationTests(unittest.TestCase):
    def test_valid_shape(self):
        self.assertTrue(_valid("document_platforms", valid_report()))

    def test_non_dict_platform_is_rejected(self):
        report = valid_report()
        report["platforms"]["scribd"] = "invalid"
        self.assertFalse(_valid("document_platforms", report))

    def test_negative_query_count_is_rejected(self):
        report = valid_report()
        report["platforms"]["slideshare"]["queries"] = -1
        self.assertFalse(_valid("document_platforms", report))

    def test_boolean_query_count_is_rejected(self):
        report = valid_report()
        report["platforms"]["internet-archive"]["queries"] = True
        self.assertFalse(_valid("document_platforms", report))

    def test_missing_platform_is_rejected(self):
        report = valid_report()
        del report["platforms"]["scribd"]
        self.assertFalse(_valid("document_platforms", report))

    def test_playback_claim_is_rejected(self):
        report = valid_report()
        report["playback_verified"] = True
        self.assertFalse(_valid("document_platforms", report))


    def test_malformed_channel_advisory_handoffs_are_rejected(self):
        base = {
            "schema": 1,
            "candidates": [],
            "source_audit": [],
            "coverage_status": "COMPLETE",
            "playback_verified": False,
            "candidate_status": "UNVERIFIED",
        }
        for key in ("advisory_channel_identity_handoff",
                    "public_source_reference_handoff",
                    "approved_live_page_handoff"):
            with self.subTest(key=key):
                report = dict(base)
                report[key] = "invalid"
                self.assertFalse(_valid("channel_scan", report))


    def test_invalid_channel_advisory_links(self):
        report = {
            "schema": 1, "candidates": [], "source_audit": [],
            "coverage_status": "COMPLETE", "playback_verified": False,
            "candidate_status": "UNVERIFIED",
            "advisory_channel_identity_handoff": {
                "av_verified": False, "ibo_device_verified": False,
                "youtube_pages_are_not_m3u_streams": True,
                "official_websites_are_not_m3u_streams": True,
                "linked_m3u_candidates": 1, "links": "invalid",
            },
        }
        self.assertFalse(_valid("channel_scan", report))


if __name__ == "__main__":
    unittest.main()

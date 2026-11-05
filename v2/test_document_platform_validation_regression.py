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


if __name__ == "__main__":
    unittest.main()

"""Offline tests: no channel network scan and no protected playlist writes."""
import unittest
from stage3_metadata_acceptance import normalized_identity, epg_match, quality_from_probe, category


class Stage3MetadataTests(unittest.TestCase):
    def test_country_is_not_guessed(self):
        self.assertEqual(normalized_identity({"name": "TRT", "country": "TR"})["country_verified"], False)
        self.assertEqual(normalized_identity({"country": "SE"})["country"], "UNVERIFIED")

    def test_epg_requires_exact_id(self):
        self.assertTrue(epg_match({"tvg_id": "trt1.tr"}, {"channel": "trt1.tr"}))
        self.assertFalse(epg_match({"name": "TRT 1"}, {"name": "TRT 1"}))
        self.assertFalse(epg_match({"tvg_id": "trt1.tr"}, {"channel": "trt1.az"}))

    def test_no_quality_from_name_or_http(self):
        self.assertFalse(quality_from_probe({"name": "1440P HD", "http_status": 200})["av_verified"])
        self.assertFalse(quality_from_probe({"status": "AV_VERIFIED", "video": True, "audio": True, "streams": [
            {"codec_type": "video", "width": 1920, "height": 1080}]})["av_verified"])

    def test_real_av_quality(self):
        result = quality_from_probe({"real_probe": True, "streams": [
            {"codec_type": "video", "width": 1280, "height": 720},
            {"codec_type": "audio", "codec_name": "aac"}]})
        self.assertEqual(result["quality"], "720p")
        self.assertTrue(result["av_verified"])

    def test_category_no_guess(self):
        self.assertEqual(category({"name": "News TV"}), "UNCATEGORIZED")
        self.assertEqual(category({"group": " YEREL "}), "YEREL")


if __name__ == "__main__":
    unittest.main()

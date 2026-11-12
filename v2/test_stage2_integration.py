"""Offline end-to-end Stage 2 integration; no channel search or playback."""
import unittest
from stage2_integration import integrate
from recovery_queue import sha_for_url


class Stage2IntegrationTests(unittest.TestCase):
    def test_retry_identity_epg_category_together(self):
        url = "https://example.invalid/channel"
        xml = ('<tv><channel id="news.tr"></channel>'
               '<programme channel="news.tr" start="20261112190000 +0000"/>'
               '</tv>')
        result = integrate([{"url": url, "source": "tr-source", "name": "Example",
                             "tvg_id": "news.tr", "group": "Haber",
                             "status": "TIMEOUT", "attempts": 0}],
                           scopes={"tr-source": "TR"}, xmltv_text=xml)
        self.assertEqual(result["mode"], "offline-no-channel-search")
        self.assertEqual(result["observations"][0]["url_sha256"], sha_for_url(url))
        self.assertEqual(result["observations"][0]["country_hint"], "TR")
        self.assertEqual(result["observations"][0]["category_hint"], "news")
        self.assertTrue(result["observations"][0]["epg_verified"])
        self.assertTrue(result["observations"][0]["epg_programme_available"])
        self.assertFalse(result["observations"][0]["country_verified"])
        self.assertEqual(result["recovery"]["retry"][0]["next_attempt"], 1)
        self.assertNotIn(url, str(result))

    def test_no_false_av_acceptance(self):
        url = "https://example.invalid/channel"
        row = {"url": url, "status": "AV_VERIFIED",
               "video": True, "audio": True, "decoded_av_verified": False}
        self.assertEqual(integrate([row])["recovery"]["verified"], [])
        row["decoded_av_verified"] = True
        self.assertEqual(len(integrate([row])["recovery"]["verified"]), 1)

    def test_mismatch_and_duplicate_fail_closed(self):
        url = "https://example.invalid/channel"
        with self.assertRaises(ValueError):
            integrate([{"url": url, "url_sha256": sha_for_url(url + "bad")}])
        with self.assertRaises(ValueError):
            integrate([{"url": url}, {"url": url}])

    def test_metadata_cannot_self_certify(self):
        result = integrate([{"url_sha256": sha_for_url("https://example.invalid/a"),
                             "country_verified": True, "category_verified": True,
                             "epg_verified": True}])
        self.assertFalse(result["observations"][0]["country_verified"])
        self.assertFalse(result["observations"][0]["category_verified"])
        self.assertFalse(result["observations"][0]["epg_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

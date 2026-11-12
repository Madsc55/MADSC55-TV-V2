import unittest
from identity_metadata import identity_metadata, verify_epg_ids
from discover import discover


class IdentityMetadataTests(unittest.TestCase):
    def test_country_and_epg_are_hints_only(self):
        data = identity_metadata({"tvg_id": "Station.az", "group": "İdman"}, "world")
        self.assertEqual(data["country_hint"], "AZ")
        self.assertEqual(data["epg_id_candidate"], "Station.az")
        self.assertEqual(data["category_hint"], "sports")
        self.assertFalse(data["epg_verified"])
        self.assertFalse(data["country_verified"])
        self.assertFalse(data["category_verified"])

    def test_missing_epg_or_unknown_category_not_invented(self):
        data = identity_metadata({"tvg_id": "", "group": "Unmapped"}, "TR")
        self.assertIsNone(data["epg_id_candidate"])
        self.assertEqual(data["category_hint"], "unclassified")
        self.assertFalse(data["epg_verified"])

    def test_exact_xmltv_epg_verification(self):
        candidates = [
            {"epg_id_candidate": "TRT1.tr", "epg_verified": False},
            {"epg_id_candidate": "TRT1", "epg_verified": False},
            {"epg_id_candidate": None, "epg_verified": False},
        ]
        xmltv = '<tv><channel id="TRT1.tr"><display-name>TRT 1</display-name></channel></tv>'
        rows = verify_epg_ids(candidates, xmltv)
        self.assertEqual([row["epg_verified"] for row in rows], [True, False, False])
        self.assertEqual(rows[0]["epg_match_type"], "exact_xmltv_channel_id")

    def test_invalid_xmltv_fails_closed(self):
        with self.assertRaises(ValueError):
            verify_epg_ids([], '<invalid/>')

    def test_discovery_report_keeps_private_url_out(self):
        url = "https://example.invalid/live.m3u8?secret=hidden"
        playlist = '#EXTM3U\n#EXTINF:-1 tvg-id="Channel.tr" group-title="Haber",Channel\n' + url + '\n'
        rows = discover([("source", playlist)], "#EXTM3U\n", {"source": "TR"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category_hint"], "news")
        self.assertEqual(rows[0]["epg_id_candidate"], "Channel.tr")
        self.assertNotIn(url, str(rows))
        self.assertFalse(rows[0]["epg_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

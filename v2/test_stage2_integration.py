"""Offline end-to-end Stage 2 integration; no channel search or playback."""
import unittest
from stage2_integration import integrate
from recovery_queue import sha_for_url


class Stage2IntegrationTests(unittest.TestCase):
    def test_retry_identity_epg_category_together(self):
        url = "https://example.invalid/channel"
        xml = ('<tv><channel id="news.tr"></channel>'
               '<programme channel="news.tr" start="20261112190000 +0000" stop="20261112200000 +0000"/>'
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

    def test_existing_scanner_offline_entrypoint_never_fetches_or_scans(self):
        import json
        import pathlib
        import tempfile
        from unittest.mock import patch
        import real_ibo_scan
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "observations.json"
            output = root / "v2" / "reports" / "result.json"
            source.write_text(json.dumps({"records": [
                {"url": "https://example.invalid/stream", "status": "TIMEOUT"}]}),
                encoding="utf-8")
            with patch.object(real_ibo_scan, "ROOT", root), patch("sys.argv", ["real_ibo_scan.py", "--stage2-offline-input",
                                    str(source), "--stage2-offline-output", str(output)]):
                with patch.object(real_ibo_scan, "fetch",
                                  side_effect=AssertionError("network access forbidden")):
                    with patch.object(real_ibo_scan, "check_hls",
                                      side_effect=AssertionError("playback forbidden")):
                        real_ibo_scan.main()
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "offline-no-channel-search")
            self.assertEqual(len(report["recovery"]["retry"]), 1)
            self.assertNotIn("https://example.invalid/stream", output.read_text())

    def test_offline_report_refuses_playlist_overwrite(self):
        import json
        import pathlib
        import tempfile
        from unittest.mock import patch
        import real_ibo_scan
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            source = root / "observations.json"
            source.write_text(json.dumps({"records": [{"url": "https://example.invalid/a"}]}))
            protected = root / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
            protected.write_text("PROTECTED")
            with patch.object(real_ibo_scan, "ROOT", root), patch("sys.argv", [
                "real_ibo_scan.py", "--stage2-offline-input", str(source),
                "--stage2-offline-output", str(protected)]):
                with self.assertRaises(SystemExit):
                    real_ibo_scan.main()
            self.assertEqual(protected.read_text(), "PROTECTED")


    def test_untrusted_xmltv_programme_claims_are_not_promoted(self):
        row = {
            "url_sha256": sha_for_url("https://example.invalid/epg"),
            "tvg_id": "Station.tr",
            "epg_verified": True,
            "epg_programme_available": True,
            "epg_match_type": "forged"
        }
        without_xmltv = integrate([row])["observations"][0]
        self.assertFalse(without_xmltv["epg_verified"])
        self.assertFalse(without_xmltv["epg_programme_available"])
        self.assertIsNone(without_xmltv["epg_match_type"])

        invalid_interval = ('<tv><channel id="Station.tr"/>'
                            '<programme channel="Station.tr" start="20261113120000 +0000"'
                            ' stop="20261113110000 +0000"/></tv>')
        with_invalid_xmltv = integrate([row], xmltv_text=invalid_interval)["observations"][0]
        self.assertTrue(with_invalid_xmltv["epg_verified"])
        self.assertFalse(with_invalid_xmltv["epg_programme_available"])
        self.assertEqual(with_invalid_xmltv["epg_match_type"], "exact_xmltv_channel_id")

        valid_interval = ('<tv><channel id="Station.tr"/>'
                          '<programme channel="Station.tr" start="20261113120000 +0200"'
                          ' stop="20261113110000 +0000"/></tv>')
        with_valid_xmltv = integrate([row], xmltv_text=valid_interval)["observations"][0]
        self.assertTrue(with_valid_xmltv["epg_programme_available"])

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

    def test_untrusted_metadata_hints_cannot_override_canonical_values(self):
        result = integrate([{"url_sha256": sha_for_url("https://example.invalid/a"),
                             "name": "Station 1080P", "group": "Haber",
                             "category_hint": "sports", "resolution_hint": "2160p",
                             "epg_id_candidate": "spoofed"}])
        row = result["observations"][0]
        self.assertEqual(row["category_hint"], "news")
        self.assertEqual(row["resolution_hint"], "1080p")
        self.assertIsNone(row["epg_id_candidate"])

    def test_resolution_hint_is_propagated_without_self_verification(self):
        result = integrate([{"url_sha256": sha_for_url("https://example.invalid/a"),
                             "name": "Station 1080P", "resolution_verified": True}])
        self.assertEqual(result["observations"][0]["resolution_hint"], "1080p")
        self.assertFalse(result["observations"][0]["resolution_verified"])

    def test_metadata_cannot_self_certify(self):
        result = integrate([{"url_sha256": sha_for_url("https://example.invalid/a"),
                             "country_verified": True, "category_verified": True,
                             "epg_verified": True}])
        self.assertFalse(result["observations"][0]["country_verified"])
        self.assertFalse(result["observations"][0]["category_verified"])
        self.assertFalse(result["observations"][0]["epg_verified"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

import io
import unittest
from unittest.mock import patch
import epg_integrity

class XMLTVIntegrityTests(unittest.TestCase):
    def test_unsafe_feed_urls_rejected_before_network(self):
        for url in ("https://user:secret@example.org/guide.xml",
                    "https://example.org\\@localhost/guide.xml"):
            with patch("epg_integrity.urllib.request.build_opener") as opener:
                result = epg_integrity.inspect(url, set())
                self.assertEqual(result["status"], "NON_HTTPS")
                opener.assert_not_called()

    def test_malformed_configured_source_urls_fail_closed_without_network(self):
        for url in (None, 7, [], {}, "https://[broken/epg.xml",
                    "http://example.org/epg.xml", "https://user:pass@example.org/epg.xml"):
            with self.subTest(url=url), patch("epg_integrity.urllib.request.build_opener") as opener:
                result = epg_integrity.inspect(url, set())
                self.assertEqual(result["status"], "NON_HTTPS")
                opener.assert_not_called()

    def test_valid_timezone_offsets(self):
        self.assertEqual(epg_integrity.parse_xmltv_time("20261113120000 +1400").utcoffset().total_seconds(), 50400)
        self.assertEqual(epg_integrity.parse_xmltv_time("20261113120000 -0330").utcoffset().total_seconds(), -12600)

    def test_malformed_timestamp_types_fail_closed(self):
        for value in (None, 0, True, [], {}, b"20261113120000"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    epg_integrity.parse_xmltv_time(value)

    def test_invalid_timezone_offsets_rejected(self):
        for value in ("20261113120000 +1460", "20261113120000 +1401", "20261113120000 +1500", "20261113120000 -2360"):
            with self.assertRaises(ValueError):
                epg_integrity.parse_xmltv_time(value)

    def test_invalid_programme_interval_is_reported(self):
        xml = b'<tv><channel id="x"/><programme channel="x" start="20261113130000 +0000" stop="20261113120000 +0000"/></tv>'
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response(xml)
            result = epg_integrity.inspect("https://example.org/epg.xml", {"x"})
        self.assertEqual(result["status"], "XMLTV_VALID")
        self.assertEqual(result["invalid_programme_intervals"], 1)
        self.assertEqual(result["current_programme_intervals"], 0)

    def test_programme_evidence_requires_valid_intervals_and_unique_xmltv_id(self):
        xml = (
            b'<tv><channel id="valid"/><channel id="invalid"/><channel id="duplicate"/>'
            b'<channel id="duplicate"/>'
            b'<programme channel="valid" start="20261113100000 +0000" stop="20261113110000 +0000"><title>Programme</title></programme>'
            b'<programme channel="invalid" start="20261113130000 +0000" stop="20261113120000 +0000"/>'
            b'<programme channel="duplicate" start="20261113100000 +0000" stop="20261113110000 +0000"/>'
            b'<programme channel="undeclared" start="20261113100000 +0000" stop="20261113110000 +0000"/>'
            b'</tv>'
        )
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response(xml)
            result = epg_integrity.inspect(
                "https://example.org/epg.xml", {"valid", "invalid", "duplicate", "undeclared"}
            )
        self.assertEqual(result["status"], "XMLTV_VALID")
        # Legacy raw count remains available, but cannot be used as proof.
        self.assertEqual(result["matched_programme_channel_ids"], 4)
        self.assertEqual(result["valid_matched_programme_channel_ids"], 1)
        self.assertEqual(result["duplicate_channel_ids"], 1)
        self.assertEqual(result["invalid_programme_intervals"], 1)
        self.assertLessEqual(result["current_matched_programme_channel_ids"],
                             result["valid_matched_programme_channel_ids"])

    def test_missing_or_blank_titles_do_not_count_as_epg_evidence(self):
        xml = (
            b'<tv><channel id="missing"/><channel id="blank"/><channel id="good"/>'
            b'<programme channel="missing" start="20261113100000 +0000" stop="20261113110000 +0000"/>'
            b'<programme channel="blank" start="20261113100000 +0000" stop="20261113110000 +0000"><title>  </title></programme>'
            b'<programme channel="good" start="20261113100000 +0000" stop="20261113110000 +0000"><title>News</title></programme>'
            b'</tv>'
        )
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response(xml)
            result = epg_integrity.inspect("https://example.org/epg.xml", {"missing", "blank", "good"})
        self.assertEqual(result["matched_programme_channel_ids"], 3)
        self.assertEqual(result["valid_matched_programme_channel_ids"], 1)
        self.assertEqual(result["missing_programme_titles"], 2)

    def test_current_titled_evidence_excludes_blank_and_duplicate_ids(self):
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        start = (now - datetime.timedelta(minutes=5)).strftime("%Y%m%d%H%M%S +0000")
        stop = (now + datetime.timedelta(minutes=5)).strftime("%Y%m%d%H%M%S +0000")
        xml = ('<tv><channel id="good"/><channel id="blank"/>'
               '<channel id="duplicate"/><channel id="duplicate"/>'
               + ''.join('<programme channel="%s" start="%s" stop="%s">%s</programme>'
                         % (channel, start, stop, title)
                         for channel, title in [("good", "<title>News</title>"),
                                                ("blank", "<title> </title>"),
                                                ("duplicate", "<title>News</title>"),
                                                ("undeclared", "<title>News</title>")])
               + '</tv>').encode()
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response(xml)
            result = epg_integrity.inspect("https://example.org/epg.xml", {"good", "blank", "duplicate", "undeclared"})
        self.assertEqual(result["status"], "XMLTV_VALID")
        self.assertEqual(result["current_programme_intervals"], 4)
        self.assertEqual(result["current_titled_unique_programme_intervals"], 1)
        self.assertEqual(result["current_matched_programme_channel_ids"], 1)
        self.assertEqual(result["current_titled_unique_programme_intervals"], 1)

    def test_current_titled_evidence_excludes_declared_non_playlist_channel(self):
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        start = (now - datetime.timedelta(minutes=5)).strftime("%Y%m%d%H%M%S +0000")
        stop = (now + datetime.timedelta(minutes=5)).strftime("%Y%m%d%H%M%S +0000")
        xml = ('<tv><channel id="listed"/><channel id="not-listed"/>'
               + ''.join('<programme channel="%s" start="%s" stop="%s"><title>News</title></programme>'
                         % (channel, start, stop) for channel in ("listed", "not-listed"))
               + '</tv>').encode()
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response(xml)
            result = epg_integrity.inspect("https://example.org/epg.xml", {"listed"})
        self.assertEqual(result["current_programme_intervals"], 2)
        self.assertEqual(result["current_titled_unique_programme_intervals"], 1)
        self.assertEqual(result["current_matched_programme_channel_ids"], 1)

    def test_expired_programmes_are_not_current_evidence(self):
        xml = (b'<tv><channel id="x"/>'
               b'<programme channel="x" start="20261113000000 +0000" stop="20261113010000 +0000">'
               b'<title>Old News</title></programme></tv>')
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response(xml)
            result = epg_integrity.inspect("https://example.org/epg.xml", {"x"})
        self.assertEqual(result["valid_matched_programme_channel_ids"], 1)
        self.assertEqual(result["current_matched_programme_channel_ids"], 0)
        self.assertEqual(result["expired_programme_intervals"], 1)
        self.assertEqual(result["latest_programme_stop_utc"], "2026-11-13T01:00:00+00:00")

    def test_main_report_preserves_unverified_historical_gap_status(self):
        import json
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "audit.json"
            sources = ["https://example.org/a.xml", "https://example.org/b.xml"]
            with (patch.object(epg_integrity, "ROOT", Path(directory)),
                  patch.object(epg_integrity, "LIVE", Path(directory) / "playlist.m3u"),
                  patch.object(epg_integrity, "OUT", out),
                  patch.object(epg_integrity, "entries", return_value=[{"tvg_id": "x"}]),
                  patch.object(epg_integrity, "inspect", side_effect=[
                      {"status": "XMLTV_VALID", "valid_matched_programme_channel_ids": 1},
                      {"status": "EPG_UNVERIFIED"}
                  ])):
                (Path(directory) / "v2").mkdir()
                (Path(directory) / "v2" / "epg_sources.json").write_text(
                    json.dumps({"sources": sources}), encoding="utf-8"
                )
                (Path(directory) / "playlist.m3u").write_text("#EXTM3U", encoding="utf-8")
                epg_integrity.main()
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["source_coverage"]["configured_sources"], 2)
            self.assertEqual(report["source_coverage"]["valid_xmltv_sources"], 1)
            self.assertEqual(report["source_coverage"]["unverified_sources"], 1)
            self.assertEqual(report["source_coverage"]["feeds_with_valid_matched_programmes"], 1)
            self.assertEqual(report["source_coverage"]["feeds_with_current_matched_programmes"], 0)
            self.assertIsNone(report["source_coverage"]["historical_303_gaps_resolved"])

    def test_epg_dtd_and_entity_declarations_are_rejected(self):
        xml = (b'<!DOCTYPE tv [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
               b'<tv><channel id="x"/></tv>')
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = Response(xml)
            result = epg_integrity.inspect("https://example.org/epg.xml", {"x"})
        self.assertEqual(result["status"], "XMLTV_DTD_REJECTED")

if __name__ == "__main__":
    unittest.main()

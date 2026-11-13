import io
import unittest
from unittest.mock import patch
import epg_integrity

class XMLTVIntegrityTests(unittest.TestCase):
    def test_valid_timezone_offsets(self):
        self.assertEqual(epg_integrity.parse_xmltv_time("20261113120000 +1400").utcoffset().total_seconds(), 50400)
        self.assertEqual(epg_integrity.parse_xmltv_time("20261113120000 -0330").utcoffset().total_seconds(), -12600)

    def test_invalid_timezone_offsets_rejected(self):
        for value in ("20261113120000 +1460", "20261113120000 +1401", "20261113120000 +1500", "20261113120000 -2360"):
            with self.assertRaises(ValueError):
                epg_integrity.parse_xmltv_time(value)

    def test_invalid_programme_interval_is_reported(self):
        xml = b'<tv><channel id="x"/><programme channel="x" start="20261113130000 +0000" stop="20261113120000 +0000"/></tv>'
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.urlopen", return_value=Response(xml)):
            result = epg_integrity.inspect("https://example.org/epg.xml", {"x"})
        self.assertEqual(result["status"], "XMLTV_VALID")
        self.assertEqual(result["invalid_programme_intervals"], 1)
        self.assertEqual(result["current_programme_intervals"], 0)

    def test_programme_evidence_requires_valid_intervals_and_unique_xmltv_id(self):
        xml = (
            b'<tv><channel id="valid"/><channel id="invalid"/><channel id="duplicate"/>'
            b'<channel id="duplicate"/>'
            b'<programme channel="valid" start="20261113100000 +0000" stop="20261113110000 +0000"/>'
            b'<programme channel="invalid" start="20261113130000 +0000" stop="20261113120000 +0000"/>'
            b'<programme channel="duplicate" start="20261113100000 +0000" stop="20261113110000 +0000"/>'
            b'<programme channel="undeclared" start="20261113100000 +0000" stop="20261113110000 +0000"/>'
            b'</tv>'
        )
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.urlopen", return_value=Response(xml)):
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

    def test_epg_dtd_and_entity_declarations_are_rejected(self):
        xml = (b'<!DOCTYPE tv [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
               b'<tv><channel id="x"/></tv>')
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        with patch("epg_integrity.urllib.request.urlopen", return_value=Response(xml)):
            result = epg_integrity.inspect("https://example.org/epg.xml", {"x"})
        self.assertEqual(result["status"], "XMLTV_DTD_REJECTED")

if __name__ == "__main__":
    unittest.main()

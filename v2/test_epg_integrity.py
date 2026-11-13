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

if __name__ == "__main__":
    unittest.main()

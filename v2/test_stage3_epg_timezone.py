#!/usr/bin/env python3
"""Stage 3 XMLTV UTC-offset regression tests (no network)."""
import datetime
import unittest
from epg_integrity import parse_xmltv_time


class XMLTVTimezoneTests(unittest.TestCase):
    def test_valid_half_hour_offset(self):
        parsed = parse_xmltv_time("20261111120000 +0530")
        self.assertEqual(parsed.utcoffset(), datetime.timedelta(hours=5, minutes=30))

    def test_valid_negative_offset(self):
        parsed = parse_xmltv_time("20261111120000 -0330")
        self.assertEqual(parsed.utcoffset(), -datetime.timedelta(hours=3, minutes=30))

    def test_invalid_minute_field_rejected(self):
        for offset in ("+0160", "-0199", "+2360"):
            with self.subTest(offset=offset):
                with self.assertRaisesRegex(ValueError, "Invalid UTC offset"):
                    parse_xmltv_time("20261111120000 " + offset)

    def test_invalid_hour_field_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid UTC offset"):
            parse_xmltv_time("20261111120000 +2400")


if __name__ == "__main__":
    unittest.main()

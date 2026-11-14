"""Regression for invalid HTTP codes in live-scan recovery diagnostics."""
import unittest
from real_ibo_scan import recovery_http_status


class RecoveryHTTPStatusTests(unittest.TestCase):
    def test_valid_codes(self):
        for code in (100, 200, 206, 404, 429, 500, 599):
            self.assertEqual(recovery_http_status({'last_http_status': code}), code)

    def test_invalid_codes_become_unknown(self):
        for value in (None, 0, 99, 600, -1, True, False, '404', 404.0, [], {}):
            self.assertIsNone(recovery_http_status({'last_http_status': value}))
        self.assertIsNone(recovery_http_status({}))


if __name__ == '__main__':
    unittest.main()

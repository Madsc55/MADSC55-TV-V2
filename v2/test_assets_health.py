import unittest
from assets_health import probe

class AssetProbeInputTests(unittest.TestCase):
    def test_malformed_values_are_rejected(self):
        for value in (None, 7, [], {}, "", "   "):
            self.assertEqual(probe(value)["status"], "INVALID_URL")

    def test_non_https_is_skipped(self):
        self.assertEqual(probe("http://example.org/logo.png")["status"], "SKIPPED_NON_HTTPS")

if __name__ == "__main__":
    unittest.main()

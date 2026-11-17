import unittest
from unittest.mock import patch
from v2.backup_text_sampler import sample, valid_url

class SamplerTests(unittest.TestCase):
    def test_invalid_url_rejected(self):
        with self.assertRaises(ValueError):
            sample("file:///etc/passwd")
    def test_embedded_credentials_rejected(self):
        with self.assertRaises(ValueError):
            sample("https://user:pass@example.com/live")
    def test_private_and_local_addresses_rejected(self):
        for url in ("http://127.0.0.1/live","http://10.0.0.1/live",
                    "http://169.254.169.254/latest","http://[::1]/live",
                    "https://localhost/live","https://test.localhost/live"):
            with self.subTest(url=url):
                self.assertFalse(valid_url(url))

    def test_local_domains_and_control_characters_rejected(self):
        for url in ("https://server.local/live", "http://host.internal/live",
                    "https://example.org/live\n", "https://example.org/live\x00",
                    "https://example.org/a b", "https://example.org/live#fragment"):
            with self.subTest(url=url):
                self.assertFalse(valid_url(url))

    def test_public_url_allowed(self):
        self.assertTrue(valid_url("https://example.org/live"))

    def test_invalid_duration_rejected(self):
        with self.assertRaises(ValueError):
            sample("https://example.com/live",99)
    @patch("v2.backup_text_sampler.shutil.which",return_value=None)
    def test_missing_ffmpeg_is_unverified(self,_):
        self.assertFalse(sample("https://example.com/live")["language_evidence_verified"])
if __name__=="__main__":
    unittest.main()

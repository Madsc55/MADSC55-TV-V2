import unittest
from unittest.mock import patch
from v2.backup_text_sampler import sample

class SamplerTests(unittest.TestCase):
    def test_invalid_url_rejected(self):
        with self.assertRaises(ValueError):
            sample("file:///etc/passwd")
    def test_embedded_credentials_rejected(self):
        with self.assertRaises(ValueError):
            sample("https://user:pass@example.com/live")
    def test_invalid_duration_rejected(self):
        with self.assertRaises(ValueError):
            sample("https://example.com/live",99)
    @patch("v2.backup_text_sampler.shutil.which",return_value=None)
    def test_missing_ffmpeg_is_unverified(self,_):
        self.assertFalse(sample("https://example.com/live")["language_evidence_verified"])
if __name__=="__main__":
    unittest.main()

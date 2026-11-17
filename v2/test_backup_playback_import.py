import hashlib
import unittest
from v2.backup_playback_import import convert

def key(i):
    return hashlib.sha256(str(i).encode()).hexdigest()
class PlaybackImportTests(unittest.TestCase):
    def test_complete_matching_aggregate(self):
        k=key(1)
        r=convert({"channels":[{"url_sha256":k}]},{"coverage_complete":True,"channel_results":[{"url_sha256":k,"playback":"VIDEO_DECODED","audio":"AUDIO_DECODED"}]})
        self.assertFalse(r["by_url_sha256"][k]["decoded_av_verified"])
    def test_incomplete_coverage_rejected(self):
        with self.assertRaises(ValueError):
            convert({"channels":[]},{"coverage_complete":False,"channel_results":[]})
    def test_mismatched_identity_rejected(self):
        with self.assertRaises(ValueError):
            convert({"channels":[{"url_sha256":key(1)}]},{"coverage_complete":True,"channel_results":[{"url_sha256":key(2)}]})
    def test_duplicate_playback_rejected(self):
        k=key(1)
        with self.assertRaises(ValueError):
            convert({"channels":[{"url_sha256":k}]},{"coverage_complete":True,"channel_results":[{"url_sha256":k},{"url_sha256":k}]})
if __name__=="__main__":
    unittest.main()

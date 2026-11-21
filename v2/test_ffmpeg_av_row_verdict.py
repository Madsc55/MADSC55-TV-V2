import unittest
from v2.ffmpeg_av_row_verdict import classify, summarize

class TestAVRowVerdict(unittest.TestCase):
    def test_decoded(self):
        self.assertEqual(classify({"audio_decoded": True, "video_decoded": True}), "AV_DECODED")
    def test_partial(self):
        self.assertEqual(classify({"audio_decoded": True, "video_decoded": False}), "AUDIO_ONLY")
        self.assertEqual(classify({"audio_decoded": False, "video_decoded": True}), "VIDEO_ONLY")
    def test_uncertain(self):
        self.assertEqual(classify({"reason": "http_429"}), "TIMEOUT_OR_RATE_LIMIT")
        self.assertEqual(classify({"reason": "unsupported_hls_dash"}), "UNSAFE_OR_UNSUPPORTED_TRANSPORT")
    def test_fail_closed(self):
        with self.assertRaises(ValueError):
            classify({"reason": "unknown"})
        with self.assertRaises(ValueError):
            classify({"confirmed_failed": True, "reason": "decode_error"})
        with self.assertRaises(ValueError):
            classify({"audio_decoded": True, "reason": "timeout"})
    def test_identity(self):
        row = {"channel_sha256": "a" * 64, "reason": "recheck_required"}
        self.assertEqual(summarize([row], expected=1)["counts"]["PENDING_RETRY"], 1)
        with self.assertRaises(ValueError):
            summarize([row, row])
        with self.assertRaises(ValueError):
            summarize([row], expected=20148)

if __name__ == "__main__":
    unittest.main()

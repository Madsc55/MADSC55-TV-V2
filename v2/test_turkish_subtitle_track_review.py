import unittest
from v2.turkish_subtitle_track_review import review_tracks

class SubtitleTrackReviewTests(unittest.TestCase):
    def test_turkish_track_is_candidate_only(self):
        result = review_tracks({"streams": [
            {"index": 0, "codec_type": "audio", "tags": {"language": "tr"}},
            {"index": 2, "codec_type": "subtitle", "tags": {"language": "tur"}},
            {"index": 3, "codec_type": "subtitle", "tags": {"language": "eng"}}]})
        self.assertEqual(result["turkish_subtitle_track_candidates"], 1)
        self.assertFalse(result["subtitle_tracks"][0]["subtitle_content_verified"])
        self.assertFalse(result["review_approved"])
        self.assertFalse(result["playlist_modified"])

    def test_no_language_does_not_infer_turkish(self):
        self.assertEqual(review_tracks({"streams": [{"index": 1, "codec_type": "subtitle"}]})["turkish_subtitle_track_candidates"], 0)

    def test_duplicate_indices_fail_closed(self):
        with self.assertRaises(ValueError):
            review_tracks({"streams": [{"index": 1, "codec_type": "subtitle"}, {"index": 1, "codec_type": "subtitle"}]})

    def test_malformed_payload_rejected(self):
        for data in ([], {}, {"streams": "bad"}, {"streams": [None]},
                     {"streams": [{"index": True, "codec_type": "subtitle"}]},
                     {"streams": [{"index": 1, "codec_type": "subtitle", "tags": {"language": 42}}]}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                review_tracks(data)

if __name__ == "__main__":
    unittest.main()

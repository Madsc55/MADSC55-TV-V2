import unittest
from v2.package2_evidence import evaluate, digest_url


class PackageTwoTests(unittest.TestCase):
    def test_exact_join_quality_language_assets(self):
        candidates = [{"channel_id": "TRT1.tr", "url": "https://example.com/" + x}
                      for x in ("a", "b", "c", "d")]
        rows = []
        for c in candidates[:3]:
            rows.append(dict(channel_id=c["channel_id"], url_sha256=digest_url(c["url"]),
                             observed_channel_id=c["channel_id"], identity_evidence_verified=True,
                             decoded_audio=True, decoded_video=True, height=1080, width=1920,
                             video_bitrate=4000000, speech_review_verified=True, speech_language="tur",
                             subtitle_content_review_verified=True, subtitle_language="tr",
                             origin_review_verified=True, broadcast_origin="AZ",
                             epg=dict(verified=True, channel_id=c["channel_id"], tvg_id="TRT1.tr",
                                      source_url="https://example.com/epg"),
                             logo=dict(official_origin_verified=True, content_verified=True,
                                       channel_id=c["channel_id"], url="https://example.com/logo",
                                       official_source_url="https://example.com/",
                                       content_sha256="a"*64)))
        rows[1]["video_bitrate"] = 5000000
        rows[2]["observed_channel_id"] = "TRT2.tr"
        report = evaluate(candidates, rows)
        self.assertEqual([x["url_sha256"] for x in report["quality"] if x["selected"]],
                         [digest_url(candidates[1]["url"])])
        self.assertTrue(report["reviews"][0]["language"]["spoken_turkish"])
        self.assertTrue(report["reviews"][0]["language"]["turkish_subtitles"])
        self.assertEqual(report["reviews"][0]["language"]["origin"], "AZ")
        self.assertEqual(report["reviews"][0]["assets"]["tvg_id"], "TRT1.tr")
        self.assertEqual(report["reviews"][0]["assets"]["logo"], "https://example.com/logo")
        self.assertEqual(report["quality"][2]["status"], "IDENTITY_MISMATCH")
        for review in report["reviews"][2:]:
            self.assertEqual(review["assets"], {"tvg_id": None, "logo": None})
        self.assertFalse(evaluate(candidates[:1], [rows[0], rows[0]])["quality"][0]["selected"])

    def test_hints_never_approve(self):
        c = {"channel_id": "A.tr", "url": "https://example.com/a", "name": "Turkish HD"}
        row = dict(channel_id="A.tr", url_sha256=digest_url(c["url"]),
                   observed_channel_id="A.tr", identity_evidence_verified=True,
                   speech_language="tr", subtitle_language="tr", broadcast_origin="TR",
                   logo={"url": "https://example.com/random.png"},
                   epg={"tvg_id": "A.tr"})
        result = evaluate([c], [row])["reviews"][0]
        self.assertFalse(result["language"]["spoken_turkish"])
        self.assertFalse(result["language"]["turkish_subtitles"])
        self.assertFalse(result["language"]["turkic_origin"])
        self.assertEqual(result["assets"], {"tvg_id": None, "logo": None})


if __name__ == "__main__":
    unittest.main()

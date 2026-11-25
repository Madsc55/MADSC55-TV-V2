import unittest
from email.message import Message
from urllib.error import HTTPError
from v2.discovery_provider_requests import retry_delay
from v2.stream_quality_decision import decide


class PackageOneTests(unittest.TestCase):
    def row(self, digest, **kwargs):
        return dict(dict(channel_id="TRT 1", observed_channel_id="TRT 1",
                         identity_evidence_verified=True, decoded_video=True,
                         decoded_audio=True, height=1080, width=1920,
                         video_bitrate=4000000, url_sha256=digest * 64), **kwargs)

    def test_rank_and_identity(self):
        rows = [self.row("a"), self.row("b", video_bitrate=5000000),
                self.row("c", height=720, video_bitrate=9000000),
                self.row("d", observed_channel_id="TRT 2", height=2160),
                self.row("e", identity_evidence_verified=False),
                self.row("f", decoded_audio=False)]
        out = decide(rows)["decisions"]
        self.assertEqual([x["url_sha256"] for x in out if x["selected"]], ["b"*64])
        self.assertEqual(out[3]["status"], "IDENTITY_MISMATCH")
        self.assertEqual(out[4]["status"], "IDENTITY_REVIEW_REQUIRED")
        self.assertEqual(out[5]["status"], "INSUFFICIENT_MEASUREMENTS")

    def test_throttle(self):
        for host in ("gitlab.com", "codeberg.org"):
            headers = Message()
            headers["Retry-After"] = "0"
            exc = HTTPError("https://" + host, 429, "Too Many Requests", headers, None)
            self.assertEqual(retry_delay(exc, 1), 30)
            self.assertEqual(retry_delay(exc, 2), 60)
            headers.replace_header("Retry-After", "600")
            self.assertIsNone(retry_delay(exc, 1))


if __name__ == "__main__":
    unittest.main()

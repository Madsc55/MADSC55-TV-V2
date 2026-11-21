"""Negative regression coverage for initial FFmpeg target screening.

DNS rebinding, HTTP redirects and HLS child URLs still require an OS egress sandbox.
"""
import unittest
from unittest.mock import patch
from stream_probe import _public_http_url, probe, verify_decoded_av


class PublicTargetTests(unittest.TestCase):
    def test_private_and_special_ip_literals_rejected(self):
        for host in ("127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254", "0.0.0.0", "[::1]", "[fc00::1]", "224.0.0.1"):
            with self.subTest(host=host):
                self.assertFalse(_public_http_url("http://" + host + "/stream"))

    def test_credentials_and_unsafe_schemes_rejected(self):
        for url in ("file:///etc/passwd", "http://user:pass@example.com/", "http://localhost/", "http://a.internal/stream", "http://example.com/a#fragment"):
            with self.subTest(url=url):
                self.assertFalse(_public_http_url(url))

    def test_dns_mixed_public_private_fails_closed(self):
        with patch("stream_probe.socket.getaddrinfo", return_value=[
            (2, 1, 6, "", ("8.8.8.8", 0)),
            (2, 1, 6, "", ("10.0.0.5", 0)),
        ]):
            self.assertFalse(_public_http_url("https://example.org/live"))

    def test_dns_error_fails_closed(self):
        with patch("stream_probe.socket.getaddrinfo", side_effect=OSError):
            self.assertFalse(_public_http_url("https://example.org/live"))

    def test_rejection_never_spawns_ffmpeg(self):
        with patch("stream_probe.subprocess.run") as run:
            self.assertEqual(probe("http://169.254.169.254/latest")["status"], "INVALID_URL")
            self.assertEqual(verify_decoded_av("http://127.0.0.1/")["decode_status"], "INVALID_URL")
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

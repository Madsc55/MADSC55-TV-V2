import unittest
from unittest.mock import patch
from v2.backup_text_sampler import sample, valid_url, public_dns_for_url
from v2.safe_hls_prefetch import UnsafeMediaSource

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

    def test_malformed_ports_and_single_label_hosts_rejected(self):
        for url in ("https://example.org:bad/live", "http://example.org:99999/live",
                    "https://intranet/live", "https://example.invalid/live"):
            with self.subTest(url=url):
                self.assertFalse(valid_url(url))

    @patch.dict("os.environ", {}, clear=True)
    def test_secure_egress_required_before_ffmpeg(self):
        with patch("v2.backup_text_sampler.subprocess.run") as proc:
            result = sample("https://example.org/live")
            self.assertEqual(result["status"], "SECURE_EGRESS_NOT_CONFIRMED")
            proc.assert_not_called()


    @patch.dict("os.environ", {"MADSC55_SECURE_EGRESS_CONFIRMED":"1"})
    @patch("v2.backup_text_sampler.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_subtitle_extraction_uses_protocol_whitelist(self, _which):
        with patch("v2.backup_text_sampler.public_dns_for_url", return_value=True):
            with patch("v2.backup_text_sampler.prefetch_hls", return_value="/tmp/review-sample.m3u8"):
                with patch("v2.backup_text_sampler.execute", return_value="") as execute:
                    sample("https://example.org/live", include_subtitles=True)
        self.assertEqual(execute.call_count, 2)
        subtitle_command = execute.call_args_list[1].args[0]
        self.assertIn("-protocol_whitelist", subtitle_command)
        index = subtitle_command.index("-protocol_whitelist")
        self.assertEqual(subtitle_command[index + 1], "file,crypto")
        self.assertEqual(subtitle_command[subtitle_command.index("-i") + 1],
                         "/tmp/review-sample.m3u8")
        self.assertNotIn("https://example.org/live", subtitle_command)

    @patch.dict("os.environ", {"MADSC55_SECURE_EGRESS_CONFIRMED":"1"})
    def test_prefetch_failure_never_runs_ffmpeg(self):
        with patch("v2.backup_text_sampler.public_dns_for_url", return_value=True):
            with patch("v2.backup_text_sampler.shutil.which", return_value="/usr/bin/ffmpeg"):
                with patch("v2.backup_text_sampler.prefetch_hls",
                           side_effect=UnsafeMediaSource("Unsafe source")):
                    with patch("v2.backup_text_sampler.execute") as run:
                        result=sample("https://example.org/live")
        self.assertEqual(result["status"],"SECURE_PREFETCH_FAILED")
        run.assert_not_called()

    def test_malformed_dns_labels_rejected(self):
        for url in ("https://bad..example.org/live", "https://-bad.example.org/live",
                    "https://bad-.example.org/live", "https://bad_host.example.org/live"):
            with self.subTest(url=url):
                self.assertFalse(valid_url(url))

    def test_sanitized_local_stream_whitelist_excludes_network(self):
        from v2.backup_text_sampler import STREAM_PROTOCOL_WHITELIST
        from v2.spoken_language_sample_review import STREAM_PROTOCOL_WHITELIST as speech_protocols
        self.assertEqual(STREAM_PROTOCOL_WHITELIST, speech_protocols)
        self.assertIn("file", STREAM_PROTOCOL_WHITELIST.split(","))
        for protocol in ("http", "https", "tcp", "tls", "concat"):
            self.assertNotIn(protocol, STREAM_PROTOCOL_WHITELIST.split(","))

    def test_legacy_ipv4_numeric_aliases_rejected(self):
        for url in ("http://127.1/live", "http://0x7f.0.0.1/live",
                    "http://0177.0.0.1/live", "https://127.0.0.1./live"):
            with self.subTest(url=url):
                self.assertFalse(valid_url(url))

    def test_public_dns_preflight_rejects_private_and_mixed_answers(self):
        import socket
        def answer(ip):
            family=socket.AF_INET6 if ":" in ip else socket.AF_INET
            return (family, socket.SOCK_STREAM, 6, "", (ip, 443))
        with patch("v2.backup_text_sampler.socket.getaddrinfo",
                   return_value=[answer("8.8.8.8"),answer("127.0.0.1")]):
            self.assertFalse(public_dns_for_url("https://example.org/live"))
        with patch("v2.backup_text_sampler.socket.getaddrinfo",
                   return_value=[answer("8.8.8.8")]):
            self.assertTrue(public_dns_for_url("https://example.org/live"))
        with patch("v2.backup_text_sampler.socket.getaddrinfo",
                   side_effect=socket.gaierror("No DNS")):
            self.assertFalse(public_dns_for_url("https://example.org/live"))

    @patch.dict("os.environ", {"MADSC55_SECURE_EGRESS_CONFIRMED":"1"})
    def test_unsafe_dns_target_stops_before_ffmpeg(self):
        with patch("v2.backup_text_sampler.public_dns_for_url", return_value=False):
            with patch("v2.backup_text_sampler.execute") as execute:
                result=sample("https://example.org/live")
        self.assertEqual(result["status"],"UNSAFE_DNS_TARGET")
        execute.assert_not_called()

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

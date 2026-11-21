import datetime
import socket
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
import unittest

from v2.pinned_http_proxy import PinnedHTTPProxy, ProxyPolicyError
from v2.turkish_media_sample_capture import MAX_BYTES, capture, validate_url


def dns_answer(address):
    def resolver(host, port, type=socket.SOCK_STREAM):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]
    return resolver


class CaptureTests(unittest.TestCase):
    def test_bad_urls(self):
        for url in ("file:///tmp/secret", "http://user:pass@example.com/live",
                    "ftp://host/live", "http://host/x#frag", "http://localhost/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_reject_private_and_local_destinations(self):
        for url in ("http://127.0.0.1/live", "http://10.0.0.1/live",
                    "http://192.168.1.1/live", "http://[::1]/live",
                    "https://localhost/live", "https://server.local/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_dns_hostname_allowed_as_root_capture_host(self):
        self.assertEqual(validate_url("https://example.com/live", {"example.com"}),
                         "https://example.com/live")

    def test_capture_requires_explicit_root_host_allowlist(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                capture("https://example.com/live", Path(d) / "sample.mkv",
                        runner=lambda *a, **k: SimpleNamespace(returncode=0),
                        which=lambda _: "/usr/bin/ffmpeg")

    def test_dns_hostname_requires_exact_proxy_allowlist(self):
        proxy = PinnedHTTPProxy({"example.com"}, resolver=dns_answer("8.8.8.8"))
        self.assertEqual(proxy.resolve("example.com", 443), "8.8.8.8")
        with self.assertRaises(ProxyPolicyError):
            proxy.resolve("cdn.example.com", 443)

    def test_private_dns_answer_rejected(self):
        proxy = PinnedHTTPProxy({"example.com"}, resolver=dns_answer("10.0.0.8"))
        with self.assertRaises(ProxyPolicyError):
            proxy.resolve("example.com", 443)

    def test_mixed_public_and_private_dns_answers_rejected(self):
        def resolver(host, port, type=socket.SOCK_STREAM):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.2", port)),
            ]
        proxy = PinnedHTTPProxy({"example.com"}, resolver=resolver)
        with self.assertRaises(ProxyPolicyError):
            proxy.resolve("example.com", 443)

    def test_dns_answer_change_fails_closed(self):
        answers = iter(("8.8.8.8", "1.1.1.1"))
        proxy = PinnedHTTPProxy({"example.com"},
                                resolver=lambda host, port, type=socket.SOCK_STREAM:
                                [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(answers), port))])
        self.assertEqual(proxy.resolve("example.com", 443), "8.8.8.8")
        with self.assertRaises(ProxyPolicyError):
            proxy.resolve("example.com", 443)

    def _start_upstream(self, handler):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        address = listener.getsockname()
        def serve():
            conn, _ = listener.accept()
            try:
                handler(conn)
            finally:
                conn.close()
                listener.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        return address, thread

    def test_http_proxy_forwards_only_origin_form_and_host(self):
        observed = {}
        def upstream(conn):
            data = bytearray()
            while b"\r\n\r\n" not in data:
                data.extend(conn.recv(1024))
            observed["request"] = bytes(data).decode("iso-8859-1")
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        address, thread = self._start_upstream(upstream)
        proxy = PinnedHTTPProxy({"example.com"}, {80}, resolver=dns_answer("8.8.8.8"),
                                connector=lambda _address, timeout: socket.create_connection(address, timeout))
        with proxy:
            host, port = proxy._server.server_address
            client = socket.create_connection((host, port), timeout=3)
            client.sendall(b"GET http://example.com/live.m3u8?x=1 HTTP/1.1\r\nHost: attacker.invalid\r\n\r\n")
            response = bytearray()
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                response.extend(chunk)
            client.close()
        thread.join(timeout=2)
        self.assertIn(b"200 OK", response)
        self.assertTrue(response.endswith(b"ok"))
        self.assertIn("GET /live.m3u8?x=1 HTTP/1.1", observed["request"])
        self.assertIn("Host: example.com", observed["request"])
        self.assertNotIn("attacker.invalid", observed["request"])

    def test_https_connect_tunnels_without_terminating_tls(self):
        def echo(conn):
            data = conn.recv(5)
            conn.sendall(data)
        address, thread = self._start_upstream(echo)
        proxy = PinnedHTTPProxy({"example.com"}, {443}, resolver=dns_answer("8.8.8.8"),
                                connector=lambda _address, timeout: socket.create_connection(address, timeout))
        with proxy:
            host, port = proxy._server.server_address
            client = socket.create_connection((host, port), timeout=3)
            client.sendall(b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n")
            response = bytearray()
            while b"\r\n\r\n" not in response:
                response.extend(client.recv(1024))
            self.assertIn(b"200 Connection Established", response)
            client.sendall(b"hello")
            self.assertEqual(client.recv(5), b"hello")
            client.close()
        thread.join(timeout=2)

    def test_invalid_ports_rejected(self):
        for url in ("http://8.8.8.8:abc/live", "http://8.8.8.8:65536/live",
                    "http://8.8.8.8:0/live"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_symlink_created_during_capture_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            target = Path(d) / "protected.txt"
            target.write_text("untouched")
            def runner(cmd, **kwargs):
                p.symlink_to(target)
                return SimpleNamespace(returncode=0)
            with self.assertRaises(ValueError):
                capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg", allowed_hosts=["8.8.8.8"])
            self.assertFalse(p.is_symlink())
            self.assertEqual(target.read_text(), "untouched")

    def test_redirects_are_bounded_and_proxy_is_mandatory(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                self.assertEqual(cmd[cmd.index("-max_redirect") + 1], "3")
                self.assertEqual(cmd[cmd.index("-fs") + 1], str(MAX_BYTES))
                proxy = cmd[cmd.index("-http_proxy") + 1]
                self.assertTrue(proxy.startswith("http://127.0.0.1:"))
                self.assertEqual(cmd[cmd.index("-tls_verify") + 1], "1")
                p.write_bytes(b"sample")
                return SimpleNamespace(returncode=0)
            capture("https://example.com/live", p, runner=runner,
                    which=lambda _: "/usr/bin/ffmpeg", allowed_hosts=["example.com", "cdn.example.com"],
                    allowed_ports=[8080])

    def test_reject_long_duration_and_timeout(self):
        with self.assertRaises(ValueError):
            capture("http://8.8.8.8/live", "/tmp/unused.mkv", seconds=13)
        with self.assertRaises(ValueError):
            capture("http://8.8.8.8/live", "/tmp/unused.mkv", timeout=18)

    def test_no_ffmpeg_is_not_success(self):
        r = capture("http://8.8.8.8/live", "/tmp/unused.mkv", which=lambda _: None, allowed_hosts=["8.8.8.8"])
        self.assertEqual(r["status"], "FFMPEG_UNAVAILABLE")

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            p.write_bytes(b"existing")
            with self.assertRaises(ValueError):
                capture("http://8.8.8.8/live", p, which=lambda _: "/usr/bin/ffmpeg", allowed_hosts=["8.8.8.8"])
            self.assertEqual(p.read_bytes(), b"existing")

    def test_success_is_not_language_proof(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                self.assertLessEqual(kwargs["timeout"], 17)
                p.write_bytes(b"sample")
                return SimpleNamespace(returncode=0)
            r = capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg", allowed_hosts=["8.8.8.8"])
            self.assertEqual(r["status"], "SAMPLE_CAPTURED_UNVERIFIED")
            stamp = datetime.datetime.fromisoformat(r["captured_at_utc"].replace("Z", "+00:00"))
            self.assertIsNotNone(stamp.tzinfo)
            self.assertFalse(r["language_verified"])
            self.assertFalse(r["asr_completed"])
            self.assertFalse(r["ocr_completed"])

    def test_oversize_capture_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                with p.open("wb") as output:
                    output.truncate(MAX_BYTES + 1)
                return SimpleNamespace(returncode=0)
            r = capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg", allowed_hosts=["8.8.8.8"])
            self.assertEqual(r["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())

    def test_failed_capture_cleans_partial_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.mkv"
            def runner(cmd, **kwargs):
                p.write_bytes(b"partial")
                return SimpleNamespace(returncode=1)
            r = capture("http://8.8.8.8/live", p, runner=runner, which=lambda _: "/usr/bin/ffmpeg", allowed_hosts=["8.8.8.8"])
            self.assertEqual(r["status"], "CAPTURE_FAILED")
            self.assertFalse(p.exists())


if __name__ == "__main__":
    unittest.main()

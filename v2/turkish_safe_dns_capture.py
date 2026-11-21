#!/usr/bin/env python3
"""Safe, bounded DNS media download for *finite or MPEG-TS* capture samples.

Every DNS answer must be a public IP. The connection uses a pinned numeric IP
while HTTPS certificate verification and SNI use the original hostname. HTTP
redirects, nested playlists, proxies and unbounded downloads are not supported.
Only local downloaded bytes may be passed to FFmpeg. No network on import.
"""
import http.client
import ipaddress
import os
from pathlib import Path
import re
import socket
import ssl
import time
from urllib.parse import urlsplit

MAX_REMOTE_BYTES = 12 * 1024 * 1024
CHUNK = 64 * 1024
_DENIED_SUFFIXES = (".localhost", ".local", ".internal", ".home.arpa")
_DENIED_CONTENT = ("text/", "application/vnd.apple.mpegurl",
                   "application/x-mpegurl", "application/dash+xml",
                   "application/xml", "application/json")
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.ASCII)


def _public_unicast(ip):
    # ipaddress.is_global alone is insufficient: multicast addresses can be
    # reported as global and must never be used as media egress destinations.
    return (ip.is_global and not ip.is_multicast and not ip.is_reserved and
            not ip.is_unspecified and not ip.is_loopback and
            not ip.is_link_local and getattr(ip, "ipv4_mapped", None) is None)


def parse_url(url):
    if not isinstance(url, str) or not 0 < len(url) <= 4096:
        raise ValueError("Invalid media URL")
    if any(ord(c) <= 32 or ord(c) in (92, 127) for c in url):
        raise ValueError("Media URL contains whitespace or control characters")
    try:
        parsed = urlsplit(url)
        if "%" in parsed.netloc:
            raise ValueError("Percent-encoded URL authority is forbidden")
        port = parsed.port
        host = parsed.hostname
    except ValueError as exc:
        raise ValueError("Malformed media URL") from exc
    if (parsed.scheme not in ("http", "https") or not host or
            parsed.username is not None or parsed.password is not None or parsed.fragment or
            port == 0):
        raise ValueError("Only HTTP(S) URLs without credentials or fragments")
    port = port or (443 if parsed.scheme == "https" else 80)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None:
        if not _public_unicast(ip):
            raise ValueError("IP address must be globally routable unicast")
        canonical_host = str(ip)
    else:
        try:
            canonical_host = host.encode("idna").decode("ascii").lower().rstrip(".")
        except UnicodeError as exc:
            raise ValueError("Invalid DNS hostname") from exc
        labels = canonical_host.split(".")
        if (len(canonical_host) > 253 or len(labels) < 2 or
                any(not _HOST_LABEL.fullmatch(label) for label in labels) or
                canonical_host == "localhost" or
                canonical_host.endswith(_DENIED_SUFFIXES) or
                canonical_host.endswith((".invalid", ".test"))):
            raise ValueError("Unsafe DNS hostname")
    target = (parsed.path or "/") + (("?" + parsed.query) if parsed.query else "")
    if (target.lower().split("?", 1)[0].endswith(
            (".m3u", ".m3u8", ".mpd", ".pls", ".xspf"))):
        raise ValueError("Nested adaptive media manifests are not supported")
    return parsed.scheme, canonical_host, port, target, ip


def resolve_public(host, *, resolver=socket.getaddrinfo):
    """Fail closed if ANY DNS answer is private, link-local or non-global."""
    try:
        answers = resolver(host, None, type=socket.SOCK_STREAM)
    except (OSError, ValueError) as exc:
        raise ValueError("DNS lookup failed") from exc
    if not answers or len(answers) > 32:
        raise ValueError("Missing or excessive DNS addresses")
    addresses = []
    for answer in answers:
        try:
            ip = ipaddress.ip_address(answer[4][0])
        except (IndexError, ValueError, TypeError, KeyError) as exc:
            raise ValueError("Invalid DNS answer") from exc
        if not _public_unicast(ip):
            raise ValueError("DNS response contains a non-public/unicast address")
        if str(ip) not in addresses:
            addresses.append(str(ip))
    return tuple(addresses)


class _PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, pinned_ip, timeout):
        super().__init__(host, port, timeout=timeout)
        self._pinned_ip = pinned_ip

    def connect(self):
        if self._tunnel_host:
            raise ValueError("Proxy tunnels are not allowed")
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, pinned_ip, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._pinned_ip = pinned_ip

    def connect(self):
        if self._tunnel_host:
            raise ValueError("Proxy tunnels are not allowed")
        raw = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        # TLS hostname validation and SNI MUST use the original DNS name.
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


def _strict_media_format(first):
    """Never allow FFmpeg to autodetect remote scripts/playlists as file input."""
    if len(first) >= 12 and first[4:8] == b"ftyp":
        return "mov"
    if first.startswith(b"\x1a\x45\xdf\xa3"):
        return "matroska"
    if len(first) >= 377 and first[0] == first[188] == first[376] == 0x47:
        return "mpegts"
    raise ValueError("Unsupported media container: only MP4, Matroska or MPEG-TS")


def download_bounded(url, output, *, timeout=17, resolver=socket.getaddrinfo,
                     connection_factory=None):
    """Download bounded bytes into a *new private temp file* only.

    No redirects, no playlist/segment fetch, no FFmpeg network requests.
    Fail closed for DNS rebinding (IP is pinned), private DNS answers,
    unsupported media or limits. Caller owns the temporary directory.
    """
    scheme, hostname, port, target, literal_ip = parse_url(url)
    if not 1 <= timeout <= 17:
        raise ValueError("Invalid timeout")
    addresses = (str(literal_ip),) if literal_ip is not None else resolve_public(hostname, resolver=resolver)
    chosen_ip = addresses[0]
    dest = Path(output)
    if dest.exists() or dest.is_symlink():
        raise ValueError("Refusing to overwrite downloaded input")
    if connection_factory is None:
        connection_factory = _PinnedHTTPS if scheme == "https" else _PinnedHTTP
    conn = connection_factory(hostname, port, chosen_ip, timeout)
    total = 0
    deadline = time.monotonic() + timeout
    try:
        host_header = hostname if ":" not in hostname else "[" + hostname + "]"
        if port not in (80, 443):
            host_header += ":" + str(port)
        conn.request("GET", target, headers={"Host": host_header,
                                              "Accept": "video/*,application/octet-stream",
                                              "User-Agent": "MADSC55-TV-V2-safe-capture"})
        response = conn.getresponse()
        if response.status not in (200, 206):
            raise ValueError("Media source refused or redirected")
        content_type = (response.getheader("Content-Type") or "").lower().split(";", 1)[0].strip()
        if content_type.startswith("text/") or content_type in _DENIED_CONTENT:
            raise ValueError("Media manifest or non-media response denied")
        length = response.getheader("Content-Length")
        if length is not None and (not length.isdecimal() or int(length) > MAX_REMOTE_BYTES):
            raise ValueError("Remote body length exceeds safe bound")
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as target_file:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Capture download deadline reached")
                if getattr(conn, "sock", None) is not None:
                    conn.sock.settimeout(min(remaining, 2))
                chunk = response.read(min(CHUNK, MAX_REMOTE_BYTES + 1 - total))
                if not chunk:
                    break
                if total == 0 and chunk.lstrip(b"\xef\xbb\xbf\r\n \t").startswith(b"#EXTM3U"):
                    raise ValueError("Nested HLS playlists are not supported")
                total += len(chunk)
                if total > MAX_REMOTE_BYTES:
                    raise ValueError("Remote media body exceeds safe bound")
                target_file.write(chunk)
        if total == 0:
            raise ValueError("Empty remote media body")
        with dest.open("rb") as check:
            fmt = _strict_media_format(check.read(512))
        return {"bytes": total, "pinned_ip_count": len(addresses), "input_format": fmt}
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    finally:
        conn.close()

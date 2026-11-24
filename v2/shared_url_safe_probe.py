#!/usr/bin/env python3
"""Bounded read-only IPTV MPEG-TS sampling with pinned public IP egress.

URLs are untrusted playlist input. No URL or token is written to reports/logs.
FFmpeg is never given a URL. This module does not verify broadcaster identity.
"""
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit, urljoin

MAX_MANIFEST = 256_000
MAX_SAMPLE = 3_000_000
ALLOWED_PORTS = {80, 443, 8000, 8080, 8443}
VIDEO_TYPES = {0x01, 0x02, 0x10, 0x1B, 0x24, 0x42, 0xD1}
AUDIO_TYPES = {0x03, 0x04, 0x0F, 0x11, 0x81, 0x87}


class SafeFetchError(Exception):
    """Only a fixed error code may be exposed in reports or console."""


def vetted_target(url):
    if (not isinstance(url, str) or not 0 < len(url) <= 4096
            or any(ord(c) <= 32 or ord(c) == 127 or c == "\\" for c in url)
            or any(bad in url.lower() for bad in ("%0a", "%0d", "%00"))):
        raise SafeFetchError("INVALID_URL")
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.fragment or "%" in parsed.netloc):
            raise SafeFetchError("INVALID_URL")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in ALLOWED_PORTS:
            raise SafeFetchError("UNSUPPORTED_PORT")
        host = parsed.hostname
        if (host.lower() in ("localhost", "localhost.localdomain")
                or host.lower().endswith((".local", ".localhost", ".internal", ".home.arpa"))):
            raise SafeFetchError("PRIVATE_HOST")
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        if not addresses or len(addresses) > 32:
            raise SafeFetchError("DNS_UNVERIFIED")
        ips = {item[4][0] for item in addresses}
        if not all(ipaddress.ip_address(ip).is_global for ip in ips):
            raise SafeFetchError("PRIVATE_IP")
        # Return only vetted numeric IPs; never reconnect using the DNS name.
        ip = sorted(ips)[0]
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        return parsed.scheme, host, port, ip, path
    except SafeFetchError:
        raise
    except (OSError, ValueError, UnicodeError, TypeError, IndexError):
        raise SafeFetchError("DNS_UNVERIFIED") from None


class PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, port, ip, timeout):
        super().__init__(host, port, timeout=timeout)
        self.pinned_ip = ip

    def connect(self):
        self.sock = socket.create_connection(
            (self.pinned_ip, self.port), timeout=self.timeout
        )


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, port, ip, timeout):
        super().__init__(host, port, timeout=timeout,
                         context=ssl.create_default_context())
        self.pinned_ip = ip

    def connect(self):
        raw = socket.create_connection(
            (self.pinned_ip, self.port), timeout=self.timeout
        )
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def bounded_get(url, limit=MAX_SAMPLE, timeout=6, *, report_http_status=False):
    """Pin DNS to a vetted IP, refuse redirects and cap response bytes."""
    scheme, host, port, ip, path = vetted_target(url)
    connection = (PinnedHTTPS if scheme == "https" else PinnedHTTP)(
        host, port, ip, timeout
    )
    try:
        connection.request(
            "GET", path,
            headers={"Accept-Encoding": "identity",
                     "Range": f"bytes=0-{limit - 1}",
                     "User-Agent": "MADSC55-TV-V2-IdentityAudit/1.0"}
        )
        response = connection.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            raise SafeFetchError("REDIRECT_BLOCKED")
        if response.status not in (200, 206):
            if report_http_status and response.status in (404, 410):
                raise SafeFetchError("HTTP_" + str(response.status))
            raise SafeFetchError("HTTP_UNAVAILABLE")
        if response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise SafeFetchError("ENCODING_BLOCKED")
        data = response.read(limit + 1)
        if len(data) > limit:
            data = data[:limit]
        if not data:
            raise SafeFetchError("EMPTY_RESPONSE")
        return data
    except SafeFetchError:
        raise
    except (OSError, ValueError, TimeoutError, ssl.SSLError,
            http.client.HTTPException):
        raise SafeFetchError("FETCH_FAILED") from None
    finally:
        connection.close()


def sample_transport_stream(url, fetch=bounded_get):
    """Resolve at most two HLS manifests; no keys, redirects, or nested schemes."""
    current = url
    for _ in range(3):
        chunk = fetch(current, MAX_SAMPLE)
        if not chunk.lstrip().startswith(b"#EXTM3U"):
            return chunk
        if len(chunk) > MAX_MANIFEST:
            raise SafeFetchError("HLS_MANIFEST_TOO_LARGE")
        text = chunk.decode("utf-8-sig", errors="replace")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if any(line.startswith("#EXT-X-KEY:") and "METHOD=NONE" not in line
               for line in lines):
            raise SafeFetchError("ENCRYPTED_HLS_UNSUPPORTED")
        if any(line.startswith("#EXT-X-MAP:") for line in lines):
            raise SafeFetchError("FMP4_UNSUPPORTED")
        urls = [urljoin(current, line) for line in lines
                if not line.startswith("#")]
        if not urls:
            raise SafeFetchError("HLS_WITHOUT_SEGMENTS")
        if any(line.startswith("#EXT-X-STREAM-INF:") for line in lines):
            current = urls[0]
            continue
        if not any(line.startswith("#EXTINF:") for line in lines):
            raise SafeFetchError("UNKNOWN_HLS_FORMAT")
        # Sample the most recent media segment of a live window.
        return fetch(urls[-1], MAX_SAMPLE)
    raise SafeFetchError("HLS_DEPTH_LIMIT")


def ts_sections(data, pids):
    """Reassemble bounded PSI sections across MPEG-TS packets (188 bytes)."""
    offset = next((i for i in range(min(188, len(data)))
                   if i + 376 < len(data)
                   and data[i] == data[i + 188] == data[i + 376] == 0x47),
                  None)
    if offset is None:
        return []
    buffers = {}
    sections = []
    for start in range(offset, len(data) - 187, 188):
        packet = data[start:start + 188]
        if packet[0] != 0x47:
            continue
        pid = ((packet[1] & 0x1F) << 8) | packet[2]
        if pid not in pids or packet[1] & 0x80:
            continue
        adaptation = (packet[3] >> 4) & 0x03
        if not (adaptation & 1):
            continue
        pos = 4
        if adaptation & 2:
            pos += 1 + packet[4]
        if pos >= 188:
            continue
        payload = packet[pos:]
        if packet[1] & 0x40:
            if not payload:
                continue
            pointer = payload[0]
            if pointer + 1 > len(payload):
                continue
            buffers[pid] = bytearray()
            payload = payload[1 + pointer:]
        if pid not in buffers:
            continue
        buffers[pid].extend(payload)
        while len(buffers[pid]) >= 3:
            b = buffers[pid]
            if b[0] == 0xFF:
                break
            total = 3 + (((b[1] & 0x0F) << 8) | b[2])
            if total < 12 or total > 4096:
                buffers[pid] = bytearray()
                break
            if len(b) < total:
                break
            sections.append((pid, bytes(b[:total])))
            buffers[pid] = bytearray(b[total:])
    return sections


def program_table(data):
    """Return real PAT/PMT video/audio PID evidence, not channel-name proof."""
    pat = {}
    for _, section in ts_sections(data, {0}):
        if section[0] != 0x00:
            continue
        for i in range(8, len(section) - 4, 4):
            if i + 4 > len(section) - 4:
                break
            service = (section[i] << 8) | section[i + 1]
            pmt_pid = ((section[i + 2] & 0x1F) << 8) | section[i + 3]
            if service:
                pat[service] = pmt_pid
    if not pat:
        return []
    programs = {}
    for pid, section in ts_sections(data, set(pat.values())):
        if section[0] != 0x02 or len(section) < 16:
            continue
        service = (section[3] << 8) | section[4]
        if pat.get(service) != pid:
            continue
        info_len = ((section[10] & 0x0F) << 8) | section[11]
        i = 12 + info_len
        videos, audios = set(), set()
        end = len(section) - 4
        while i + 5 <= end:
            typ = section[i]
            elem_pid = ((section[i + 1] & 0x1F) << 8) | section[i + 2]
            desc_len = ((section[i + 3] & 0x0F) << 8) | section[i + 4]
            if typ in VIDEO_TYPES:
                videos.add(elem_pid)
            if typ in AUDIO_TYPES:
                audios.add(elem_pid)
            i += 5 + desc_len
        programs[service] = {
            "program_number": service,
            "video_pids": sorted(videos),
            "audio_pids": sorted(audios),
        }
    return sorted(programs.values(), key=lambda x: x["program_number"])


def inspect_url(url, fetch=bounded_get):
    try:
        sample = sample_transport_stream(url, fetch)
        programs = program_table(sample)
        video_programs = [p for p in programs if p["video_pids"]]
        if len(video_programs) > 1 and len({
                tuple(p["video_pids"]) for p in video_programs}) > 1:
            status = "MULTIPLE_VIDEO_SERVICE_PIDS_OBSERVED"
        elif len(video_programs) == 1:
            status = "ONE_VIDEO_SERVICE_OBSERVED"
        elif programs:
            status = "PROGRAMS_WITHOUT_VIDEO_EVIDENCE"
        else:
            status = "NO_MPEGTS_PROGRAM_EVIDENCE"
        return {
            "status": status, "sample_bytes": len(sample),
            "programs": programs,
            "distinct_broadcasters_verified": False,
            "audio_video_decoded_verified": False,
        }
    except SafeFetchError as exc:
        return {
            "status": str(exc), "sample_bytes": 0, "programs": [],
            "distinct_broadcasters_verified": False,
            "audio_video_decoded_verified": False,
        }

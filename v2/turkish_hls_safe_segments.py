#!/usr/bin/env python3
"""Opt-in, bounded, unencrypted HLS MPEG-TS capture without FFmpeg network egress.

This is deliberately a narrow safe subset: same-origin relative .ts segments,
one media playlist only, no keys, maps, byte ranges, redirects or nested lists.
Every HTTP(S) request uses the public-IP-pinned transport; ffmpeg receives
only a local MPEG-TS file. This does NOT enable the #497 685-channel live retry.
"""
import http.client
import os
from pathlib import Path
import re
import shutil
import socket
import tempfile
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlsplit

from v2.turkish_safe_dns_capture import (
    MAX_REMOTE_BYTES, _PinnedHTTP, _PinnedHTTPS, CHUNK,
    download_bounded, parse_url, resolve_public,
)

MAX_MANIFEST_BYTES = 64 * 1024
MAX_SEGMENTS = 8
MAX_PLAYLIST_SECONDS = Decimal("120")
MAX_ELAPSED_SECONDS = 60
_SEGMENT_SUFFIX = ".ts"
_ALLOWED_SINGLE_TAGS = frozenset({
    "#EXT-X-ENDLIST", "#EXT-X-INDEPENDENT-SEGMENTS",
})
_ALLOWED_PREFIX_TAGS = {
    "#EXT-X-VERSION:": (r"[0-9]{1,2}",),
    "#EXT-X-TARGETDURATION:": (r"[0-9]{1,2}",),
    "#EXT-X-MEDIA-SEQUENCE:": (r"[0-9]{1,15}",),
    "#EXT-X-PLAYLIST-TYPE:": (r"(VOD|EVENT)",),
}
_ALLOWED_MANIFEST_TYPES = frozenset({
    "", "application/vnd.apple.mpegurl", "application/x-mpegurl",
    "audio/x-mpegurl", "text/plain", "application/octet-stream",
})


def _manifest_origin(url):
    if not isinstance(url, str) or not urlsplit(url).path.lower().endswith(".m3u8"):
        raise ValueError("Only explicit HLS .m3u8 media playlists are supported")
    scheme, hostname, port, target, literal = parse_url(url, allow_playlist=True)
    return scheme, hostname, port, target, literal


def _same_origin_ts_url(manifest_url, origin, reference):
    if (not isinstance(reference, str) or not reference or
            len(reference) > 4096 or reference.startswith("/") or
            any(ord(c) <= 32 or ord(c) == 127 or c == "\\" for c in reference)):
        raise ValueError("Unsafe HLS segment reference")
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or parsed.fragment or not parsed.path:
        raise ValueError("HLS segments must use relative same-origin references")
    # Do not normalize tricky relative paths or percent-encoded separators.
    if ("%" in parsed.path or
            any(part in (".", "..") for part in parsed.path.split("/")) or
            not parsed.path.lower().endswith(_SEGMENT_SUFFIX)):
        raise ValueError("Only simple unencrypted relative MPEG-TS segments are supported")
    absolute = urljoin(manifest_url, reference)
    segment = parse_url(absolute)
    if segment[:3] != origin[:3]:
        raise ValueError("Cross-origin HLS segment request refused")
    return absolute


def parse_hls_media_playlist(raw, manifest_url):
    """Validate every URI *before* allowing the first segment request."""
    origin = _manifest_origin(manifest_url)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_MANIFEST_BYTES:
        raise ValueError("Missing or oversized HLS manifest")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("HLS manifest must be UTF-8") from exc
    if "\ufeff" in text or any(ord(c) < 32 and c not in "\r\n" for c in text):
        raise ValueError("HLS manifest has unsafe control characters")
    lines = text.splitlines()
    if not lines or lines[0] != "#EXTM3U":
        raise ValueError("Expected HLS media playlist header")
    segments = []
    pending = None
    duration_total = Decimal(0)
    endlist = False
    target_duration_seen = False
    for line in lines[1:]:
        if not line:
            continue
        if endlist:
            raise ValueError("Extra data after HLS end marker")
        if pending is not None:
            if line.startswith("#"):
                raise ValueError("HLS segment must immediately follow EXTINF")
            address = _same_origin_ts_url(manifest_url, origin, line)
            if address in segments:
                raise ValueError("Duplicate HLS media segment")
            segments.append(address)
            if len(segments) > MAX_SEGMENTS:
                raise ValueError("Too many HLS segments for bounded capture")
            pending = None
            continue
        if line.startswith("#EXTINF:"):
            if not target_duration_seen or "," not in line:
                raise ValueError("Missing target duration or malformed EXTINF")
            length = line[len("#EXTINF:"):].split(",", 1)[0]
            try:
                duration = Decimal(length)
            except InvalidOperation as exc:
                raise ValueError("Invalid HLS segment duration") from exc
            if not duration.is_finite() or not 0 < duration <= 30:
                raise ValueError("HLS segment duration outside limits")
            duration_total += duration
            if duration_total > MAX_PLAYLIST_SECONDS:
                raise ValueError("Excessive total HLS duration")
            pending = duration
        elif line in _ALLOWED_SINGLE_TAGS:
            if line == "#EXT-X-ENDLIST":
                endlist = True
        elif any(line.startswith(prefix) for prefix in _ALLOWED_PREFIX_TAGS):
            prefix = next(key for key in _ALLOWED_PREFIX_TAGS if line.startswith(key))
            value = line[len(prefix):]
            if not re.fullmatch(_ALLOWED_PREFIX_TAGS[prefix][0], value, re.ASCII):
                raise ValueError("Malformed HLS metadata")
            if prefix == "#EXT-X-TARGETDURATION:":
                if target_duration_seen or not 1 <= int(value) <= 30:
                    raise ValueError("Invalid HLS target duration")
                target_duration_seen = True
        else:
            # Explicitly deny KEY/SESSION-KEY/MAP/STREAM-INF/MEDIA/RENDITION,
            # BYTERANGE, DISCONTINUITY, DEFINE and every unknown URI-carrying tag.
            raise ValueError("Unsupported or unsafe HLS playlist directive")
    if pending is not None or not segments or not target_duration_seen:
        raise ValueError("Incomplete or empty HLS media playlist")
    return tuple(segments)


def fetch_hls_manifest_bounded(url, *, timeout=12, resolver=socket.getaddrinfo,
                               connection_factory=None):
    """Fetch one tiny manifest through a pinned public-IP HTTP(S) connection."""
    scheme, host, port, target, ip = _manifest_origin(url)
    if type(timeout) is not int or not 1 <= timeout <= 17:
        raise ValueError("Invalid HLS manifest timeout")
    addresses = (str(ip),) if ip is not None else resolve_public(host, resolver=resolver)
    factory = connection_factory or (_PinnedHTTPS if scheme == "https" else _PinnedHTTP)
    conn = factory(host, port, addresses[0], timeout)
    try:
        host_header = host if ":" not in host else "[" + host + "]"
        if port != (443 if scheme == "https" else 80):
            host_header += ":" + str(port)
        conn.request("GET", target, headers={
            "Host": host_header,
            "Accept": "application/vnd.apple.mpegurl,application/x-mpegurl,text/plain",
            "User-Agent": "MADSC55-TV-V2-safe-HLS",
        })
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("HLS manifest redirected or not available")
        kind = (response.getheader("Content-Type") or "").split(";", 1)[0].lower().strip()
        if kind not in _ALLOWED_MANIFEST_TYPES:
            raise ValueError("Unexpected HLS manifest MIME type")
        length = response.getheader("Content-Length")
        if length is not None and (
                not length.isdecimal() or int(length) > MAX_MANIFEST_BYTES):
            raise ValueError("HLS manifest exceeds maximum size")
        deadline = time.monotonic() + timeout
        chunks = []
        size = 0
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("HLS manifest fetch deadline")
            if getattr(conn, "sock", None) is not None:
                conn.sock.settimeout(min(remaining, 2))
            chunk = response.read(min(4096, MAX_MANIFEST_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_MANIFEST_BYTES:
                raise ValueError("HLS manifest exceeds maximum size")
            chunks.append(chunk)
        raw = b"".join(chunks)
        if not raw:
            raise ValueError("Empty HLS media manifest")
        return raw, {"manifest_bytes": len(raw), "manifest_public_dns_answers": len(addresses)}
    finally:
        conn.close()


def download_hls_ts_bounded(url, output, *, timeout=12, max_bytes=MAX_REMOTE_BYTES,
                            resolver=socket.getaddrinfo, connection_factory=None):
    """Create one private local TS file. No remote URL ever reaches FFmpeg."""
    dest = Path(output)
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_REMOTE_BYTES:
        raise ValueError("Invalid HLS total byte limit")
    if dest.exists() or dest.is_symlink() or not dest.parent.is_dir():
        raise ValueError("Refusing unsafe HLS output path")
    started = time.monotonic()
    manifest, receipt = fetch_hls_manifest_bounded(
        url, timeout=timeout, resolver=resolver, connection_factory=connection_factory)
    segments = parse_hls_media_playlist(manifest, url)
    deadline = started + MAX_ELAPSED_SECONDS
    total = 0
    with tempfile.TemporaryDirectory(prefix="v2-hls-ts-", dir=dest.parent) as private:
        concat = Path(private) / "combined.ts"
        with concat.open("xb") as joined:
            for index, segment_url in enumerate(segments):
                remaining_time = deadline - time.monotonic()
                if remaining_time < 1:
                    raise TimeoutError("HLS capture total deadline")
                part = Path(private) / ("part-%02d.ts" % index)
                info = download_bounded(
                    segment_url, part, timeout=max(1, min(17, int(remaining_time))),
                    resolver=resolver, connection_factory=connection_factory,
                    max_bytes=max_bytes - total)
                if info["input_format"] != "mpegts":
                    raise ValueError("HLS segment is not MPEG-TS")
                with part.open("rb") as source:
                    shutil.copyfileobj(source, joined, CHUNK)
                total += info["bytes"]
                part.unlink()
        if not 0 < total <= max_bytes:
            raise ValueError("HLS byte budget exceeded")
        os.link(concat, dest, follow_symlinks=False)  # atomic no-clobber
    return {
        "input_format": "mpegts",
        "bytes": total,
        "segment_count": len(segments),
        "manifest_bytes": receipt["manifest_bytes"],
        "manifest_public_dns_answers": receipt["manifest_public_dns_answers"],
        "hls_unencrypted_ts_only": True,
    }

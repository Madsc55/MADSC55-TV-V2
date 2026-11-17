#!/usr/bin/env python3
"""Bounded HLS prefetch with pinned public IP, no redirects or FFmpeg network input.

Only the resulting local manifest may be handed to FFmpeg. Unsupported HLS
features fail closed, never silently read arbitrary remote or local URLs.
"""
import http.client
import ipaddress
import math
import re
from pathlib import Path
import socket
import ssl
from urllib.parse import urljoin, urlsplit

MAX_MANIFEST_BYTES = 192 * 1024
MAX_SEGMENT_BYTES = 4 * 1024 * 1024
MAX_SEGMENTS = 8
MAX_TOTAL_BYTES = 20 * 1024 * 1024
LOCAL_PROTOCOLS = "file,crypto"

class UnsafeMediaSource(ValueError):
    pass

def public_endpoints(url):
    try:
        from .backup_text_sampler import valid_url
    except ImportError:
        from backup_text_sampler import valid_url
    if not valid_url(url):
        raise UnsafeMediaSource("Invalid external media URL")
    parsed = urlsplit(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        answers = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
        ips = [row[4][0] for row in answers]
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise UnsafeMediaSource("Private or ambiguous DNS address")
        return parsed, port, ips
    except (OSError, IndexError, TypeError, ValueError) as exc:
        raise UnsafeMediaSource("Unsafe or unresolved media hostname") from exc

def fetch_pinned(url, limit):
    """Fetch from a vetted *numeric* public IP, maintaining HTTPS hostname checks.

    No proxy, automatic redirect or second hostname-based socket resolution.
    """
    parsed, port, ips = public_endpoints(url)
    ip = ips[0]
    if parsed.scheme == "https":
        conn = http.client.HTTPSConnection(parsed.hostname, port, timeout=8,
                                           context=ssl.create_default_context())
    else:
        conn = http.client.HTTPConnection(parsed.hostname, port, timeout=8)
    conn._create_connection = lambda _target, timeout=8, source_address=None: (
        socket.create_connection((ip, port), timeout, source_address))
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    try:
        conn.request("GET", path, headers={"Accept-Encoding": "identity",
                                          "User-Agent": "MADSC55-V2-safe-review/1.0"})
        response = conn.getresponse()
        if response.status != 200:
            raise UnsafeMediaSource("Media request declined or redirected")
        declared = response.getheader("Content-Length")
        if declared is not None and (not declared.isdecimal() or int(declared) > limit):
            raise UnsafeMediaSource("Media payload exceeds byte limit")
        body = response.read(limit + 1)
        if len(body) > limit:
            raise UnsafeMediaSource("Media payload exceeds byte limit")
        return body
    except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
        raise UnsafeMediaSource("Media download unavailable") from exc
    finally:
        conn.close()

def _media_segments(text, base_url, remaining_depth, getter):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or lines[0] != "#EXTM3U" or len(lines) > 5000:
        raise UnsafeMediaSource("Not a bounded HLS playlist")
    # I-FRAME-STREAM-INF describes an alternate trick-play rendition.
    # We neither fetch nor copy it into the sanitized local manifest.
    forbidden = ("#EXT-X-KEY", "#EXT-X-SESSION-KEY", "#EXT-X-MAP",
                 "#EXT-X-BYTERANGE", "#EXT-X-PART", "#EXT-X-PRELOAD-HINT")
    for line in lines:
        for tag in forbidden:
            if line.startswith(tag):
                raise UnsafeMediaSource("Unsupported HLS directive " + tag)
    if any(line.startswith("#EXT-X-STREAM-INF") for line in lines):
        if remaining_depth <= 0:
            raise UnsafeMediaSource("Nested HLS depth exceeded")
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                if i + 1 >= len(lines) or lines[i + 1].startswith("#"):
                    raise UnsafeMediaSource("Invalid HLS variant")
                url = urljoin(base_url, lines[i + 1])
                data = getter(url, MAX_MANIFEST_BYTES)
                if len(data) > MAX_MANIFEST_BYTES:
                    raise UnsafeMediaSource("Oversized HLS variant")
                try:
                    child = data.decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    raise UnsafeMediaSource("Invalid HLS encoding") from exc
                return _media_segments(child, url, remaining_depth - 1, getter)
        raise UnsafeMediaSource("No HLS variant")
    segments = []
    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF:"):
            continue
        if i + 1 >= len(lines) or lines[i + 1].startswith("#"):
            raise UnsafeMediaSource("Invalid segment reference")
        try:
            duration = float(line.split(":", 1)[1].split(",", 1)[0])
        except ValueError as exc:
            raise UnsafeMediaSource("Invalid segment duration") from exc
        if not math.isfinite(duration) or not 0 < duration <= 120:
            raise UnsafeMediaSource("Invalid segment duration")
        url = urljoin(base_url, lines[i + 1])
        if not urlsplit(url).path.lower().endswith((".ts", ".mpegts", ".m2ts")):
            raise UnsafeMediaSource("Unsupported HLS segment format")
        segments.append((duration, url))
    if not segments:
        raise UnsafeMediaSource("No safe HLS segments")
    return segments

def prefetch_hls(url, output_dir, seconds=8, getter=fetch_pinned):
    """Create a private local HLS sample. Manifest contains no network URLs."""
    if not isinstance(seconds, int) or not 2 <= seconds <= 30:
        raise UnsafeMediaSource("Invalid sample duration")
    output_dir = Path(output_dir)
    if not output_dir.is_dir() or output_dir.is_symlink():
        raise UnsafeMediaSource("Unsafe local destination")
    manifest_bytes = getter(url, MAX_MANIFEST_BYTES)
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise UnsafeMediaSource("Oversized HLS manifest")
    try:
        manifest = manifest_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsafeMediaSource("Invalid HLS encoding") from exc
    segments = _media_segments(manifest, url, 2, getter)
    lines = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-X-TARGETDURATION:120",
             "#EXT-X-MEDIA-SEQUENCE:0"]
    count_bytes, count_seconds = 0, 0.0
    for i, (duration, remote) in enumerate(segments[:MAX_SEGMENTS]):
        data = getter(remote, MAX_SEGMENT_BYTES)
        count_bytes += len(data)
        if not data or len(data) > MAX_SEGMENT_BYTES or count_bytes > MAX_TOTAL_BYTES:
            raise UnsafeMediaSource("Empty or oversized HLS media")
        filename = f"segment-{i:02d}.ts"
        with (output_dir / filename).open("xb") as destination:
            destination.write(data)
        lines.extend([f"#EXTINF:{duration:.3f},", filename])
        count_seconds += duration
        if count_seconds >= seconds:
            break
    if count_seconds <= 0:
        raise UnsafeMediaSource("No sample media")
    lines.append("#EXT-X-ENDLIST")
    path = output_dir / "review-sample.m3u8"
    with path.open("x", encoding="utf-8") as destination:
        destination.write("\n".join(lines) + "\n")
    return path


MAX_SUBTITLE_BYTES = 128 * 1024
MAX_SUBTITLE_SEGMENTS = 2

def subtitle_observations(url, getter=fetch_pinned):
    """Safely fetch at most two WebVTT subtitle cues from a named HLS track.

    Only transient text is returned to the caller's review-hint classifier.
    The fetcher pins public IPs and refuses redirects at each nested request.
    """
    master_bytes = getter(url, MAX_MANIFEST_BYTES)
    if len(master_bytes) > MAX_MANIFEST_BYTES:
        raise UnsafeMediaSource("Subtitle master manifest exceeds byte limit")
    try:
        master = master_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UnsafeMediaSource("Invalid HLS subtitle manifest encoding") from exc
    if not master.startswith("#EXTM3U"):
        raise UnsafeMediaSource("Not an HLS subtitle master")
    entries = []
    for line in master.splitlines():
        if not line.startswith("#EXT-X-MEDIA:"):
            continue
        attributes = dict(
            (key.upper(), value.strip('"'))
            for key, value in re.findall(r'([A-Za-z0-9-]+)=("[^"]*"|[^,]*)',
                                          line.partition(":")[2])
        )
        if attributes.get("TYPE") != "SUBTITLES" or not attributes.get("URI"):
            continue
        tag = attributes.get("LANGUAGE", "")
        if len(tag) > 32 or any(ord(ch) < 33 or ord(ch) > 126 for ch in tag):
            raise UnsafeMediaSource("Invalid subtitle language tag")
        entries.append((tag, urljoin(url, attributes["URI"])))
    # Prioritize the Turkish track only as a sampling hint; never approval.
    entries.sort(key=lambda pair: not pair[0].lower().startswith("tr"))
    found = []
    for tag, playlist_url in entries[:2]:
        body = getter(playlist_url, MAX_MANIFEST_BYTES)
        if len(body) > MAX_MANIFEST_BYTES:
            raise UnsafeMediaSource("Subtitle playlist too large")
        try:
            playlist = body.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UnsafeMediaSource("Invalid subtitle playlist encoding") from exc
        lines = [line.strip() for line in playlist.splitlines() if line.strip()]
        if not lines or lines[0] != "#EXTM3U" or len(lines) > 1000:
            raise UnsafeMediaSource("Invalid WebVTT media playlist")
        if any(line.startswith(("#EXT-X-KEY", "#EXT-X-MAP", "#EXT-X-BYTERANGE",
                                "#EXT-X-PART", "#EXT-X-PRELOAD-HINT"))
               for line in lines):
            raise UnsafeMediaSource("Unsupported WebVTT playlist feature")
        segments = []
        for index, line in enumerate(lines):
            if not line.startswith("#EXTINF:"):
                continue
            if index + 1 >= len(lines) or lines[index + 1].startswith("#"):
                raise UnsafeMediaSource("Malformed WebVTT segment")
            ref = urljoin(playlist_url, lines[index + 1])
            if not urlsplit(ref).path.lower().endswith((".vtt", ".webvtt")):
                raise UnsafeMediaSource("Unsupported subtitle segment format")
            segments.append(ref)
        if not segments:
            continue
        cue_text = []
        for ref in segments[:MAX_SUBTITLE_SEGMENTS]:
            media = getter(ref, MAX_SUBTITLE_BYTES)
            if len(media) > MAX_SUBTITLE_BYTES:
                raise UnsafeMediaSource("WebVTT payload exceeds limit")
            try:
                vtt = media.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise UnsafeMediaSource("Invalid WebVTT encoding") from exc
            if not vtt.startswith("WEBVTT") or "-->" not in vtt:
                continue
            # Avoid treating the header alone as evidence of actual subtitles.
            lines_text = [line for line in vtt.splitlines()
                          if line.strip() and "-->" not in line and
                          line.strip() not in ("WEBVTT", "STYLE", "REGION") and
                          not line.strip().isdigit() and
                          not line.lstrip().startswith(("NOTE", "X-TIMESTAMP-MAP"))]
            if any(any(ch.isalpha() for ch in line) for line in lines_text):
                cue_text.append("\n".join(lines_text))
        if cue_text:
            found.append({"kind": "SUBTITLE", "text": "\n".join(cue_text)[:4096],
                          "language_tag": tag})
    return found

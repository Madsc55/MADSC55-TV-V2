#!/usr/bin/env python3
"""Opt-in bounded single-stream sample capture for later ASR/OCR review.

No automatic channel classification, no network activity on import, no playlist
or archive writes. Capture alone is NOT proof of speech language or OCR.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

from v2.pinned_http_proxy import PinnedHTTPProxy, normalize_host

MAX_SECONDS = 12
MAX_TIMEOUT = 17
MAX_BYTES = 12 * 1024 * 1024
MAX_REDIRECTS = 3
MAX_PROXY_BYTES = 64 * 1024 * 1024


def validate_url(url, allowed_hosts=None):
    if not isinstance(url, str) or len(url) > 4096:
        raise ValueError("Invalid stream URL")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only HTTP(S) URLs without embedded credentials are allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid URL port") from exc
    if port == 0:
        raise ValueError("Port zero is not a valid stream endpoint")
    if parsed.fragment:
        raise ValueError("URL fragments are not supported")
    host = normalize_host(parsed.hostname)
    if allowed_hosts is not None:
        permitted = {normalize_host(item) for item in allowed_hosts}
        if host not in permitted:
            raise ValueError("Hostname is outside the explicit capture allowlist")
    return url


def capture(url, destination, *, seconds=4, timeout=17, runner=subprocess.run, which=shutil.which,
            include_subtitles=False, allowed_hosts=(), allowed_ports=()):
    parsed = urlsplit(url) if isinstance(url, str) else None
    if parsed is None or not parsed.hostname:
        raise ValueError("Invalid stream URL")
    root_host = normalize_host(parsed.hostname)
    if not isinstance(allowed_hosts, (list, tuple, set, frozenset)) or not allowed_hosts:
        raise ValueError("An explicit exact-host allowlist is required")
    hosts = {normalize_host(item) for item in allowed_hosts}
    if root_host not in hosts:
        raise ValueError("Root hostname must be explicitly allowlisted")
    root_port = parsed.port or (443 if parsed.scheme == "https" else 80)
    ports = {80, 443, root_port}
    if not isinstance(allowed_ports, (list, tuple, set, frozenset)):
        raise ValueError("Allowed ports must be an explicit collection")
    for item in allowed_ports:
        if type(item) is not int or not 1 <= item <= 65535:
            raise ValueError("Invalid allowed port")
        ports.add(item)
    validate_url(url, allowed_hosts=hosts)
    if type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS:
        raise ValueError("Sample duration must be 1..12 seconds")
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT:
        raise ValueError("Timeout must be 1..17 seconds")
    if type(include_subtitles) is not bool:
        raise ValueError("Invalid subtitle selection")
    executable = which("ffmpeg")
    if not executable:
        return {"status": "FFMPEG_UNAVAILABLE", "language_verified": False, "device_verified": False}
    dest = Path(destination)
    if dest.is_absolute() and any(part in ("..",) for part in dest.parts):
        raise ValueError("Invalid output path")
    if dest.exists() or dest.is_symlink():
        raise ValueError("Refusing to overwrite existing file")
    if dest.suffix.lower() != ".mkv" or not dest.parent.is_dir():
        raise ValueError("Output must be a new .mkv file in an existing directory")
    with PinnedHTTPProxy(hosts, ports, timeout=min(timeout, 4),
                         max_bytes=MAX_PROXY_BYTES, max_seconds=timeout) as proxy:
        cmd = [executable, "-nostdin", "-hide_banner", "-loglevel", "error",
               "-rw_timeout", str(timeout * 1000000), "-http_proxy", proxy.url,
               "-max_redirect", str(MAX_REDIRECTS), "-tls_verify", "1",
               "-i", url, "-t", str(seconds), "-fs", str(MAX_BYTES),
               "-map", "0:v:0?", "-map", "0:a:0?", "-c:v", "mpeg4", "-q:v", "12",
               "-c:a", "aac", "-b:a", "48k"]
        if include_subtitles:
            cmd.extend(["-map", "0:s?", "-c:s", "copy"])
        cmd.extend(["-n", str(dest)])
        try:
            result = runner(cmd, capture_output=True, timeout=timeout, check=False)
            if dest.is_symlink():
                dest.unlink(missing_ok=True)
                raise ValueError("Capture output cannot be a symlink")
            size = dest.stat().st_size if dest.is_file() else 0
            if result.returncode != 0 or not 0 < size <= MAX_BYTES:
                dest.unlink(missing_ok=True)
                return {"status": "CAPTURE_FAILED", "language_verified": False, "device_verified": False}
            return {"status": "SAMPLE_CAPTURED_UNVERIFIED", "bytes": size,
                    "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "sample_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
                    "url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
                    "language_verified": False, "device_verified": False,
                    "asr_completed": False, "ocr_completed": False}
        except (subprocess.TimeoutExpired, OSError):
            dest.unlink(missing_ok=True)
            return {"status": "CAPTURE_FAILED", "language_verified": False, "device_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=int, default=4)
    parser.add_argument("--include-subtitles", action="store_true", help="Retain available embedded tracks")
    parser.add_argument("--allowed-host", action="append", required=True,
                        help="Exact approved root/CDN hostname; repeat for each permitted host")
    parser.add_argument("--allowed-port", action="append", type=int, default=[],
                        help="Additional explicit TCP port allowed for redirects/subresources")
    args = parser.parse_args()
    print(json.dumps(capture(args.url, args.output, seconds=args.seconds,
                             include_subtitles=args.include_subtitles,
                             allowed_hosts=args.allowed_host,
                             allowed_ports=args.allowed_port), sort_keys=True))


if __name__ == "__main__":
    main()

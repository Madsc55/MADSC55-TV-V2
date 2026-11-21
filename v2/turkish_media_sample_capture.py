#!/usr/bin/env python3
"""Opt-in bounded single-stream sample capture for later ASR/OCR review.

No automatic channel classification, no network activity on import, no playlist
or archive writes. Capture alone is NOT proof of speech language or OCR.
"""
import argparse
import os
import tempfile
import datetime
import hashlib
import json
import ipaddress
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit
from v2.turkish_safe_dns_capture import download_bounded, parse_url

MAX_SECONDS = 12
MAX_TIMEOUT = 17
MAX_BYTES = 12 * 1024 * 1024

def validate_url(url):
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise ValueError("Invalid stream URL")
    # urlsplit() silently strips some ASCII controls. FFmpeg receives the exact
    # original bytes; reject ambiguous authority/path delimiters before parsing.
    if any(ord(char) <= 32 or ord(char) == 127 or char == "\\" for char in url):
        raise ValueError("Control characters, whitespace and backslashes are forbidden in stream URLs")
    parsed = urlsplit(url)
    if "%" in parsed.netloc:
        raise ValueError("Percent-encoded URL authority is forbidden")
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
    if parsed.hostname.lower() == "localhost" or parsed.hostname.lower().endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local hostnames are not supported")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        # DNS names may be used ONLY through the pinned, local-file-only
        # transport below. No DNS is resolved during syntax validation.
        parse_url(url)
        return url
    if not address.is_global:
        raise ValueError("Non-public IP addresses are not supported")
    return url

def _capture_domain(url, dest, *, seconds, timeout, executable, runner,
                    resolver=None, connection_factory=None, include_subtitles=False):
    """Pinned-IP download, then FFmpeg strictly on local bytes, never network."""
    with tempfile.TemporaryDirectory(prefix="v2-capture-", dir=dest.parent) as private:
        source = Path(private) / "source.bin"
        output = Path(private) / "decoded.mkv"
        options = {}
        if resolver is not None:
            options["resolver"] = resolver
        if connection_factory is not None:
            options["connection_factory"] = connection_factory
        info = download_bounded(url, source, timeout=timeout, **options)
        cmd = [executable, "-nostdin", "-hide_banner", "-loglevel", "error",
               "-protocol_whitelist", "file", "-f", info["input_format"], "-i", str(source),
               "-t", str(seconds), "-fs", str(MAX_BYTES),
               "-map", "0:v:0?", "-map", "0:a:0?", "-c:v", "mpeg4",
               "-q:v", "12", "-c:a", "aac", "-b:a", "48k"]
        if include_subtitles:
            cmd.extend(["-map", "0:s?", "-c:s", "copy"])
        cmd.extend(["-n", str(output)])
        result = runner(cmd, capture_output=True, timeout=timeout, check=False)
        if (result.returncode != 0 or output.is_symlink() or not output.is_file() or
                not 0 < output.stat().st_size <= MAX_BYTES):
            return {"status": "CAPTURE_FAILED", "language_verified": False,
                    "device_verified": False}
        # Hard-link creation is exclusive: no overwrite if the final name was
        # created during the download or decode. The private staging directory
        # is owned by this process; no path in the user playlist is modified.
        try:
            os.link(output, dest, follow_symlinks=False)
        except FileExistsError as exc:
            raise ValueError("Output path appeared during capture") from exc
        sample = dest.read_bytes()
        return {
            "status": "SAMPLE_CAPTURED_UNVERIFIED",
            "bytes": len(sample),
            "downloaded_source_bytes": info["bytes"],
            "dns_public_answers": info["pinned_ip_count"],
            "captured_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sample_sha256": hashlib.sha256(sample).hexdigest(),
            "url_sha256": hashlib.sha256(url.encode("utf-8")).hexdigest(),
            "language_verified": False, "device_verified": False,
            "asr_completed": False, "ocr_completed": False,
        }


def capture(url, destination, *, seconds=4, timeout=17, runner=subprocess.run, which=shutil.which,
            include_subtitles=False, resolver=None, connection_factory=None):
    validate_url(url)
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
    # Apply the identical public-IP-pinned, no-redirect local-file transport
    # for BOTH DNS hostnames and numeric IP literals. A public literal may
    # still return HLS with private/cross-host children; never pass that URL
    # directly to FFmpeg even with an FFmpeg protocol whitelist.
    try:
        return _capture_domain(url, dest, seconds=seconds, timeout=timeout,
                               executable=executable, runner=runner,
                               resolver=resolver, connection_factory=connection_factory,
                               include_subtitles=include_subtitles)
    except (OSError, TimeoutError, subprocess.TimeoutExpired):
        return {"status": "CAPTURE_FAILED", "language_verified": False,
                "device_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=int, default=4)
    parser.add_argument("--include-subtitles", action="store_true", help="Retain available embedded tracks")
    args = parser.parse_args()
    print(json.dumps(capture(args.url, args.output, seconds=args.seconds,
                             include_subtitles=args.include_subtitles), sort_keys=True))

if __name__ == "__main__":
    main()

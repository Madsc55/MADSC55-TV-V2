#!/usr/bin/env python3
"""Opt-in bounded single-stream sample capture for later ASR/OCR review.

No automatic channel classification, no network activity on import, no playlist
or archive writes. Capture alone is NOT proof of speech language or OCR.
"""
import argparse
import json
import ipaddress
from pathlib import Path
import shutil
import subprocess
from urllib.parse import urlsplit

MAX_SECONDS = 12
MAX_TIMEOUT = 17
MAX_BYTES = 12 * 1024 * 1024

def validate_url(url):
    if not isinstance(url, str) or len(url) > 4096:
        raise ValueError("Invalid stream URL")
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only HTTP(S) URLs without embedded credentials are allowed")
    if parsed.fragment:
        raise ValueError("URL fragments are not supported")
    if parsed.hostname.lower() == "localhost" or parsed.hostname.lower().endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local hostnames are not supported")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        raise ValueError("DNS hostnames are not allowed in restricted capture mode")
    if not address.is_global:
        raise ValueError("Non-public IP addresses are not supported")
    return url

def capture(url, destination, *, seconds=4, timeout=17, runner=subprocess.run, which=shutil.which):
    validate_url(url)
    if type(seconds) is not int or not 1 <= seconds <= MAX_SECONDS:
        raise ValueError("Sample duration must be 1..12 seconds")
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT:
        raise ValueError("Timeout must be 1..17 seconds")
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
    cmd = [executable, "-nostdin", "-hide_banner", "-loglevel", "error",
           "-rw_timeout", str(timeout * 1000000), "-max_redirect", "0",
           "-i", url, "-t", str(seconds), "-fs", str(MAX_BYTES),
           "-map", "0:v:0?", "-map", "0:a:0?", "-c:v", "mpeg4", "-q:v", "12",
           "-c:a", "aac", "-b:a", "48k", "-n", str(dest)]
    try:
        result = runner(cmd, capture_output=True, timeout=timeout, check=False)
        if dest.is_symlink():
            raise ValueError("Capture output cannot be a symlink")
        size = dest.stat().st_size if dest.is_file() else 0
        if result.returncode != 0 or not 0 < size <= MAX_BYTES:
            dest.unlink(missing_ok=True)
            return {"status": "CAPTURE_FAILED", "language_verified": False, "device_verified": False}
        return {"status": "SAMPLE_CAPTURED_UNVERIFIED", "bytes": size,
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
    args = parser.parse_args()
    print(json.dumps(capture(args.url, args.output, seconds=args.seconds), sort_keys=True))

if __name__ == "__main__":
    main()

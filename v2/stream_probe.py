#!/usr/bin/env python3
"""Probe actual stream audio/video codecs; network retries may require a public-only egress guard."""
import argparse
from functools import lru_cache
import json
import os
import shutil
import subprocess
from urllib.parse import urlsplit

try:
    from .public_egress_guard import is_installed
except ImportError:
    from public_egress_guard import is_installed

PROTOCOL_WHITELIST = "http,https,tcp,tls,crypto"
MAX_REDIRECTS = "5"


@lru_cache(maxsize=1)
def _egress_guard_installed():
    return is_installed()


def _valid_http_url(url):
    if not isinstance(url, str) or not url or any(ord(ch) < 32 or ch.isspace() or ord(ch) == 92 for ch in url):
        return False
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    if parsed.username or parsed.password or parsed.fragment or "%" in parsed.netloc:
        return False
    if port == 53:
        return False
    return True


def probe(url, timeout=25, ffprobe="ffprobe", require_guard=False):
    if not _valid_http_url(url):
        return {"status": "INVALID_URL", "video": False, "audio": False}
    if require_guard and not _egress_guard_installed():
        return {"status": "EGRESS_GUARD_REQUIRED", "video": False, "audio": False}
    executable = shutil.which(ffprobe)
    if not executable:
        return {"status": "PROBE_UNAVAILABLE", "video": False, "audio": False}
    command = [
        executable, "-v", "error",
        "-protocol_whitelist", PROTOCOL_WHITELIST,
        "-max_redirects", MAX_REDIRECTS,
        "-tls_verify", "1",
        "-probesize", "1500000",
        "-analyzeduration", "3000000",
        "-rw_timeout", str(int(timeout * 1000000)),
        "-show_entries", "stream=codec_type,codec_name,width,height",
        "-of", "json", url,
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout + 5,
            check=False, env={**os.environ, "AV_LOG_FORCE_NOCOLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "video": False, "audio": False}
    except OSError:
        return {"status": "PROBE_FAILED", "video": False, "audio": False}
    if result.returncode != 0:
        return {"status": "PROBE_FAILED", "video": False, "audio": False}
    try:
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            return {"status": "INVALID_PROBE_RESULT", "video": False, "audio": False}
        streams = payload.get("streams", [])
    except (ValueError, TypeError):
        return {"status": "INVALID_PROBE_RESULT", "video": False, "audio": False}
    if not isinstance(streams, list) or any(not isinstance(item, dict) for item in streams):
        return {"status": "INVALID_PROBE_RESULT", "video": False, "audio": False}
    video = any(item.get("codec_type") == "video" and item.get("codec_name") not in (None, "unknown")
                for item in streams)
    audio = any(item.get("codec_type") == "audio" and item.get("codec_name") not in (None, "unknown")
                for item in streams)
    dimensions = [
        (item.get("width"), item.get("height")) for item in streams
        if item.get("codec_type") == "video" and item.get("codec_name") not in (None, "unknown")
    ]
    dimensions = [
        (width, height) for width, height in dimensions
        if type(width) is int and type(height) is int and 0 < width <= 16384 and 0 < height <= 16384
    ]
    width, height = max(dimensions, key=lambda pair: pair[0] * pair[1]) if dimensions else (None, None)
    return {
        "streams": streams,
        "status": "AV_STREAMS_PRESENT" if video and audio else (
            "VIDEO_ONLY" if video else ("AUDIO_ONLY" if audio else "NO_MEDIA")
        ),
        "evidence_level": "ffprobe_stream_metadata",
        "decoded_av_verified": False,
        "video": video,
        "audio": audio,
        "width": width,
        "height": height,
        "resolution_verified": bool(video and width and height),
    }


def verify_decoded_av(url, timeout=25, ffmpeg="ffmpeg", require_guard=False):
    """Require one actually decoded frame from both video and audio."""
    if not _valid_http_url(url):
        return {"decoded_av_verified": False, "decode_status": "INVALID_URL"}
    if require_guard and not _egress_guard_installed():
        return {"decoded_av_verified": False, "decode_status": "EGRESS_GUARD_REQUIRED"}
    executable = shutil.which(ffmpeg)
    if not executable:
        return {"decoded_av_verified": False, "decode_status": "DECODER_UNAVAILABLE"}
    for selector in ("v:0", "a:0"):
        command = [
            executable, "-nostdin", "-hide_banner", "-v", "error",
            "-protocol_whitelist", PROTOCOL_WHITELIST,
            "-max_redirects", MAX_REDIRECTS,
            "-tls_verify", "1",
            "-rw_timeout", str(int(timeout * 1000000)),
            "-i", url,
            "-map", "0:" + selector,
            "-frames:" + selector[0], "1",
            "-f", "framemd5", "-",
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=timeout + 5, check=False)
        except subprocess.TimeoutExpired:
            return {"decoded_av_verified": False, "decode_status": "TIMEOUT"}
        except OSError:
            return {"decoded_av_verified": False, "decode_status": "DECODE_FAILED"}
        frames = [
            line for line in result.stdout.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
            and len(line.split(",")) == 6
            and all(part.strip() for part in line.split(","))
        ]
        if result.returncode != 0 or not frames:
            return {"decoded_av_verified": False, "decode_status": "NO_DECODED_FRAME"}
    return {"decoded_av_verified": True, "decode_status": "DECODED_AV"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--timeout", type=float, default=25)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error("timeout must be 1..120 seconds")
    outcome = probe(args.url, args.timeout)
    if outcome["status"] == "AV_STREAMS_PRESENT":
        outcome.update(verify_decoded_av(args.url, args.timeout))
        if outcome["decoded_av_verified"]:
            outcome["status"] = "AV_VERIFIED"
    print(json.dumps(outcome))
    if outcome["status"] != "AV_VERIFIED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

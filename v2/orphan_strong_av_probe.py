#!/usr/bin/env python3
"""Second real-media validation with larger HLS analysis window.

Used ONLY for ambiguous playback evidence on exact historical candidate URLs.
Never retries 401/403/404, changes host, spoofs credentials or calls an
unverified result playable. All stderr and plaintext stream URLs remain private.
"""
import hashlib
import json
import subprocess
from historical_targeted_playback import public_dns
from historical_url_recovery import validate_url

RECHECK_STATUSES = frozenset({
    "VIDEO_ONLY", "AUDIO_ONLY", "NO_AV", "VIDEO_AUDIO_STREAMS_ONLY",
    "PROBE_UNCONFIRMED", "PROBE_FAILED_NETWORK_TIMEOUT",
    "PROBE_FAILED_MEDIA_FORMAT_UNSUPPORTED",
    "PROBE_FAILED_UNKNOWN_NETWORK_OR_MEDIA_ERROR",
})
PROTOCOLS = "http,https,tcp,tls,crypto"


def extended_probe(pair, initial, *, runner=subprocess.run, resolver=public_dns):
    digest, url = pair
    if (not isinstance(digest, str) or len(digest) != 64 or
            not isinstance(url, str) or
            hashlib.sha256(url.encode("utf-8")).hexdigest() != digest):
        raise ValueError("Extended probe requires exact URL SHA256 identity")
    if (not isinstance(initial, dict) or initial.get("url_sha256") != digest
            or any(type(initial.get(key)) is not bool
                   for key in ("video", "audio", "decoded"))):
        raise ValueError("Invalid first-stage FFmpeg proof")
    # Never re-request server-declared forbidden/missing/authenticated streams.
    if initial.get("decoded") or initial.get("status") not in RECHECK_STATUSES:
        return initial
    if not validate_url(url) or not resolver(url):
        return initial
    args = ["-hide_banner", "-loglevel", "error", "-rw_timeout", "8000000",
            "-protocol_whitelist", PROTOCOLS, "-analyzeduration", "8000000",
            "-probesize", "2000000"]
    inspect = (["ffprobe"] + args + ["-show_entries", "stream=codec_type",
               "-of", "json", url])
    try:
        p = runner(inspect, capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, timeout=28)
        if p.returncode:
            return initial
        tracks = json.loads(p.stdout).get("streams", [])
        if not isinstance(tracks, list):
            return initial
        video = any(isinstance(x, dict) and x.get("codec_type") == "video"
                    for x in tracks)
        audio = any(isinstance(x, dict) and x.get("codec_type") == "audio"
                    for x in tracks)
        if not video or not audio:
            return initial
        decode = (["ffmpeg", "-nostdin"] + args + ["-i", url, "-map", "0:v:0",
                  "-map", "0:a:0", "-t", "1", "-f", "null", "-"])
        d = runner(decode, capture_output=True, text=True,
                   stdin=subprocess.DEVNULL, timeout=32)
        if d.returncode:
            return initial
        return {"url_sha256": digest, "status": "VIDEO_AUDIO_DECODED",
                "video": True, "audio": True, "decoded": True,
                "audio_lang_tags": []}
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired):
        return initial

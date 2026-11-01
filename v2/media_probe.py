#!/usr/bin/env python3
"""Real media probe: only ffprobe-confirmed audio/video is playable evidence."""
import json
import subprocess
import urllib.parse

def probe(url, timeout=18):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {"status": "INVALID_URL", "streams": []}
    cmd = ["ffprobe", "-v", "error", "-show_entries",
           "stream=codec_type,codec_name", "-of", "json",
           "-analyzeduration", "5000000", "-probesize", "5000000", url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {"status": "PROBE_TIMEOUT", "streams": []}
    except OSError:
        return {"status": "FFPROBE_UNAVAILABLE", "streams": []}
    if result.returncode:
        return {"status": "PROBE_FAILED", "streams": []}
    try:
        streams = json.loads(result.stdout).get("streams", [])
    except (ValueError, TypeError):
        return {"status": "INVALID_PROBE_RESULT", "streams": []}
    codecs = [{"type": s.get("codec_type"), "codec": s.get("codec_name")}
              for s in streams if s.get("codec_type") in ("audio", "video")
              and s.get("codec_name") not in (None, "", "unknown")]
    return {"status": "MEDIA_CONFIRMED" if codecs else "NO_MEDIA_STREAM",
            "streams": codecs}

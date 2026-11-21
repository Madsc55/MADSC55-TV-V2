#!/usr/bin/env python3
"""Bounded real FFmpeg audio/video decode of Turkish candidates; advisory only."""
import concurrent.futures
import datetime
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
try:
    from .turkish_stream_probe import probe
except ImportError:  # direct script execution from the v2 directory
    from turkish_stream_probe import probe

SOURCE = ROOT / "v2/reports/turkish-stream-candidates.json"
OUT = ROOT / "v2/reports/turkish-stream-decode.json"
MAX_DECODES = 24
VIDEO_FRAME = re.compile(r"Parsed_showinfo.*\bn:\s*\d+")
AUDIO_FRAME = re.compile(r"Parsed_ashowinfo.*\bn:\s*\d+")


def decode(item):
    """Require FFmpeg to report at least one decoded video frame and audio frame."""
    url = item["url"]
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-v", "info",
           "-rw_timeout", "6000000", "-analyzeduration", "2000000",
           "-probesize", "65536", "-i", url,
           "-map", "0:v:0", "-map", "0:a:0",
           "-vf", "showinfo", "-af", "ashowinfo",
           "-t", "3", "-f", "null", "-"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=18)
        stderr = result.stderr or ""
        video_decoded = bool(VIDEO_FRAME.search(stderr))
        audio_decoded = bool(AUDIO_FRAME.search(stderr))
        verified = result.returncode == 0 and video_decoded and audio_decoded
        return {"channel_id": item["channel_id"],
                "status": "SHORT_DECODE_VERIFIED" if verified else "DECODE_UNVERIFIED",
                "media_types": ["audio", "video"] if verified else []}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"channel_id": item["channel_id"], "status": "DECODE_UNVERIFIED",
                "media_types": []}


def main():
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required")
    candidates = json.loads(SOURCE.read_text(encoding="utf-8"))["candidates"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        hints = list(pool.map(probe, candidates))
    selected = [item for item, hint in zip(candidates, hints)
                if hint["status"] == "HTTP_RESPONSIVE_MEDIA_HINT"][:MAX_DECODES]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        decoded = list(pool.map(decode, selected))
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY_SHORT_DECODER_CHECK_NOT_LONG_TERM_PLAYBACK",
              "http_media_hints": sum(x["status"] == "HTTP_RESPONSIVE_MEDIA_HINT" for x in hints),
              "selected_for_decode": len(selected),
              "short_decode_verified": sum(x["status"] == "SHORT_DECODE_VERIFIED" for x in decoded),
              "results": decoded}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Short decode verified:", report["short_decode_verified"], "of", len(selected),
          "HTTP media hints:", report["http_media_hints"])


if __name__ == "__main__":
    main()

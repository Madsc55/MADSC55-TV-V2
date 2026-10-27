#!/usr/bin/env python3
"""Bounded ffprobe check of responsive Turkish stream candidates, advisory only."""
import concurrent.futures
import datetime
import json
import shutil
import subprocess
from discover import ROOT
from turkish_stream_probe import probe

SOURCE = ROOT / "v2/reports/turkish-stream-candidates.json"
OUT = ROOT / "v2/reports/turkish-stream-decode.json"
MAX_DECODES = 24

def decode(item):
    url = item["url"]
    cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,avg_frame_rate,bit_rate",
           "-of", "json", "-rw_timeout", "6000000", "-analyzeduration", "2000000",
           "-probesize", "65536", url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=13)
        if result.returncode != 0:
            return {"channel_id": item["channel_id"], "url": url, "status": "DECODE_UNVERIFIED"}
        streams = json.loads(result.stdout).get("streams", [])
        types = sorted({x.get("codec_type") for x in streams if x.get("codec_type") in ("audio", "video")})
        return {"channel_id": item["channel_id"], "url": url,
                "video_streams": [{"width": s.get("width"), "height": s.get("height"), "codec": s.get("codec_name"), "bit_rate": s.get("bit_rate")} for s in streams if s.get("codec_type") == "video"],
                "status": "SHORT_DECODE_VERIFIED" if types else "DECODE_UNVERIFIED",
                "media_types": types}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"channel_id": item["channel_id"], "status": "DECODE_UNVERIFIED"}

def main():
    if not shutil.which("ffprobe"):
        raise SystemExit("ffprobe is required")
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

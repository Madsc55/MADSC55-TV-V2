#!/usr/bin/env python3
"""Bounded read-only baseline video resolution checks for existing playlist channels."""
import concurrent.futures
import datetime
import hashlib
import json
import subprocess
from discover import ROOT, LIVE, entries

OUT = ROOT / "v2/reports/current-stream-resolution.json"
LIMIT = 120

def measure(item):
    url = item["url"]
    result = {"tvg_id": item["tvg_id"], "name": item["name"],
              "url_sha256": hashlib.sha256(url.encode()).hexdigest(), "status": "UNVERIFIED"}
    try:
        command = ["ffprobe", "-v", "error", "-rw_timeout", "5000000",
                   "-analyzeduration", "2000000", "-probesize", "65536",
                   "-show_entries", "stream=codec_type,width,height", "-of", "json", url]
        process = subprocess.run(command, capture_output=True, text=True, timeout=12)
        if process.returncode == 0:
            streams = json.loads(process.stdout).get("streams", [])
            heights = [int(s["height"]) for s in streams if s.get("codec_type") == "video" and s.get("height")]
            if heights:
                result.update(status="MEASURED", height=max(heights))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return result

def main():
    channels = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    distinct = {}
    for channel in channels:
        if channel["tvg_id"] and channel["url"].startswith(("http://", "https://")):
            distinct.setdefault(channel["tvg_id"].split("@")[0].casefold(), channel)
    candidate_path = ROOT / "v2/reports/turkish-stream-candidates.json"
    candidate_ids = set()
    if candidate_path.exists():
        data = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate_ids = {x["channel_id"].split("@")[0].casefold() for x in data.get("candidates", [])}
    selected = [item for key, item in distinct.items() if key in candidate_ids][:LIMIT]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(measure, selected))
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY_BOUNDED_SAMPLE_NO_AUTOMATIC_REPLACEMENT",
              "playlist_entries": len(channels), "selected": len(selected),
              "measured": sum(x["status"] == "MEASURED" for x in results), "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Current stream resolutions:", report["measured"], "of", len(selected))

if __name__ == "__main__":
    main()

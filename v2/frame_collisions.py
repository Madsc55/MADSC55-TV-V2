#!/usr/bin/env python3
"""Read-only bounded comparison of decoded video samples for candidate URLs."""
import concurrent.futures
import datetime
import hashlib
import json
import shutil
import subprocess
from discover import ROOT

def fingerprint(item):
    url = item["url"]
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
               "-rw_timeout", "5000000", "-i", url,
               "-map", "0:v:0", "-vf", "fps=1/2,scale=32:18,format=gray", "-frames:v", "3",
               "-f", "rawvideo", "-"]
    try:
        result = subprocess.run(command, capture_output=True, timeout=12)
        if result.returncode == 0 and len(result.stdout) == 1728:
            return {"channel_id": item["channel_id"], "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                    "frame_sha256": hashlib.sha256(result.stdout).hexdigest(), "status": "THREE_FRAMES_SAMPLED"}
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"channel_id": item["channel_id"], "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
            "status": "SAMPLE_UNVERIFIED"}

def main():
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg required")
    decoded = json.loads((ROOT / "v2/reports/turkish-stream-decode.json").read_text(encoding="utf-8"))
    candidates = [x for x in decoded["results"] if x["status"] == "SHORT_DECODE_VERIFIED" and x.get("url")][:16]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fingerprint, candidates))
    groups = {}
    for item in results:
        if item.get("frame_sha256"):
            groups.setdefault(item["frame_sha256"], []).append(item["url_sha256"])
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY_THREE_FRAME_HASH; matching samples are only possible duplicate evidence, not identity proof",
              "sampled": len(results),
              "possible_duplicate_groups": [urls for urls in groups.values() if len(urls) > 1],
              "results": results}
    path = ROOT / "v2/reports/frame-collisions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Three-frame possible duplicate groups:", len(report["possible_duplicate_groups"]))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Extract source-specific streams with bounded decoder checks. Read-only; never publish raw URLs in JSON."""
import concurrent.futures
import datetime
import hashlib
import json
import subprocess
from pathlib import Path
from discover import ROOT, LIVE, fetch, entries
from turkish_stream_probe import probe

URL = "https://gist.githubusercontent.com/akan1970/040f6a07995df715c74ef1268b57c92d/raw/4f491cf9bd165340f4008c64dea263d119542eeb/NewlistTR.m3u"
OUT = ROOT / "v2/reports"
MAX = 600

def test(item):
    status = probe({"url": item["url"], "channel_id": item["tvg_id"] or item["name"]})
    decoded = False
    width = height = None
    if status["status"] == "HTTP_RESPONSIVE_MEDIA_HINT":
        try:
            p = subprocess.run(
                ["ffprobe", "-v", "error", "-analyzeduration", "1500000",
                 "-probesize", "300000", "-show_entries", "stream=codec_type,width,height",
                 "-of", "json", item["url"]],
                capture_output=True, text=True, timeout=14, check=False)
            if p.returncode == 0:
                streams = json.loads(p.stdout).get("streams", [])
                video = next((s for s in streams if s.get("codec_type") == "video"), None)
                if video:
                    decoded = True
                    width, height = video.get("width"), video.get("height")
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
    return status["status"], decoded, width, height

def main():
    source = list(entries(fetch(URL)))
    unique, seen = [], set()
    for item in source:
        if item["url"] not in seen:
            unique.append(item)
            seen.add(item["url"])
    existing = {x["url"] for x in entries(LIVE.read_text(encoding="utf-8-sig"))}
    checked = unique[:MAX]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(test, checked))
    confirmed = [(item, result) for item, result in zip(checked, results) if result[1]]
    lines = ["#EXTM3U"]
    for item, (_, _, width, height) in confirmed:
        def clean(v):
            return str(v or "").replace('"', "'").replace("\n", " ").replace("\r", " ")
        lines.extend([f'#EXTINF:-1 tvg-id="{clean(item["tvg_id"])}" tvg-logo="{clean(item["logo"])}" group-title="NewlistTR DOĞRULANAN",{clean(item["name"])}', item["url"]])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "newlisttr-decoded-only.m3u8").write_text("\n".join(lines) + "\n", encoding="utf-8")
    records = []
    for item, (http, decoded, width, height) in zip(checked, results):
        records.append({"name": item["name"], "tvg_id": item["tvg_id"],
                        "url_sha256": hashlib.sha256(item["url"].encode()).hexdigest(),
                        "already_in_playlist": item["url"] in existing,
                        "http_status": http, "video_decoded": decoded,
                        "width": width, "height": height})
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "source": "akan1970-NewlistTR", "source_entries": len(source),
              "distinct_urls": len(unique), "tested": len(checked),
              "remaining_untested": len(unique) - len(checked),
              "short_video_decoded": len(confirmed),
              "policy": "READ_ONLY_SHORT_DECODER_CHECK_NOT_IDENTITY_OR_LONG_TERM_STABILITY",
              "channels": records}
    (OUT / "newlisttr-check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("NewlistTR:", len(source), "entries,", len(checked), "checked,", len(confirmed), "short video decoded")

if __name__ == "__main__":
    main()

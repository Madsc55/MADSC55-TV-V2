#!/usr/bin/env python3
"""Generate a separate provisional M3U from short-decoded candidates; never edit live IBO."""
import json
from pathlib import Path
from discover import ROOT, LIVE, entries

REPORT = ROOT / "v2/reports/turkish-stream-review-queue.json"
OUT = ROOT / "v2/reports/short-decoded-review-only.m3u8"
SUMMARY = ROOT / "v2/reports/short-decoded-playlist-summary.json"

def clean(value):
    return str(value or "").replace("\r", " ").replace("\n", " ").replace('"', "'").strip()

def main():
    queue = json.loads(REPORT.read_text(encoding="utf-8"))["items"]
    existing = {e["url"] for e in entries(LIVE.read_text(encoding="utf-8-sig"))}
    seen, lines, count = set(), ["#EXTM3U"], 0
    for item in queue:
        url = item.get("url", "")
        if not url.startswith(("https://", "http://")) or url in existing or url in seen:
            continue
        if "video" not in item.get("media_types", []):
            continue
        seen.add(url)
        name = clean(item.get("channel_id", "ADAY"))
        height = item.get("measured_max_height") or 0
        lines.append('#EXTINF:-1 group-title="TEST - MANUEL ONAY",'+name+" ["+str(height)+"P]")
        lines.append(url)
        count += 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    SUMMARY.write_text(json.dumps({"policy":"PROVISIONAL_SHORT_DECODED_NOT_IDENTITY_OR_STABILITY_VERIFIED",
        "entries":count,"live_playlist_modified":False},ensure_ascii=False,indent=2)+"\n")
    print("Provisional review-only entries:",count)

if __name__ == "__main__":
    main()

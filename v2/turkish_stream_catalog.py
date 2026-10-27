#!/usr/bin/env python3
"""Read-only Turkish stream candidate cross-reference from public IPTV-org API."""
import datetime
import json
import urllib.request
from discover import ROOT, LIVE, entries

API = "https://iptv-org.github.io/api/streams.json"
OUT = ROOT / "v2/reports/turkish-stream-candidates.json"
MAX_BYTES = 40_000_000

def main():
    request = urllib.request.Request(API, headers={"User-Agent": "MADSC55-TV-V2-Discovery/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise SystemExit("Stream catalog too large")
    catalog = json.loads(data)
    current = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    known_urls = {item["url"] for item in current}
    known_ids = {item["tvg_id"].split("@")[0].casefold() for item in current if item["tvg_id"]}
    candidates, seen = [], set()
    for stream in catalog:
        channel = str(stream.get("channel") or "")
        url = str(stream.get("url") or "")
        if not channel or not (channel.casefold().endswith(".tr") or ".tr@" in channel.casefold()):
            continue
        if not url.startswith(("http://", "https://")) or url in known_urls or url in seen:
            continue
        if stream.get("is_nsfw"):
            continue
        seen.add(url)
        candidates.append({"channel_id": channel, "url": url,
                           "already_present_by_id": channel.split("@")[0].casefold() in known_ids,
                           "status": "CANDIDATE_NOT_PLAYBACK_VERIFIED"})
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "source": API, "policy": "REVIEW_ONLY_NO_PLAYLIST_WRITES",
              "v2_entries": len(current), "candidates": candidates,
              "candidate_count": len(candidates)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Turkish stream candidates:", len(candidates), "current playlist entries:", len(current))
if __name__ == "__main__":
    main()

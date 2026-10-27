#!/usr/bin/env python3
"""Read-only bounded XMLTV integrity inspection of EPG feeds."""
import concurrent.futures
import datetime
import gzip
import io
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from discover import ROOT, LIVE, entries

OUT = ROOT / "v2" / "reports" / "epg-integrity.json"
MAX_BYTES = 20_000_000

def inspect(url, playlist_ids):
    result = {"url_sha256": hashlib.sha256(url.encode()).hexdigest(), "status": "UNVERIFIED"}
    if not url.startswith("https://"):
        result["status"] = "NON_HTTPS"
        return result
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-V2-EPG-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=16) as res:
            data = res.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            result["status"] = "TOO_LARGE_FOR_AUDIT"
            return result
        if data.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                data = gz.read(120_000_001)
        if len(data) > 120_000_000:
            result["status"] = "DECOMPRESSED_TOO_LARGE"
            return result
        root = ET.fromstring(data)
        if root.tag != "tv":
            result["status"] = "NOT_XMLTV"
            return result
        channels = {node.get("id") for node in root.iter("channel") if node.get("id")}
        now = datetime.datetime.now(datetime.timezone.utc)
        programmes = 0
        current_programmes = 0
        matched_programme_ids = set()
        for node in root.iter("programme"):
            programmes += 1
            channel_id = node.get("channel")
            if channel_id in playlist_ids:
                matched_programme_ids.add(channel_id)
            start, stop = node.get("start", ""), node.get("stop", "")
            try:
                start_at = datetime.datetime.strptime(start[:14], "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc)
                stop_at = datetime.datetime.strptime(stop[:14], "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc)
                if start_at <= now <= stop_at:
                    current_programmes += 1
            except ValueError:
                pass
        result.update(status="XMLTV_VALID", channels=len(channels), programmes=programmes,
                      playlist_id_matches=len(channels & playlist_ids),
                      matched_programme_channel_ids=len(matched_programme_ids),
                      current_programme_intervals_approx_utc=current_programmes,
                      playlist_id_match_rate=round(len(channels & playlist_ids) / len(playlist_ids), 4) if playlist_ids else None)
    except (OSError, ValueError, ET.ParseError, EOFError, gzip.BadGzipFile, MemoryError) as exc:
        result.update(status="EPG_UNVERIFIED", error_type=type(exc).__name__)
    return result

def main():
    sources = json.loads((ROOT / "v2" / "epg_sources.json").read_text(encoding="utf-8"))["sources"]
    playlist_ids = {e["tvg_id"] for e in entries(LIVE.read_text(encoding="utf-8-sig")) if e["tvg_id"]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        checks = list(pool.map(lambda url: inspect(url, playlist_ids), sources))
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; programme times are approximate UTC when XMLTV timezone offsets exist; matching IDs do not prove accurate schedules",
              "status_counts": dict(Counter(x["status"] for x in checks)),
              "playlist_distinct_tvg_ids": len(playlist_ids), "sources": checks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("EPG XMLTV validation:", report["status_counts"])

if __name__ == "__main__":
    main()

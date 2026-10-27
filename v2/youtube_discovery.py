#!/usr/bin/env python3
"""Find candidate live Turkish TV broadcasts on YouTube without changing the playlist.

Discovery is advisory: YouTube page URLs are not direct IBO-compatible stream URLs.
"""
import datetime
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "v2/reports/youtube-live-candidates.json"
QUERIES = [
    "Türkiye televizyon canlı yayın resmi",
    "Türk haber kanalı canlı yayın resmi",
    "yerel televizyon canlı yayın Türkiye",
    "TRT canlı yayın resmi",
    "Türk spor televizyonu canlı yayın",
]
def search(query):
    command = ["yt-dlp", "--flat-playlist", "--dump-single-json", "--no-warnings",
               "--socket-timeout", "10", f"ytsearch8:{query}"]
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=65)
        if p.returncode != 0:
            return [], "SEARCH_FAILED"
        data = json.loads(p.stdout)
        found = []
        for item in data.get("entries") or []:
            if not isinstance(item, dict):
                continue
            video_id = item.get("id") or ""
            if not isinstance(video_id, str) or len(video_id) != 11 or not all(c.isascii() and (c.isalnum() or c in "_-") for c in video_id):
                continue
            found.append({"video_id": video_id, "title": str(item.get("title") or "")[:200],
                          "channel": str(item.get("channel") or item.get("uploader") or "")[:120],
                          "url": f"https://www.youtube.com/watch?v={video_id}",
                          "status": "DISCOVERED_NOT_LIVE_VERIFIED"})
        return found, None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return [], "SEARCH_TIMEOUT_OR_ERROR"

def verify(item):
    try:
        p = subprocess.run(["yt-dlp", "--skip-download", "--dump-single-json", "--no-warnings",
                            "--socket-timeout", "8", item["url"]],
                           capture_output=True, text=True, timeout=24)
        if p.returncode != 0:
            return "UNVERIFIED"
        meta = json.loads(p.stdout)
        return "LIVE_METADATA_VERIFIED" if meta.get("is_live") is True or meta.get("live_status") == "is_live" else "NOT_CURRENTLY_LIVE"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return "UNVERIFIED"

def main():
    if not shutil.which("yt-dlp"):
        raise SystemExit("yt-dlp required")
    results, errors, seen = [], [], set()
    for query in QUERIES:
        items, error = search(query)
        if error:
            errors.append({"query": query, "reason": error})
        for item in items:
            if item["video_id"] in seen:
                continue
            seen.add(item["video_id"])
            results.append(item)
    # Keep network work bounded. Never promote YouTube URLs as direct IBO streams.
    for item in results[:12]:
        item["status"] = verify(item)
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "ADVISORY_ONLY_NO_PLAYLIST_WRITES_NO_AUTOMATIC_IBO_IMPORT",
              "queries": QUERIES, "errors": errors, "results": results,
              "live_verified": sum(x["status"] == "LIVE_METADATA_VERIFIED" for x in results)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("YouTube discovered:", len(results), "live metadata verified:", report["live_verified"], "query errors:", len(errors))
if __name__ == "__main__":
    main()

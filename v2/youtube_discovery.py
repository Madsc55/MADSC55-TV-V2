#!/usr/bin/env python3
"""Find candidate live Turkish TV broadcasts on YouTube without changing the playlist.

Discovery is advisory: YouTube page URLs are not direct IBO-compatible stream URLs.
"""
import datetime
import json
import pathlib
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "v2/reports/youtube-live-candidates.json"
QUERIES = [
    "Türkiye televizyon canlı yayın resmi",
    "Türk haber kanalı canlı yayın resmi",
    "yerel televizyon canlı yayın Türkiye",
    "TRT canlı yayın resmi",
    "Türk spor televizyonu canlı yayın",
    "Türk müzik televizyonu canlı yayın resmi",
    "Türk belgesel televizyonu canlı yayın resmi",
    "Türk dini televizyon kanalı canlı yayın resmi",
    "Türk çocuk televizyonu canlı yayın resmi",
    "Türkiye bölgesel yerel TV canlı yayın",
    "Türkçe Avrupa televizyonu canlı yayın resmi",
    "Azerbaycan televiziya canlı yayım rəsmi",
    "Azərbaycan xəbər kanalı canlı yayım",
    "Azerice yerel televizyon canlı yayın",
    "Türkçe Almanya televizyon canlı yayın resmi",
    "Türkçe Hollanda Belçika televizyon canlı yayın",
    "Türkçe Fransa Avusturya İsviçre televizyon canlı yayın",
    "Türkçe İngiltere Amerika televizyon canlı yayın",
    "Türkçe Balkanlar televizyon canlı yayın",
    "Türkçe Kıbrıs televizyon canlı yayın",
    "Türkiye il il yerel televizyon canlı yayın",
]
def search(query):
    command = ["yt-dlp", "--flat-playlist", "--dump-single-json", "--no-warnings",
               "--socket-timeout", "10", f"ytsearch15:{query}"]
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

def metadata_summary(results):
    statuses = [item["status"] for item in results]
    checked = sum(value != "DISCOVERED_NOT_LIVE_VERIFIED" for value in statuses)
    unknown = sum(value == "UNVERIFIED" for value in statuses)
    return {"metadata_verification_attempted": checked,
            "metadata_unverified_count": unknown,
            "metadata_not_live_count": sum(value == "NOT_CURRENTLY_LIVE" for value in statuses),
            "metadata_unattempted_count": len(results) - checked,
            "metadata_coverage_complete": checked == len(results) and unknown == 0}


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
    # Check every discovered video in a bounded parallel batch. Search pages
    # are not direct IPTV streams, even when live metadata succeeds.
    with ThreadPoolExecutor(max_workers=8) as executor:
        for item, status in zip(results, executor.map(verify, results)):
            item["status"] = status
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "ADVISORY_ONLY_NO_PLAYLIST_WRITES_NO_AUTOMATIC_IBO_IMPORT",
              "queries": QUERIES, "errors": errors, "results": results,
              "live_verified": sum(x["status"] == "LIVE_METADATA_VERIFIED" for x in results),
              "verified_live_pages": [x for x in results if x["status"] == "LIVE_METADATA_VERIFIED"],
              **metadata_summary(results)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("YouTube discovered:", len(results), "live metadata verified:", report["live_verified"],
          "metadata unverified:", report["metadata_unverified_count"],
          "unattempted:", report["metadata_unattempted_count"], "query errors:", len(errors))
if __name__ == "__main__":
    main()

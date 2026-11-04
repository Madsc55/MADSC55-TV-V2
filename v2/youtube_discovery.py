#!/usr/bin/env python3
"""Find candidate live Turkish TV broadcasts on YouTube without changing the playlist.

Discovery is advisory: YouTube page URLs are not direct IBO-compatible stream URLs.
"""
import datetime
import json
import pathlib
import shutil
import subprocess
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from youtube_official_live_api import verify_ids, search_live

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
            return [], "SEARCH_" + failure_reason(p.stderr)
        data = json.loads(p.stdout)
        found = []
        for item in data.get("entries") or []:
            if not isinstance(item, dict):
                continue
            video_id = item.get("id") or ""
            if not isinstance(video_id, str) or len(video_id) != 11 or not all(c.isascii() and (c.isalnum() or c in "_-") for c in video_id):
                continue
            # An explicit yt-dlp result field is usable metadata evidence.
            # A title containing "LIVE" is not. Confirm with official API
            # when configured; otherwise keep any uncertain video unverified.
            status, reason = search_live_metadata(item)
            found.append({"video_id": video_id, "title": str(item.get("title") or "")[:200],
                          "channel": str(item.get("channel") or item.get("uploader") or "")[:120],
                          "url": f"https://www.youtube.com/watch?v={video_id}",
                          "status": status, "metadata_reason": reason})
        return found, None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return [], "SEARCH_TIMEOUT_OR_ERROR"

def search_live_metadata(item):
    """Only explicit, consistent live fields determine a broadcast's state."""
    if not isinstance(item, dict):
        return "DISCOVERED_NOT_LIVE_VERIFIED", "SEARCH_NO_EXPLICIT_LIVE_STATUS"
    state, flag = item.get("live_status"), item.get("is_live")
    if state == "is_live":
        if flag is False:
            return "DISCOVERED_NOT_LIVE_VERIFIED", "SEARCH_CONFLICTING_LIVE_FIELDS"
        return "LIVE_METADATA_VERIFIED", "SEARCH_FLAT_LIVE_METADATA"
    if state in ("not_live", "was_live", "post_live", "is_upcoming"):
        if flag is True:
            return "DISCOVERED_NOT_LIVE_VERIFIED", "SEARCH_CONFLICTING_LIVE_FIELDS"
        return "NOT_CURRENTLY_LIVE", "SEARCH_FLAT_NOT_LIVE"
    if flag is True:
        return "LIVE_METADATA_VERIFIED", "SEARCH_FLAT_LIVE_METADATA"
    if flag is False:
        return "NOT_CURRENTLY_LIVE", "SEARCH_FLAT_NOT_LIVE"
    return "DISCOVERED_NOT_LIVE_VERIFIED", "SEARCH_NO_EXPLICIT_LIVE_STATUS"


def failure_reason(stderr):
    """Classify unverified metadata without publishing URLs or raw server text."""
    msg = (stderr or "").lower()
    if "not a bot" in msg or "automated requests" in msg: return "BOT_CHALLENGE"
    if "sign in" in msg or "login" in msg: return "AUTH_REQUIRED"
    if "429" in msg or "too many requests" in msg: return "RATE_LIMITED"
    if "403" in msg or "forbidden" in msg: return "HTTP_FORBIDDEN"
    if "unavailable in your country" in msg: return "GEO_RESTRICTED"
    if "video unavailable" in msg or "not available" in msg: return "VIDEO_UNAVAILABLE"
    if "timed out" in msg or "timeout" in msg: return "TIMEOUT"
    return "EXTRACTOR_FAILED"


def verify_with_reason(item):
    try:
        p = subprocess.run(["yt-dlp", "--skip-download", "--dump-single-json", "--no-warnings",
                            "--socket-timeout", "8", item["url"]],
                           capture_output=True, text=True, timeout=24)
        if p.returncode != 0:
            return "UNVERIFIED", failure_reason(p.stderr)
        meta = json.loads(p.stdout)
        if meta.get("is_live") is True or meta.get("live_status") == "is_live":
            return "LIVE_METADATA_VERIFIED", "LIVE_METADATA_CONFIRMED"
        state = meta.get("live_status")
        if state in ("not_live", "was_live", "post_live", "is_upcoming"):
            return "NOT_CURRENTLY_LIVE", "LIVE_METADATA_EXPLICITLY_NOT_LIVE"
        if meta.get("is_live") is False:
            return "NOT_CURRENTLY_LIVE", "LIVE_METADATA_EXPLICITLY_NOT_LIVE"
        return "UNVERIFIED", "LIVE_METADATA_STATUS_MISSING"
    except subprocess.TimeoutExpired:
        return "UNVERIFIED", "TIMEOUT"
    except (OSError, ValueError):
        return "UNVERIFIED", "PARSE_OR_PROCESS_ERROR"


def verify(item):
    # Retain the previous caller's string status contract.
    return verify_with_reason(item)[0]

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
    # Optional official live search is independent from yt-dlp scraping.
    # videos.list confirms start and no end before a search result is accepted.
    # Without an API key, this is explicitly partial rather than simulated.
    live_search_rows, live_search_status = search_live(QUERIES[:4])
    new_official_live = 0
    for item in live_search_rows:
        if item["video_id"] in seen:
            existing = next(row for row in results if row["video_id"] == item["video_id"])
            existing["status"] = "LIVE_METADATA_VERIFIED"
            existing["metadata_reason"] = "OFFICIAL_API_ACTIVE_LIVE"
            continue
        seen.add(item["video_id"])
        results.append(item)
        new_official_live += 1
    # Official videos.list checks at most 50 IDs per request; even search
    # results are never direct IPTV stream URLs.
    official, api_status = verify_ids([item["video_id"] for item in results])
    for item in results:
        result = official.get(item["video_id"])
        if result is not None:
            item["status"], item["metadata_reason"] = result
    # For remaining unknowns, attempt ordinary public yt-dlp metadata.
    # Avoid re-querying videos already confirmed live/offline by providers.
    unknown = [item for item in results
               if item["status"] == "DISCOVERED_NOT_LIVE_VERIFIED"]
    with ThreadPoolExecutor(max_workers=3) as executor:
        for item, detail in zip(unknown, executor.map(verify_with_reason, unknown)):
            item["status"], item["metadata_reason"] = detail
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "ADVISORY_ONLY_NO_PLAYLIST_WRITES_NO_AUTOMATIC_IBO_IMPORT",
              "queries": QUERIES, "errors": errors, "results": results,
              "official_youtube_api_status": api_status,
              "official_youtube_api_classified": len(official),
              "official_live_search_status": live_search_status,
              "official_live_search_new_candidates": new_official_live,
              "verification_status": ("ALL_RESULTS_CLASSIFIED" if
                    all(item["status"] in ("LIVE_METADATA_VERIFIED", "NOT_CURRENTLY_LIVE")
                        for item in results) and not errors
                    else "PARTIAL_EXTERNAL_METADATA_ACCESS"),
              "live_verified": sum(x["status"] == "LIVE_METADATA_VERIFIED" for x in results),
              "verified_live_pages": [x for x in results if x["status"] == "LIVE_METADATA_VERIFIED"],
              "anonymous_metadata_reason_counts": dict(sorted(Counter(
                  item.get("metadata_reason", "NOT_CHECKED") for item in results).items())),
              **metadata_summary(results)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("YouTube discovered:", len(results), "live metadata verified:", report["live_verified"],
          "metadata unverified:", report["metadata_unverified_count"],
          "unattempted:", report["metadata_unattempted_count"], "query errors:", len(errors),
          "reason_counts:", json.dumps(report["anonymous_metadata_reason_counts"], sort_keys=True),
          "official_api_status:", api_status, "api_classified:", len(official),
          "live_search_status:", live_search_status, "new_live_search_candidates:", new_official_live)
if __name__ == "__main__":
    main()

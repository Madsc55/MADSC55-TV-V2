#!/usr/bin/env python3
"""Read-only Turkish TV discovery and playlist health audit."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import re
import urllib.request
import urllib.error
from collections import Counter
from discover import ROOT, LIVE, SOURCES, fetch, entries

OUT = ROOT / "v2" / "reports" / "turkish-tv-health.json"
RADIO = re.compile(r"\b(radio|radyo|fm|audio only)\b", re.I)
LOCKED = re.compile(r"\b(drm|widevine|playready|encrypted|şifreli|sifreli)\b", re.I)
TURKISH = re.compile(r"\b(turk|türk|turkiye|türkiye|trt|atv|show tv|kanal d|star tv|now tv|haber|ulusal)\b", re.I)

def identity(e):
    return (e["tvg_id"] or e["name"]).strip().casefold()

def digest(url):
    return hashlib.sha256(url.encode()).hexdigest()

def check(e):
    url = e["url"]
    result = {"name": e["name"].upper(), "id": identity(e), "url_sha256": digest(url),
              "status": "UNVERIFIED", "resolution": "UNKNOWN"}
    if not url.startswith(("http://", "https://")):
        return result
    if "youtube.com" in url or "youtu.be" in url:
        result["status"] = "YOUTUBE_REQUIRES_PLAYBACK_CHECK"
        return result
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MADSC55-TV-V2", "Range": "bytes=0-32767"})
        with urllib.request.urlopen(req, timeout=9) as res:
            sample = res.read(32768)
            mime = res.headers.get("Content-Type", "").lower()
            status = res.status
        txt = sample.decode("utf-8", errors="replace")
        manifest = "#EXTM3U" in txt and ("#EXT-X-" in txt or "#EXTINF:" in txt)
        transport = sample.startswith(bytes.fromhex("4740")) or ("video/" in mime)
        if status in (200, 206) and (manifest or transport):
            result["status"] = "STREAM_RESPONDS_PLAYBACK_UNCONFIRMED"
            if "#EXT-X-STREAM-INF" in txt:
                resolutions = re.findall(r"RESOLUTION=(\d+x\d+)", txt)
                if resolutions:
                    result["resolution"] = ",".join(sorted(set(resolutions)))
        else:
            result["status"] = "UNVERIFIED"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        result["status"] = "UNREACHABLE_OR_TIMEOUT"
    return result

def main():
    live = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    categories = Counter(e["group"] or "KATEGORİSİZ" for e in live)
    unique = {identity(e) for e in live}
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    discovered = {}
    errors = []
    for source in sources:
        try:
            for e in entries(fetch(source["url"])):
                if RADIO.search(e["name"] + " " + e["group"]) or LOCKED.search(e["name"] + " " + e["group"]):
                    continue
                is_tr = source.get("scope") == "TR" or e["tvg_id"].lower().endswith(".tr") or bool(TURKISH.search(e["name"] + " " + e["group"]))
                if not is_tr or identity(e) in unique:
                    continue
                discovered.setdefault((identity(e), digest(e["url"])), e)
        except Exception as exc:
            errors.append({"source": source["id"], "error": type(exc).__name__})
    # Limit remote probes per run; live channels take precedence.
    candidate_items = list(discovered.values())[:300]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        live_checks = list(pool.map(check, live))
        candidate_checks = list(pool.map(check, candidate_items))
    # Only responsive candidates are presented; never claim confirmed playback.
    candidates = []
    for e, c in zip(candidate_items, candidate_checks):
        if c["status"] == "STREAM_RESPONDS_PLAYBACK_UNCONFIRMED":
            candidates.append({**c, "logo_source": e["logo"], "epg_id": e["tvg_id"], "category_suggestion": (e["group"] or "YENİ GELEN").upper()})
    report = {"schema": 1, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; no playlist writes; network response is not playback confirmation",
              "playlist_entries": len(live), "unique_channel_identities": len(unique),
              "category_counts": dict(sorted(categories.items())), "live_status_counts": dict(Counter(x["status"] for x in live_checks)),
              "live_checks": live_checks, "candidate_status": "NETWORK_RESPONSIVE_ONLY_NOT_APPROVED",
              "candidate_checked": len(candidate_items), "candidates": candidates, "source_errors": errors}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print("Live entries:", len(live), "Unique IDs:", len(unique), "Candidate probes:", len(candidate_items), "Responsive candidates:", len(candidates))

if __name__ == "__main__":
    main()

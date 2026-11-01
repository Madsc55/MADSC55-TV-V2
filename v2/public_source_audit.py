#!/usr/bin/env python3
"""Public, credential-free IPTV source audit. Never edits protected playlists.
Produces evidence of real HTTP source retrieval and candidate counts; not AV proof.
"""
import concurrent.futures
import json
import pathlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from real_ibo_scan import parse_m3u, tr_az, ROOT

MAIN_IBO_READ_ONLY = "https://raw.githubusercontent.com/Madsc55/Madsc55-Tv/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"

def inspect(source):
    sid, url = source["id"], source["url"]
    out = {"id": sid, "url": url, "status": "failed", "total": 0, "tr_az_candidates": 0, "candidate_urls": []}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-public-audit/1"})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = response.read(25_000_001)
        if len(data) > 25_000_000:
            raise ValueError("source exceeds 25MB")
        entries = list(parse_m3u(data))
        selected = [x["url"] for x in entries if tr_az(x, source.get("scope", "candidate"))]
        out.update(status="ok", total=len(entries),
                   tr_az_candidates=len(selected), candidate_urls=selected)
    except (OSError, ValueError, UnicodeError, urllib.error.URLError) as exc:
        out["error"] = type(exc).__name__
    return out

def main():
    sources = json.loads((ROOT / "v2/config/sources.json").read_text(encoding="utf-8"))["sources"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(inspect, sources))
    unique_urls = set().union(*(set(x["candidate_urls"]) for x in results))
    # Fail closed: never label a candidate as new without fetching the real IBO list.
    main_request = urllib.request.Request(MAIN_IBO_READ_ONLY, headers={"User-Agent": "MADSC55-TV-V2-public-audit/1"})
    with urllib.request.urlopen(main_request, timeout=30) as response:
        main_bytes = response.read(25_000_001)
    if len(main_bytes) > 25_000_000:
        raise ValueError("Protected main playlist exceeds size limit")
    main_urls = {x["url"] for x in parse_m3u(main_bytes)}
    if not main_urls:
        raise RuntimeError("Real primary IBO playlist unavailable or empty; refusing new-candidate counts")
    new_urls = unique_urls - main_urls
    # Keep individual stream URLs out of public reports; only aggregate counts are published.
    for item in results:
        item["unique_candidate_urls"] = len(set(item.pop("candidate_urls")))
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "REAL_NETWORK_SOURCE_AUDIT_NOT_AV_VERIFICATION",
        "sources_configured": len(sources),
        "sources_ok": sum(x["status"] == "ok" for x in results),
        "sources_failed": sum(x["status"] != "ok" for x in results),
        "candidate_occurrences_not_deduplicated": sum(x["tr_az_candidates"] for x in results),
        "unique_candidate_urls_across_sources": len(unique_urls),
        "real_main_ibo_reference": MAIN_IBO_READ_ONLY,
        "real_main_ibo_url_count": len(main_urls),
        "candidate_urls_already_in_main": len(unique_urls & main_urls),
        "new_candidate_urls_not_in_main_unverified": len(new_urls),
        "language_is_metadata_inference_not_audio_verified": True,
        "sources": results,
        "protected_playlist_modified": False,
        "ibo_packages_produced": False,
    }
    dest = ROOT / "v2/reports/public-source-audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["sources_ok"] == 0:
        raise SystemExit("All sources failed: no usable source audit")

if __name__ == "__main__":
    main()

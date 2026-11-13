#!/usr/bin/env python3
"""#34 offline integration of existing source reports; never executes discovery jobs."""
import argparse
import json
from pathlib import Path
from discovery_34 import curated_candidates, identity

ROOT = Path(__file__).resolve().parents[1]
REPORTS = {
    "official": ROOT / "v2/reports/official-tv-sites.json",
    "youtube": ROOT / "v2/reports/youtube-live-candidates.json",
    "m3u": ROOT / "v2/config/sources.json",
    "github_m3u": ROOT / "v2/reports/github-source-discovery.json",
    "gitlab_m3u": ROOT / "v2/reports/gitlab-m3u-source-discovery.json",
    "codeberg_m3u": ROOT / "v2/reports/codeberg-m3u-source-discovery.json",
}

def normalize(source, data):
    if not isinstance(data, dict):
        raise ValueError("Invalid discovery report")
    if source == "official":
        key, field = "channels", "official_site"
    elif source == "youtube":
        key, field = "results", "video_id"
    elif source == "m3u":
        key, field = "sources", "url"
    elif source in ("github_m3u", "gitlab_m3u", "codeberg_m3u"):
        key, field = "sources", "url"
    else:
        raise ValueError("Unknown source")
    items = data.get(key, [])
    if not isinstance(items, list):
        raise ValueError("Invalid discovery rows")
    rows = [{("video_id" if source == "youtube" else "url"): item.get(field, "")}
            for item in items if isinstance(item, dict) and
            (source != "m3u" or item.get("kind") == "m3u") and
            (source not in ("github_m3u", "gitlab_m3u", "codeberg_m3u") or item.get("status") == "SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED")]
    identity_source = "m3u" if source in ("github_m3u", "gitlab_m3u", "codeberg_m3u") else source
    candidates = curated_candidates(identity_source, rows)
    if source == "official":
        by_url = {item.get("official_site"): item for item in items if isinstance(item, dict)}
        for candidate in candidates:
            metadata = by_url.get(candidate["url"], {})
            candidate["name"] = str(metadata.get("name") or "")
            candidate["tvg_id"] = str(metadata.get("channel_id") or "")
            candidate["country"] = str(metadata.get("country") or "")
            candidate["status"] = str(metadata.get("status") or "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED")
    elif source == "youtube":
        by_id = {item.get("video_id"): item for item in items if isinstance(item, dict)}
        for candidate in candidates:
            video_id = candidate.get("source_id", "").split(":", 1)[-1]
            metadata = by_id.get(video_id, {})
            candidate["name"] = str(metadata.get("title") or "")
            candidate["group"] = str(metadata.get("channel") or "")
            candidate["status"] = str(metadata.get("status") or "DISCOVERED_NOT_LIVE_VERIFIED")
            candidate["region"] = str(metadata.get("region") or "WORLD")
    return candidates

def integrate(reports=REPORTS):
    records, errors = {}, []
    for source, path in reports.items():
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for item in normalize(source, data):
                records[item["source_id"]] = item
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append({"source": source, "error": type(exc).__name__})
    return {"policy": "CANDIDATES_ONLY_NO_PLAYLIST_WRITES", "candidates": list(records.values()),
            "errors": errors, "verified_av": 0}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="v2/reports/discovery-34-integrated.json")
    args = parser.parse_args()
    result = integrate()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print("Integrated candidate identities:", len(result["candidates"]), "Missing/invalid inputs:", len(result["errors"]))

if __name__ == "__main__":
    main()

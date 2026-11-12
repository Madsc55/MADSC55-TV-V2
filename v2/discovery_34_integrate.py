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
}

def normalize(source, data):
    if source == "official":
        rows = [{"url": x.get("official_site", "")} for x in data.get("channels", [])]
    elif source == "youtube":
        rows = [{"video_id": x.get("video_id", "")} for x in data.get("results", [])]
    elif source == "m3u":
        rows = [{"url": x.get("url", "")} for x in data.get("sources", []) if x.get("kind") == "m3u"]
    else:
        raise ValueError("Unknown source")
    return curated_candidates(source, rows)

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
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Integrated candidate identities:", len(result["candidates"]), "Missing/invalid inputs:", len(result["errors"]))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only mapping of candidate EPG IDs and logo hints."""
import datetime
import json
from discover import ROOT, LIVE, entries

def main():
    existing = {}
    for entry in entries(LIVE.read_text(encoding="utf-8-sig")):
        identifier = entry["tvg_id"].split("@")[0].strip().casefold()
        if identifier:
            existing.setdefault(identifier, []).append(entry)
    source = ROOT / "v2/reports/turkish-stream-candidates.json"
    catalog = json.loads(source.read_text(encoding="utf-8"))
    output = []
    for candidate in catalog["candidates"]:
        identifier = candidate["channel_id"].split("@")[0].strip().casefold()
        matches = existing.get(identifier, [])
        output.append({
            "channel_id": candidate["channel_id"],
            "url": candidate["url"],
            "existing_epg_ids": sorted({x["tvg_id"] for x in matches if x["tvg_id"]}),
            "existing_logo_hints": sorted({x["logo"] for x in matches if x["logo"]}),
            "status": "EXACT_ID_METADATA_HINT" if matches else "NO_EXACT_ID_MATCH"
        })
    report = {
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "policy": "READ_ONLY_HINTS_NOT_VERIFIED_NO_AUTO_ASSIGNMENT",
        "count": len(output),
        "matched": sum(x["status"] == "EXACT_ID_METADATA_HINT" for x in output),
        "items": output
    }
    path = ROOT / "v2/reports/candidate-assets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Candidate asset hints:", report["matched"], "of", report["count"])

if __name__ == "__main__":
    main()

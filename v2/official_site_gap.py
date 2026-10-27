#!/usr/bin/env python3
"""Read-only Turkish broadcaster site comparison with the current V2 playlist.

Does not claim a website is a stream, and does not extract DRM-protected media.
"""
import json
import pathlib
import re
from discover import ROOT, LIVE, entries

DIRECTORY = ROOT / "v2/reports/official-tv-sites.json"
OUT = ROOT / "v2/reports/official-tv-gap.json"
def norm(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold().replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c"))
def main():
    data = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    current = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    ids = {norm(e["tvg_id"]) for e in current if e["tvg_id"]}
    names = {norm(e["name"]) for e in current}
    missing, present = [], []
    for item in data["channels"]:
        channel_id = norm(item["channel_id"])
        channel_name = norm(item["name"])
        found = bool((channel_id and channel_id in ids) or (channel_name and channel_name in names))
        record = {**item, "playlist_match": "MATCHED_BY_ID_OR_NAME" if found else "NO_EXACT_MATCH_REVIEW_REQUIRED"}
        (present if found else missing).append(record)
    report = {"source": "official-tv-sites.json", "playlist_entries": len(current),
              "directory_entries": len(data["channels"]), "matched": len(present),
              "not_exactly_matched": len(missing),
              "warning": "No exact match does not mean channel absent; aliases, accents and suffixes may differ. Sites are not validated streams.",
              "unmatched_sites": missing, "matched_sites": present}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Official-site comparison:", "matched", len(present), "review", len(missing))
if __name__ == "__main__":
    main()

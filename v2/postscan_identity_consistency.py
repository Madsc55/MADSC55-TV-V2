#!/usr/bin/env python3
"""Read-only cross-source identity consistency audit; never approve from playlist metadata alone."""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "reports"
def norm(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(re.findall(r"[^\\W_]+", value, flags=re.UNICODE))
def main():
    candidates = json.loads((ROOT / "candidates.json").read_text(encoding="utf-8"))["candidates"]
    triage = json.loads((ROOT / "postscan-video_identity_review.json").read_text(encoding="utf-8"))
    lookup = {x["url_sha256"]: x for x in candidates}
    if len(lookup) != len(candidates) or len(triage) != len({x["url_sha256"] for x in triage}):
        raise SystemExit("Duplicate URL hashes; refusing inconsistent evidence")
    by_epg = defaultdict(list)
    for item in triage:
        digest = item["url_sha256"]
        if digest not in lookup:
            raise SystemExit("Identity candidate absent from immutable discovery")
        original = lookup[digest]
        epg = norm(original.get("tvg_id"))
        if epg:
            by_epg[epg].append(item)
    result = []
    counts = Counter()
    for item in triage:
        original = lookup[item["url_sha256"]]
        epg = norm(original.get("tvg_id"))
        name = norm(original.get("name"))
        peers = by_epg.get(epg, [])
        peer_names = {norm(lookup[x["url_sha256"]].get("name")) for x in peers}
        sources = {x.get("source") for x in peers}
        issues = []
        if not epg: issues.append("NO_EPG_ID")
        if not name: issues.append("NO_NAME")
        if len(peer_names) > 1: issues.append("EPG_ID_MULTIPLE_NAMES")
        if len(sources) == 1: issues.append("SINGLE_SOURCE_METADATA")
        if not original.get("logo"): issues.append("NO_LOGO")
        if not original.get("group"): issues.append("NO_CATEGORY")
        priority = "CONFLICT_REVIEW" if "EPG_ID_MULTIPLE_NAMES" in issues else ("MULTISOURCE_REVIEW" if len(sources) > 1 else "SINGLE_SOURCE_REVIEW")
        counts[priority] += 1
        result.append({"url_sha256": item["url_sha256"], "name": original.get("name"), "source": original.get("source"),
                       "tvg_id": original.get("tvg_id"), "source_count_same_epg": len(sources),
                       "distinct_names_same_epg": len(peer_names), "issues": issues,
                       "review_priority": priority, "identity_verified": False, "approved": False})
    if len(result) != len(triage):
        raise SystemExit("Incomplete identity audit")
    summary = {"total": len(result), "priority_counts": dict(counts), "approved": 0,
               "policy": "READ_ONLY_METADATA_CONSISTENCY_NOT_BROADCASTER_IDENTITY",
               "notes": "Agreement between playlists is not independent broadcaster verification. EPG and logo URL validity not tested."}
    (ROOT / "postscan-identity-consistency.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (ROOT / "postscan-identity-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
if __name__ == "__main__":
    main()

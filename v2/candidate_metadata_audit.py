#!/usr/bin/env python3
"""Read-only metadata audit of the complete deduplicated discovery inventory."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "v2/reports"

def main():
    discovery = json.loads((REPORTS / "candidates.json").read_text(encoding="utf-8"))
    playback = json.loads((REPORTS / "all-source-playback-aggregate.json").read_text(encoding="utf-8"))
    candidates = discovery["candidates"]
    by_hash = {item["url_sha256"]: item for item in playback["channel_results"]}
    output = []
    for item in candidates:
        name = item.get("name", "").strip()
        tvg_id = item.get("tvg_id", "").strip()
        group = item.get("group", "").strip()
        logo = item.get("logo", "").strip()
        tested = by_hash.get(item["url_sha256"])
        issues = []
        if not name: issues.append("MISSING_NAME")
        if not tvg_id: issues.append("MISSING_EPG_ID")
        if not group: issues.append("MISSING_CATEGORY")
        if not logo: issues.append("MISSING_LOGO")
        if not tested: issues.append("MISSING_PLAYBACK_EVIDENCE")
        elif tested.get("playback") != "VIDEO_DECODED": issues.append("NO_DECODED_VIDEO")
        elif not tested.get("audio"): issues.append("NO_AUDIO_EVIDENCE")
        # EPG IDs, logos and broadcaster identities require external verification.
        issues.append("IDENTITY_EPG_LOGO_NOT_INDEPENDENTLY_VERIFIED")
        output.append({"name": name, "source": item["source"], "url_sha256": item["url_sha256"],
                       "metadata_present": {"name": bool(name), "epg_id": bool(tvg_id),
                                            "category": bool(group), "logo": bool(logo)},
                       "playback": tested.get("playback") if tested else "NOT_TESTED",
                       "classification": ("REJECTED_PLAYBACK" if tested and tested.get("playback") != "VIDEO_DECODED" else "PENDING_REVIEW"), "issues": issues})
    counts = Counter(issue for item in output for issue in item["issues"])
    report = {"policy": "READ_ONLY_METADATA_AUDIT_NOT_IDENTITY_APPROVAL",
              "total_candidates": len(candidates), "total_audited": len(output),
              "playback_matched": sum(item["playback"] != "NOT_TESTED" for item in output),
              "issue_counts": dict(sorted(counts.items())), "channels": output}
    (REPORTS / "candidate-metadata-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if len(output) != discovery.get("total_unique_candidates"):
        raise SystemExit("Metadata audit incomplete")
    if report["playback_matched"] != len(output):
        raise SystemExit("Metadata audit missing playback evidence")
    print("Metadata audited:", len(output), "matched:", report["playback_matched"])

if __name__ == "__main__":
    main()

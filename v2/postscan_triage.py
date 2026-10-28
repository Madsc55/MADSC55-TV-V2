#!/usr/bin/env python3
"""Classify full scan evidence without claiming channel identity or publishing streams."""
import json
from collections import Counter
from pathlib import Path

REPORTS = Path(__file__).resolve().parent / "reports"

def main():
    discovery = json.loads((REPORTS / "candidates.json").read_text(encoding="utf-8"))
    playback = json.loads((REPORTS / "all-source-playback-aggregate.json").read_text(encoding="utf-8"))
    metadata = json.loads((REPORTS / "candidate-metadata-audit.json").read_text(encoding="utf-8"))
    by_hash = {x["url_sha256"]: x for x in playback["channel_results"]}
    meta_hash = {x["url_sha256"]: x for x in metadata["channels"]}
    candidates = discovery["candidates"]
    if len(by_hash) != len(candidates) or len(meta_hash) != len(candidates):
        raise SystemExit("Refusing partial or inconsistent audit inventory")
    if {x["url_sha256"] for x in candidates} != set(by_hash) or set(by_hash) != set(meta_hash):
        raise SystemExit("Discovery, playback and metadata URL hashes disagree")
    queues = {"PLAYBACK_REJECTED": [], "VIDEO_NO_AUDIO": [], "VIDEO_METADATA_GAPS": [], "VIDEO_IDENTITY_REVIEW": []}
    for item in candidates:
        digest = item["url_sha256"]
        tested, meta = by_hash[digest], meta_hash[digest]
        issues = meta.get("issues", [])
        if tested["playback"] != "VIDEO_DECODED":
            kind = "PLAYBACK_REJECTED"
        elif not tested.get("audio"):
            kind = "VIDEO_NO_AUDIO"
        elif any(x in issues for x in ("MISSING_NAME", "MISSING_EPG_ID", "MISSING_CATEGORY", "MISSING_LOGO")):
            kind = "VIDEO_METADATA_GAPS"
        else:
            kind = "VIDEO_IDENTITY_REVIEW"
        queues[kind].append({"url_sha256": digest, "name": item.get("name"), "source": item.get("source"),
                             "playback": tested["playback"], "audio": bool(tested.get("audio")),
                             "width": tested.get("video_width"), "height": tested.get("video_height"),
                             "issues": issues, "decision": "NOT_APPROVED"})
    summary = {"policy": "READ_ONLY_HASH_ONLY_NO_AUTOMATIC_APPROVAL",
               "total": len(candidates), "queues": {k: len(v) for k,v in queues.items()},
               "approved": 0, "coverage_complete": playback.get("coverage_complete") is True,
               "notes": "Video/audio and M3U metadata presence do not prove broadcaster identity, EPG mapping or logo rights."}
    if not summary["coverage_complete"] or sum(summary["queues"].values()) != len(candidates):
        raise SystemExit("Triage coverage incomplete")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "postscan-triage-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    for kind, rows in queues.items():
        (REPORTS / ("postscan-" + kind.lower() + ".json")).write_text(json.dumps(rows, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()

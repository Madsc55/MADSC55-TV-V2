#!/usr/bin/env python3
"""Produce a single deterministic, read-only action queue from the current scan."""
import json
from collections import Counter
from pathlib import Path

REPORTS = Path(__file__).resolve().parent / "reports"

def load(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))

def write(name, data):
    (REPORTS / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main():
    triage = load("postscan-triage-summary.json")
    identity = load("postscan-identity-consistency.json")
    metadata = load("candidate-metadata-audit.json")
    collisions = load("stream-url-collisions.json")
    playback = load("all-source-playback-aggregate.json")
    if not playback.get("coverage_complete") or triage["total"] != playback["unique_tested"] or metadata["total_audited"] != triage["total"]:
        raise SystemExit("Refusing partial or inconsistent scan evidence")
    if len(identity) != triage["queues"]["VIDEO_IDENTITY_REVIEW"]:
        raise SystemExit("Identity audit coverage mismatch")
    if sum(triage["queues"].values()) != triage["total"]:
        raise SystemExit("Triage queues do not cover all candidates")
    identity_conflicts = [x for x in identity if x["review_priority"] == "CONFLICT_REVIEW"]
    if len(identity_conflicts) != sum(x["review_priority"] == "CONFLICT_REVIEW" for x in identity):
        raise SystemExit("Identity conflict count mismatch")
    priorities = [
        {"priority": 1, "kind": "CROSS_CHANNEL_URL_COLLISION", "count": collisions["cross_channel_url_collision_count"],
         "items": collisions["cross_channel_url_collisions"], "action": "MANUAL_IDENTITY_REVIEW"},
        {"priority": 2, "kind": "SAME_NAME_TVG_METADATA_CONFLICT", "count": collisions["identity_metadata_conflict_count"],
         "items": collisions["identity_metadata_conflicts"], "action": "VERIFY_TVG_ID_WITHOUT_EDITING_LIVE"},
        {"priority": 3, "kind": "IDENTITY_CONFLICT", "count": len(identity_conflicts),
         "items": identity_conflicts, "action": "MANUAL_BROADCASTER_VERIFICATION"},
        {"priority": 4, "kind": "VIDEO_NO_AUDIO", "count": triage["queues"]["VIDEO_NO_AUDIO"],
         "report": "postscan-video_no_audio.json", "action": "RECHECK_AUDIO_EVIDENCE"},
        {"priority": 5, "kind": "VIDEO_METADATA_GAPS", "count": triage["queues"]["VIDEO_METADATA_GAPS"],
         "report": "postscan-video_metadata_gaps.json", "action": "VERIFY_MISSING_METADATA_WITH_SOURCE"},
        {"priority": 6, "kind": "VIDEO_IDENTITY_REVIEW", "count": triage["queues"]["VIDEO_IDENTITY_REVIEW"],
         "report": "postscan-video_identity_review.json", "action": "MANUAL_BROADCASTER_VERIFICATION"},
        {"priority": 7, "kind": "PLAYBACK_REJECTED", "count": triage["queues"]["PLAYBACK_REJECTED"],
         "report": "postscan-playback_rejected.json", "action": "QUARANTINE_FROM_PROMOTION"}
    ]
    output = {"policy": "READ_ONLY_NO_AUTO_PROMOTION_NO_LIVE_EDITS", "scan_candidates": triage["total"],
              "tested": playback["unique_tested"], "video_decoded": playback["video_decoded"],
              "approved": 0, "priorities": priorities,
              "protected": ["LIVE_IBO", "FAVORITES", "13_CATEGORIES", "TWO_ORIGINAL_BACKUPS"],
              "note": "Counts overlap; verified decoding is not broadcaster identity or publishing permission."}
    write("postscan-unified-action-queue.json", output)
    print(json.dumps({"tested": output["tested"], "priorities": [{"kind": p["kind"], "count": p["count"]} for p in priorities]}, ensure_ascii=False))

if __name__ == "__main__":
    main()

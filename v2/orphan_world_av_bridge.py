#!/usr/bin/env python3
"""Historical orphan SHA evidence bridge; never substitutes old AV for current playback."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re

SHA = re.compile(r"[0-9a-f]{64}\Z")


def reconcile(orphan, world):
    if (orphan.get("kind") != "FOUR_UPSTREAM_ORPHAN_REPAIR_EVIDENCE_NOT_IBO"
            or orphan.get("schema") != 1 or orphan.get("orphan_entries") != 55
            or orphan.get("unique_orphan_metadata_identities") != 50
            or orphan.get("protected_playlist_modified") is not False
            or orphan.get("plain_stream_urls_reported") is not False
            or orphan.get("ibo_device_verified") is not False
            or orphan.get("av_acceptance_rule") != "FFMPEG_VIDEO_AND_AUDIO_DECODED_ONLY"):
        raise ValueError("Unsafe or incomplete original orphan evidence")
    records = orphan.get("records")
    if not isinstance(records, list) or len(records) != 55:
        raise ValueError("Missing original 55 records")
    current, owners, identities = {}, defaultdict(set), set()
    for entry in records:
        ident = entry.get("extinf_sha256")
        if not isinstance(ident, str) or not SHA.fullmatch(ident):
            raise ValueError("Invalid original metadata hash")
        identities.add(ident)
        if not isinstance(entry.get("candidates"), list):
            raise ValueError("Missing original candidate list")
        for row in entry["candidates"]:
            digest, status, decoded = (row.get("url_sha256"), row.get("status"),
                                       row.get("ffmpeg_video_audio_decoded"))
            if (not isinstance(digest, str) or not SHA.fullmatch(digest)
                    or not isinstance(status, str) or not re.fullmatch("[A-Z_]{2,100}", status)
                    or type(decoded) is not bool
                    or decoded and (status != "VIDEO_AUDIO_DECODED"
                                    or row.get("video_stream") is not True
                                    or row.get("audio_stream") is not True)
                    or status == "VIDEO_AUDIO_DECODED" and not decoded):
                raise ValueError("False or malformed current decoder evidence")
            state = (status, decoded)
            if digest in current and current[digest] != state:
                raise ValueError("Conflicting current evidence for same candidate SHA")
            current[digest] = state
            owners[digest].add(ident)
    if (len(identities) != 50
            or len(current) != orphan.get("unique_candidate_urls_historically_or_officially_proven")
            or len(current) != orphan.get("all_proven_url_candidates_sealed_for_future_retest")
            or sum(x[1] for x in current.values()) !=
               orphan.get("unique_candidates_video_audio_verified")):
        raise ValueError("Orphan candidate count, identity or archive mismatch")
    if (world.get("kind") != "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE"
            or world.get("schema") != 1
            or world.get("protected_main_playlist_modified") is not False
            or world.get("plaintext_url_in_public_report") is not False
            or world.get("ibo_player_verified") is not False
            or world.get("probe_budget_expired") is not False
            or world.get("unprobed") != 0):
        raise ValueError("Untrusted previous worldwide scan")
    entries = world.get("candidates")
    if (not isinstance(entries, list)
            or len(entries) != world.get("unique_url_candidates")
            or world.get("probed") != len(entries)
            or world.get("sealed_url_count") != len(entries)):
        raise ValueError("Truncated previous worldwide evidence")
    previous, all_old_av = {}, 0
    for row in entries:
        digest = row.get("url_sha256")
        if (not isinstance(digest, str) or not SHA.fullmatch(digest) or digest in previous
                or any(type(row.get(k)) is not bool for k in ("decoded", "video", "audio"))
                or row["decoded"] and (row.get("status") != "VIDEO_AUDIO_DECODED"
                                       or not row["video"] or not row["audio"])
                or row.get("status") == "VIDEO_AUDIO_DECODED" and not row["decoded"]):
            raise ValueError("Invalid or contradictory historical AV proof")
        previous[digest] = row["decoded"]
        all_old_av += row["decoded"]
    if all_old_av != world.get("audio_video_decoded"):
        raise ValueError("Prior FFmpeg count mismatch")
    overlap = set(current) & set(previous)
    old_good = {h for h in overlap if previous[h]}
    current_good = {h for h, (_, good) in current.items() if good}
    old_only = old_good - current_good
    old_identities = set().union(*(owners[h] for h in old_good)) if old_good else set()
    current_identities = set().union(*(owners[h] for h in current_good)) if current_good else set()
    report = {
        "schema": 1, "kind": "V2_ORPHAN_50_PRIOR_WORLD_AV_SHA_BRIDGE",
        "prior_world_run_id": 41715476184, "current_orphan_run_id": 42005831377,
        "original_source_occurrences": 55, "original_channel_identities": 50,
        "exact_candidate_urls_preserved": len(current),
        "world_probed_urls": len(previous), "world_ffmpeg_video_audio": all_old_av,
        "orphan_candidate_hashes_in_world": len(overlap),
        "orphan_candidate_hashes_not_in_world": len(current) - len(overlap),
        "orphan_urls_with_prior_ffmpeg_video_audio": len(old_good),
        "orphan_identities_with_prior_ffmpeg_video_audio": len(old_identities),
        "orphan_urls_with_current_ffmpeg_video_audio": len(current_good),
        "orphan_identities_with_current_ffmpeg_video_audio": len(current_identities),
        "prior_decoded_not_currently_decoded": len(old_only),
        "prior_decoded_now_failed_statuses": dict(sorted(Counter(current[h][0] for h in old_only).items())),
        "prior_evidence_is_not_current_av": True, "ibo_device_verified": False,
        "original_inventory_preserved": True, "protected_playlist_modified": False,
        "plaintext_stream_urls_exported": False,
    }
    if "://" in json.dumps(report):
        raise ValueError("Plaintext URL in public AV report")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current-orphan", type=Path, required=True)
    p.add_argument("--previous-world", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if (args.output.exists() or args.output.is_symlink()
            or args.output.resolve() in {args.current_orphan.resolve(), args.previous_world.resolve()}):
        p.error("Refuse evidence overwrite")
    orphan = json.loads(args.current_orphan.read_text(encoding="utf-8"))
    world = json.loads(args.previous_world.read_text(encoding="utf-8"))
    report = reconcile(orphan, world)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("ORPHAN_50_PRIOR_WORLD_AV", json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

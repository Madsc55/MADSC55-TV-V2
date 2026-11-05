#!/usr/bin/env python3
"""Strict anonymous 50-identity resolution accounting: AV / candidate / no candidate.

Never claims green completion for a channel with only a URL or HTTP success.
Does not print stream URLs, alter the IBO playlist, or delete historical data.
"""
from collections import Counter
import argparse
import json
from pathlib import Path
import re

HASH = re.compile(r"[0-9a-f]{64}\Z")


def classify_report(data):
    guard = data.get("immutable_orphan_identity_guard", {})
    if (data.get("protected_playlist_modified") is not False
            or data.get("plain_stream_urls_reported") is not False
            or data.get("ibo_device_verified") is not False
            or guard.get("original_source_occurrences") != 55
            or guard.get("original_distinct_extinf_identities") != 50
            or guard.get("original_occurrences_missing_metadata") != 0
            or guard.get("original_source_occurrences_still_present") != 55
            or data.get("all_proven_url_candidates_sealed_for_future_retest")
                != data.get("unique_candidate_urls_historically_or_officially_proven")):
        raise ValueError("Original 55/50 identity, encryption or playlist guard failed")
    records = data.get("records")
    if not isinstance(records, list) or len(records) != 55:
        raise ValueError("Missing original 55 metadata occurrences")
    states = {}
    per_source = {}
    causes = Counter()
    for row in records:
        digest = row.get("extinf_sha256")
        source = row.get("source_id")
        candidates = row.get("candidates")
        if (not isinstance(digest, str) or not HASH.fullmatch(digest)
                or not isinstance(source, str)
                or not isinstance(candidates, list)):
            raise ValueError("Malformed original candidate identity")
        if "url" in row or "stream_url" in row:
            raise ValueError("Plaintext URLs in public source report")
        current = states.setdefault(digest, {"sources": set(), "has_candidate": False,
                                             "has_av": False,
                                             "url_sha256": set(), "diagnostics": set()})
        current["sources"].add(source)
        per_source.setdefault(source, set()).add(digest)
        for candidate in candidates:
            if not isinstance(candidate, dict) or "url" in candidate:
                raise ValueError("Unexpected private URL in public evidence")
            if not isinstance(candidate.get("url_sha256"), str) or not HASH.fullmatch(candidate["url_sha256"]):
                raise ValueError("Missing candidate URL hash")
            current["has_candidate"] = True
            current["url_sha256"].add(candidate["url_sha256"])
            decoded = candidate.get("ffmpeg_video_audio_decoded", False)
            if type(decoded) is not bool:
                raise ValueError("Decoder proof must be boolean")
            if ((decoded and (candidate.get("status") != "VIDEO_AUDIO_DECODED"
                              or candidate.get("video_stream") is not True
                              or candidate.get("audio_stream") is not True))
                    or candidate.get("status") == "VIDEO_AUDIO_DECODED" and not decoded):
                raise ValueError("FFprobe-only evidence cannot claim real AV")
            if decoded:
                current["has_av"] = True
            elif isinstance(candidate.get("diagnostic_category"), str):
                causes[candidate["diagnostic_category"]] += 1
                current["diagnostics"].add(candidate["diagnostic_category"])
    if len(states) != 50:
        raise ValueError("Original 50 distinct metadata hashes not preserved")
    status = {"video_audio_verified": 0, "candidate_av_unverified": 0,
              "without_valid_candidate": 0}
    source_breakdown = {x: {"verified": 0, "candidate_unverified": 0,
                            "no_candidate": 0} for x in per_source}
    # Hash-only identities are useful recovery work queues; unlike per-source
    # occurrence counts, these deduplicate the 55 original rows into exactly 50.
    identity_queues = {
        "video_audio_verified": [],
        "candidate_av_unverified": [],
        "without_valid_candidate": [],
    }
    for digest, state in sorted(states.items()):
        field = ("video_audio_verified" if state["has_av"] else
                 "candidate_av_unverified" if state["has_candidate"] else
                 "without_valid_candidate")
        status[field] += 1
        identity_queues[field].append({
            "original_extinf_sha256": digest,
            "original_source_ids": sorted(state["sources"]),
            "candidate_url_sha256": sorted(state["url_sha256"]),
            "diagnostic_categories": sorted(state["diagnostics"]),
        })
        for source in state["sources"]:
            source_breakdown[source][{"video_audio_verified":"verified",
                                     "candidate_av_unverified":"candidate_unverified",
                                     "without_valid_candidate":"no_candidate"}[field]] += 1
    remaining = 50 - status["video_audio_verified"]
    return {"schema": 1, "kind": "ORPHAN_50_REAL_AV_RESOLUTION_ANONYMOUS",
            "status": "ALL_50_AV_VERIFIED" if not remaining else "RECOVERY_INCOMPLETE_REAL_AV_REQUIRED",
            "original_occurrences_preserved": 55, "original_identities_preserved": 50,
            "video_audio_verified_identities": status["video_audio_verified"],
            "candidate_present_av_unverified_identities": status["candidate_av_unverified"],
            "no_valid_candidate_identities": status["without_valid_candidate"],
            "remaining_unverified_identities": remaining,
            "by_original_source": dict(sorted(source_breakdown.items())),
            "hash_only_identity_work_queues": identity_queues,
            "diagnostic_categories_not_playback_proof": dict(sorted(causes.items())),
            "encrypted_candidate_count": data.get("all_proven_url_candidates_sealed_for_future_retest"),
            "av_acceptance_rule": "FFMPEG_VIDEO_AND_AUDIO_DECODED_ONLY",
            "no_plaintext_urls_reported": True,
            "protected_ibo_playlist_unchanged": True, "ibo_device_verified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-only", action="store_true",
                        help="Write complete anonymous resolution diagnostics; final CI acceptance still fails on missing AV")
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        parser.error("Refusing to overwrite previous resolution evidence")
    result = classify_report(json.loads(args.report.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("RESCUED_AV", result["video_audio_verified_identities"],
          "CANDIDATE_UNVERIFIED", result["candidate_present_av_unverified_identities"],
          "NO_CANDIDATE", result["no_valid_candidate_identities"],
          "UNRESOLVED", result["remaining_unverified_identities"])
    if result["remaining_unverified_identities"] and not args.report_only:
        raise SystemExit("RECOVERY_INCOMPLETE_REAL_AV_REQUIRED")


if __name__ == "__main__":
    main()

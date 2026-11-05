#!/usr/bin/env python3
"""Strict anonymous actionability triage for the original 50 orphan identities.

This is NOT playback acceptance. Never infers missing URLs, never retries
forbidden hosts, and never downgrades protected original identities.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

_SHA = re.compile(r"[a-f0-9]{64}\Z")
_STATUS = re.compile(r"[A-Z_]{2,100}\Z")

def classify(status):
    if status == "VIDEO_AUDIO_DECODED":
        return "CURRENT_AV_DECODED"
    if status in ("PROBE_FAILED_HTTP_FORBIDDEN", "PROBE_FAILED_AUTH_REQUIRED"):
        return "ACCESS_RESTRICTED"
    if status == "PROBE_FAILED_HTTP_NOT_FOUND":
        return "HTTP_NOT_FOUND"
    if status == "UNSAFE_OR_UNRESOLVED_HOST":
        return "UNSAFE_OR_UNRESOLVED_HOST"
    if status in ("PROBE_FAILED_HTTP_RESPONSE_ERROR",
                  "PROBE_FAILED_NETWORK_TIMEOUT",
                  "PROBE_FAILED_DNS_RESOLUTION_ERROR", "PROBE_UNCONFIRMED"):
        return "NETWORK_ERROR_NOT_PLAYBACK_PROOF"
    return "MEDIA_OR_OTHER_FAILURE_NOT_PLAYBACK_PROOF"

def summarize(evidence):
    if (not isinstance(evidence, dict)
            or evidence.get("kind") != "FOUR_UPSTREAM_ORPHAN_REPAIR_EVIDENCE_NOT_IBO"
            or evidence.get("schema") != 1
            or evidence.get("orphan_entries") != 55
            or evidence.get("unique_orphan_metadata_identities") != 50
            or evidence.get("protected_playlist_modified") is not False
            or evidence.get("plain_stream_urls_reported") is not False
            or evidence.get("ibo_device_verified") is not False
            or evidence.get("av_acceptance_rule") != "FFMPEG_VIDEO_AND_AUDIO_DECODED_ONLY"):
        raise ValueError("Invalid or unsafe historical orphan report")
    rows = evidence.get("records")
    if not isinstance(rows, list) or len(rows) != 55:
        raise ValueError("Original 55 source occurrences missing")
    by_id = defaultdict(dict)
    reasons = defaultdict(set)
    sources = defaultdict(set)
    by_url = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Malformed original source occurrence")
        ident = row.get("extinf_sha256")
        if not isinstance(ident, str) or not _SHA.fullmatch(ident):
            raise ValueError("Bad immutable original metadata SHA")
        if row.get("source_id") not in (
                "discevisita-tr", "github-auto-24",
                "onureroz-turk-karma", "onureroz-turk-all"):
            raise ValueError("Unexpected original publisher")
        sources[ident].add(row["source_id"])
        reasons[ident].add(row.get("uri_structure"))
        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError("Candidate list omitted")
        for entry in candidates:
            if not isinstance(entry, dict):
                raise ValueError("Malformed candidate")
            digest, status, decoded = (entry.get("url_sha256"),
                                       entry.get("status"),
                                       entry.get("ffmpeg_video_audio_decoded"))
            if (not isinstance(digest, str) or not _SHA.fullmatch(digest)
                    or not isinstance(status, str) or not _STATUS.fullmatch(status)
                    or type(decoded) is not bool):
                raise ValueError("Malformed candidate status/SHA")
            video, audio = entry.get("video_stream"), entry.get("audio_stream")
            if type(video) is not bool or type(audio) is not bool:
                raise ValueError("Untrusted video/audio flags")
            if decoded != (status == "VIDEO_AUDIO_DECODED") or decoded and not (video and audio):
                raise ValueError("False current video/audio playback success")
            state = (status, decoded, video, audio)
            if digest in by_url and by_url[digest] != state:
                raise ValueError("Contradictory SHA-matched candidate")
            by_url[digest] = state
            if digest in by_id[ident] and by_id[ident][digest] != state:
                raise ValueError("Conflicting original identity status")
            by_id[ident][digest] = state
    if len(sources) != 50:
        raise ValueError("Not all 50 original identities preserved")
    if (len(by_url) != evidence.get("unique_candidate_urls_historically_or_officially_proven")
            or len(by_url) != evidence.get("all_proven_url_candidates_sealed_for_future_retest")
            or sum(s[1] for s in by_url.values()) != evidence.get("unique_candidates_video_audio_verified")):
        raise ValueError("Unique URL archive or real decoder count mismatch")
    identities, action_counts, state_counts = [], Counter(), Counter()
    for ident in sorted(sources):
        states = by_id.get(ident, {})
        good = any(v[1] for v in states.values())
        decision = ("CURRENT_FFMPEG_AV_PROVEN" if good else
                    "SOURCE_EXISTS_BUT_AV_NOT_PROVEN" if states else
                    "MISSING_EXACT_PUBLIC_STREAM_SOURCE")
        action_counts[decision] += 1
        for status, *_ in states.values():
            state_counts[status] += 1
        # No URL, name, host, private keys, raw metadata or stderr in output.
        identities.append({
            "original_extinf_sha256": ident,
            "source_ids": sorted(sources[ident]),
            "decision": decision,
            "unique_candidate_hash_count": len(states),
            "candidate_diagnostic_groups": sorted({classify(x[0]) for x in states.values()}),
            "no_candidate_original_uri_structures":
                sorted(x for x in reasons[ident] if isinstance(x, str)) if not states else [],
            "current_real_video_audio_verified": good
        })
    statuses = Counter(s[0] for s in by_url.values())
    result = {
        "schema": 1, "kind": "V2_ORPHAN_50_ANONYMOUS_RECOVERY_ACTIONABILITY",
        "original_source_occurrences": 55, "original_unique_identities": 50,
        "unique_sha256_candidate_urls": len(by_url),
        "candidate_url_status_counts": dict(sorted(statuses.items())),
        "current_ffmpeg_video_audio_verified": action_counts["CURRENT_FFMPEG_AV_PROVEN"],
        "has_candidate_but_current_av_unverified": action_counts["SOURCE_EXISTS_BUT_AV_NOT_PROVEN"],
        "no_exact_valid_candidate": action_counts["MISSING_EXACT_PUBLIC_STREAM_SOURCE"],
        "all_50_currently_decoded": action_counts["CURRENT_FFMPEG_AV_PROVEN"] == 50,
        "full_playback_recovery_completed": action_counts["CURRENT_FFMPEG_AV_PROVEN"] == 50,
        "original_metadata_identity_sha_preserved": True,
        "protected_playlist_modified": False,
        "ibo_device_verified": False,
        "plaintext_url_reported": False,
        "next_work_required": ("NONE_FOR_CURRENT_FFMPEG_AV" if action_counts["CURRENT_FFMPEG_AV_PROVEN"] == 50
                              else "NEW_EXACT_SOURCE_OR_PUBLISHER_RESTORATION_REQUIRED"),
        "identities": identities
    }
    if "://" in json.dumps(result):
        raise ValueError("Unexpected plaintext address in actionability report")
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.output.is_symlink() or a.output.resolve() == a.report.resolve():
        p.error("Refuse overwrite or same-file reports")
    evidence = json.loads(a.report.read_text(encoding="utf-8"))
    output = summarize(evidence)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    print("ORPHAN_50_ACTIONABILITY", json.dumps({
        k: v for k, v in output.items() if k not in ("identities", "candidate_url_status_counts")
    }, sort_keys=True))

if __name__ == "__main__":
    main()

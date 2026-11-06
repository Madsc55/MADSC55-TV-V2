#!/usr/bin/env python3
"""Read-only exact SHA crosswalk: immutable historical identities vs worldwide AV.

Never infer a channel from its name, metadata, EPG or an HTTP-only response.
No URL decryption, playlist writes, or device-playback claims.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from final_worldwide_report_gate import inspect

BASELINE_SHA256 = "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27"
HEX = set("0123456789abcdef")


def crosswalk(baseline_path, worldwide_path):
    baseline_path, worldwide_path = Path(baseline_path), Path(worldwide_path)
    if baseline_path.is_symlink() or worldwide_path.is_symlink():
        raise ValueError("Symlink evidence is not allowed")
    raw = baseline_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise ValueError("Historical baseline SHA mismatch")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    hashes = [row["url_sha256"] for row in rows]
    if len(hashes) != 4955 or len(set(hashes)) != 4955 or any(
        not isinstance(h, str) or len(h) != 64 or set(h) - HEX for h in hashes
    ):
        raise ValueError("Historical identities incomplete or malformed")
    # Validate the *whole* AV report, including sealed-manifest integrity.
    acceptance = inspect(worldwide_path, require_complete=True)
    report = json.loads(worldwide_path.read_text(encoding="utf-8"))
    by_hash = {row["url_sha256"]: row for row in report["candidates"]}
    if len(by_hash) != len(report["candidates"]):
        raise ValueError("Duplicate worldwide URL SHA identities")
    matched = set(hashes) & set(by_hash)
    decoded = {h for h in matched if by_hash[h]["status"] == "VIDEO_AUDIO_DECODED"
               and by_hash[h]["decoded"] is True
               and by_hash[h]["video"] is True and by_hash[h]["audio"] is True}
    # Distinguish unproven probe outcomes without treating transient failures as dead.
    unproven = matched - decoded
    unproven_status_counts = dict(sorted(Counter(
        by_hash[h]["status"] for h in unproven
    ).items()))
    unproven_by_status = {
        status: sorted(h for h in unproven if by_hash[h]["status"] == status)
        for status in unproven_status_counts
    }
    # Priority is an investigation queue, not a claim that a URL is recoverable.
    retryable = {
        "PROBE_FAILED_NETWORK_TIMEOUT", "PROBE_FAILED_DNS_RESOLUTION_ERROR",
        "PROBE_FAILED_HTTP_RESPONSE_ERROR", "PROBE_FAILED_REDIRECT_REQUIRED_OR_BLOCKED",
        "PROBE_FAILED_UNKNOWN_NETWORK_OR_MEDIA_ERROR",
        "PROBE_UNCONFIRMED", "UNVERIFIED",
    }
    media_partial = {"VIDEO_ONLY", "AUDIO_ONLY", "VIDEO_AUDIO_STREAMS_ONLY"}
    auth_or_missing = {"NOT_PROBED_BUDGET",
        "PROBE_FAILED_AUTH_REQUIRED", "PROBE_FAILED_HTTP_FORBIDDEN",
        "PROBE_FAILED_HTTP_NOT_FOUND", "UNSAFE_OR_UNRESOLVED_HOST",
        "PROBE_FAILED_PROTOCOL_DISALLOWED_BY_SAFETY",
    }
    # No network retry of unprobed/unsafe entries is implied by queue membership.
    priority = {"partial_media": [], "transient_retry": [],
                "source_research": [], "other_unproven": []}
    for h in sorted(unproven):
        status = by_hash[h]["status"]
        group = ("partial_media" if status in media_partial else
                 "transient_retry" if status in retryable else
                 "source_research" if status in auth_or_missing else
                 "other_unproven")
        priority[group].append(h)
    result = {
        "schema": 1,
        "kind": "V2_HISTORICAL_WORLDWIDE_EXACT_SHA_AV_CROSSWALK",
        "policy": "READ_ONLY_HASH_ONLY_NO_IBO_PROMOTION",
        "historical_baseline_sha256": BASELINE_SHA256,
        "worldwide_report_sha256": hashlib.sha256(worldwide_path.read_bytes()).hexdigest(),
        "historical_identities_preserved": len(hashes),
        "worldwide_candidates": len(by_hash),
        "worldwide_av_decoded": sum(row["decoded"] is True for row in by_hash.values()),
        "historical_exact_hash_matches": len(matched),
        "historical_exact_hash_av_decoded": len(decoded),
        "historical_matched_without_av_proof": len(unproven),
        "historical_unproven_status_counts": unproven_status_counts,
        "historical_unproven_url_sha256_by_status": unproven_by_status,
        "historical_recovery_review_counts": {k: len(v) for k, v in priority.items()},
        "historical_recovery_review_url_sha256": priority,
        "historical_not_in_worldwide_report": len(hashes) - len(matched),
        "historical_decoded_url_sha256": sorted(decoded),
        "historical_match_url_sha256": sorted(matched),
        "historical_missing_worldwide_url_sha256": sorted(set(hashes) - set(by_hash)),
        "protected_playlist_modified": False,
        "ibo_device_verified": False,
        "historical_broadcaster_identity_verified": False,
    }
    # Fail closed if any historical identity is omitted or counted twice.
    missing = set(hashes) - matched
    queues = [set(group) for group in priority.values()]
    if (matched & missing or matched | missing != set(hashes)
            or sum(map(len, queues)) != len(unproven)
            or set().union(*queues) != unproven
            or sum(unproven_status_counts.values()) != len(unproven)
            or len(decoded) + len(unproven) + len(missing) != 4955):
        raise ValueError("Historical AV crosswalk lossless partition failed")
    if result["worldwide_candidates"] != acceptance["candidate_hashes"]:
        raise ValueError("Validated candidate tally changed")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--worldwide", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.is_symlink() or args.out.suffix != ".json":
        raise ValueError("Unsafe output path")
    result = crosswalk(args.baseline, args.worldwide)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("HISTORICAL_EXACT_SHA_AV", json.dumps({
        k: result[k] for k in ("historical_identities_preserved",
            "historical_exact_hash_matches", "historical_exact_hash_av_decoded",
            "historical_not_in_worldwide_report")}, sort_keys=True))


if __name__ == "__main__":
    main()

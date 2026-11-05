#!/usr/bin/env python3
"""Offline checks of anonymous worldwide acceptance and sealed URL manifests.

Never decrypt or expose candidate URLs. These checks prove manifest integrity and
consistent summaries, not successful playback on a user device.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

HASH = re.compile(r"[0-9a-f]{64}\Z")
SEALED = re.compile(r"final-worldwide-[0-9]{3}\.sealed\Z")
STREAM_URL = re.compile(r"(?:https?|rtmps?|rtsp)://", re.I)


def inspect(report_path: Path, require_complete=True):
    """Return anonymized validation counts. Raise ValueError if evidence invalid."""
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("WORLD_REPORT_NOT_OBJECT")
    def require(test, code):
        if not test:
            raise ValueError(code)
    require(report.get("schema") == 1 and
            report.get("kind") == "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
            "WRONG_REPORT_SCHEMA")
    for name, expected in {
        "protected_main_playlist_modified": False,
        "ibo_player_verified": False,
        "plaintext_url_in_public_report": False,
        "source_metadata_and_audio_track_language_tags_are_not_speech_proof": True,
        "spoken_language_verified": 0,
    }.items():
        require(report.get(name) is expected if isinstance(expected, bool)
                else report.get(name) == expected, "INVALID_PRIVACY_OR_PLAYBACK_PROOF_" + name)
    require(report.get("readiness") == "REVIEW_REQUIRED", "FALSE_READY_CLAIM")
    candidates = report.get("candidates")
    require(isinstance(candidates, list), "MISSING_CANDIDATES")
    count = report.get("unique_url_candidates")
    require(type(count) is int and count == len(candidates), "CANDIDATE_COUNT_MISMATCH")
    require(count > 0, "NO_REAL_CANDIDATE_INVENTORY")
    seen = set()
    statuses = Counter()
    routes = Counter()
    decoded = 0
    unprobed = 0
    evidence_origins = Counter()
    origin_tracking = "evidence_origin_counts" in report
    if origin_tracking:
        require(isinstance(report["evidence_origin_counts"], dict),
                "INVALID_EVIDENCE_ORIGIN_DISTRIBUTION")
        require(all(k in ("CURRENT_RUN_FFPROBE_FFMPEG",
                          "PRIOR_RUN_HASH_ONLY_NOT_FRESH") and
                    type(v) is int and v > 0
                    for k, v in report["evidence_origin_counts"].items()),
                "INVALID_EVIDENCE_ORIGIN_DISTRIBUTION")
    for i, row in enumerate(candidates):
        require(isinstance(row, dict), "INVALID_CANDIDATE_OBJECT")
        h = row.get("url_sha256")
        require(isinstance(h, str) and HASH.fullmatch(h), "INVALID_CANDIDATE_SHA")
        require(h not in seen, "DUPLICATE_CANDIDATE_SHA")
        seen.add(h)
        require(not any(k in row for k in ("url", "stream_url", "raw_url", "href")),
                "PLAINTEXT_URL_FIELD")
        require(not STREAM_URL.search(json.dumps(row, ensure_ascii=False)),
                "PLAINTEXT_URL_EXPOSURE")
        require(isinstance(row.get("source_ids"), list) and row["source_ids"],
                "MISSING_SOURCE_PROVENANCE")
        require(row.get("spoken_language_verified") is False and
                row.get("ibo_player_verified") is False, "UNSUPPORTED_VERIFICATION_CLAIM")
        if origin_tracking:
            origin = row.get("evidence_origin")
            require(origin in ("CURRENT_RUN_FFPROBE_FFMPEG",
                               "PRIOR_RUN_HASH_ONLY_NOT_FRESH", "NOT_PROBED"),
                    "INVALID_EVIDENCE_ORIGIN")
            evidence_origins[origin] += 1
        st = row.get("status")
        require(isinstance(st, str) and st, "MISSING_PROBE_STATUS")
        if st == "NOT_PROBED_BUDGET":
            if origin_tracking:
                require(row["evidence_origin"] == "NOT_PROBED",
                        "UNPROBED_MISLABELED_AS_AV_EVIDENCE")
            unprobed += 1
        else:
            if origin_tracking:
                require(row["evidence_origin"] != "NOT_PROBED",
                        "PROBED_MISLABELED_AS_UNPROBED")
            statuses[st] += 1
        route = row.get("language_route")
        require(isinstance(route, str) and route, "MISSING_LANGUAGE_ROUTE")
        routes[route] += 1
        for key in ("video", "audio", "decoded"):
            require(type(row.get(key)) is bool, "INVALID_AV_BOOL")
        expected_av = {
            "VIDEO_AUDIO_DECODED": (True, True, True),
            "VIDEO_AUDIO_STREAMS_ONLY": (True, True, False),
            "VIDEO_ONLY": (True, False, False),
            "AUDIO_ONLY": (False, True, False),
            "NO_AV": (False, False, False),
        }
        if row["decoded"]:
            require(row["video"] and row["audio"] and st == "VIDEO_AUDIO_DECODED",
                    "FALSE_AV_DECODE_CLAIM")
        if st in expected_av:
            require((row["video"], row["audio"], row["decoded"]) == expected_av[st],
                    "INCONSISTENT_AV_STATUS_FLAGS")
        elif st == "NOT_PROBED_BUDGET":
            require(not (row["video"] or row["audio"] or row["decoded"]),
                    "UNPROBED_WITH_AV_FLAGS")
        else:
            require(not (row["video"] or row["audio"] or row["decoded"]),
                    "FAILED_PROBE_WITH_AV_FLAGS")
        if row["decoded"]:
            decoded += 1
    def integer(key):
        x = report.get(key)
        require(type(x) is int and x >= 0, "INVALID_TOTAL_" + key)
        return x
    probed = integer("probed")
    require(probed + integer("unprobed") == count, "PROBE_COVERAGE_COUNT_MISMATCH")
    require(unprobed == report["unprobed"] and sum(statuses.values()) == probed,
            "CANDIDATE_STATUS_COUNT_MISMATCH")
    require(report.get("av_status_counts") == dict(statuses), "AV_STATUS_DISTRIBUTION_MISMATCH")
    if origin_tracking:
        require(report["evidence_origin_counts"] == dict(
            (key, val) for key, val in evidence_origins.items()
            if key != "NOT_PROBED"), "EVIDENCE_ORIGIN_DISTRIBUTION_MISMATCH")
    require(report.get("metadata_language_route_counts") == dict(routes),
            "LANGUAGE_ROUTE_DISTRIBUTION_MISMATCH")
    require(integer("audio_video_decoded") == decoded, "DECODED_TOTAL_MISMATCH")
    require(integer("source_success_count") <= integer("source_fetch_count"),
            "SOURCE_FETCH_COUNT_MISMATCH")
    require(integer("sealed_url_count") == count, "SEALED_TOTAL_MISMATCH")
    manifest = report.get("sealed_artifacts")
    require(isinstance(manifest, list) and manifest, "MISSING_SEALED_MANIFEST")
    chunk_sum = 0
    names = set()
    for chunk in manifest:
        require(isinstance(chunk, dict), "INVALID_SEALED_ENTRY")
        name = chunk.get("name")
        digest = chunk.get("sha256")
        require(isinstance(name, str) and SEALED.fullmatch(name), "UNSAFE_SEALED_FILENAME")
        require(name not in names, "DUPLICATE_SEALED_FILENAME")
        names.add(name)
        require(isinstance(digest, str) and HASH.fullmatch(digest), "INVALID_SEALED_CHECKSUM")
        size = chunk.get("count")
        require(type(size) is int and 0 < size <= 4000, "INVALID_SEALED_ROW_COUNT")
        chunk_sum += size
        file = report_path.parent / name
        require(file.is_file() and file.stat().st_size > 0, "SEALED_FILE_MISSING")
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        require(actual == digest, "SEALED_CHECKSUM_MISMATCH")
    require(chunk_sum == count, "SEALED_CHUNK_TOTAL_MISMATCH")
    require(len(manifest) == (count + 3999) // 4000, "SEALED_CHUNK_NUMBER_MISMATCH")
    require(bool(report.get("probe_budget_expired")) == bool(unprobed) or not unprobed,
            "BUDGET_EXPIRY_INCONSISTENT")
    if require_complete:
        require(unprobed == 0 and report.get("probe_budget_expired") is False,
                "SOME_URLS_UNPROBED_BUDGET")
    return {
        "status": "COMPLETE_AV_COVERAGE_EVIDENCE" if unprobed == 0 else "PARTIAL_AV_COVERAGE_EVIDENCE",
        "candidate_hashes": count,
        "probed": probed,
        "unprobed": unprobed,
        "decoded_video_audio": decoded,
        "sealed_artifacts": len(manifest),
        "sealed_candidate_count": chunk_sum,
        "playlist_untouched": True,
        "ibo_player_test_not_claimed": True,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=Path("v2/reports/ci/final-worldwide-acceptance.json"))
    parser.add_argument("--allow-unprobed", action="store_true", help="Only audit encrypted preservation, never claim full coverage")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.report, require_complete=not args.allow_unprobed)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("FINAL_WORLDWIDE_REPORT_GATE_FAIL:", str(exc)[:140])
        return 1
    print("FINAL_WORLDWIDE_REPORT_GATE", json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

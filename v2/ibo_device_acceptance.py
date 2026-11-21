#!/usr/bin/env python3
"""Validate manually collected IBO Player device evidence without claiming playback."""
import argparse
import datetime as dt
import json
import pathlib
import re

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REQUIRED_UI_CHECKS = (
    "playlist_loaded",
    "categories_visible",
    "yedekler_visible",
    "favorites_visible",
    "epg_visible",
)
TOP_LEVEL_KEYS = {
    "schema_version", "session_id", "tested_at", "device_model",
    "player_app_version", "playlist_url", "playlist_sha256",
    "ui_checks", "channel_results", "errors", "evidence_refs",
}
CHANNEL_KEYS = {
    "channel_id", "entry_sha256", "video_observed", "audio_observed",
    "observed_seconds", "evidence_refs",
}


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_report(report):
    """Return a validation summary; this function can never grant production PASS."""
    if not isinstance(report, dict) or set(report) != TOP_LEVEL_KEYS:
        raise ValueError("device report has missing or unexpected top-level fields")
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ValueError("unsupported device evidence schema")
    for key in ("session_id", "device_model", "player_app_version"):
        if not _nonempty(report[key]):
            raise ValueError(f"missing {key}")
    if not _nonempty(report["tested_at"]):
        raise ValueError("missing tested_at")
    try:
        timestamp = dt.datetime.fromisoformat(report["tested_at"].replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise ValueError("tested_at must be an ISO-8601 timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("tested_at must include a timezone")
    if report["playlist_url"] != "https://raw.githubusercontent.com/Madsc55/MADSC55-TV-V2/main/MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
        raise ValueError("device evidence must reference the canonical main playlist")
    if not isinstance(report["playlist_sha256"], str) or SHA256.fullmatch(report["playlist_sha256"]) is None:
        raise ValueError("invalid playlist SHA-256")
    ui = report["ui_checks"]
    if not isinstance(ui, dict) or set(ui) != set(REQUIRED_UI_CHECKS):
        raise ValueError("incomplete UI/category/EPG checks")
    if any(type(ui[key]) is not bool for key in REQUIRED_UI_CHECKS):
        raise ValueError("UI checks must be explicit booleans")
    if not isinstance(report["channel_results"], list) or not report["channel_results"]:
        raise ValueError("at least one manually tested channel is required")
    seen_ids, seen_hashes = set(), set()
    for item in report["channel_results"]:
        if not isinstance(item, dict) or set(item) != CHANNEL_KEYS:
            raise ValueError("channel result has missing or unexpected fields")
        if not _nonempty(item["channel_id"]):
            raise ValueError("missing exact channel_id")
        digest = item["entry_sha256"]
        if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            raise ValueError("invalid channel entry SHA-256")
        if item["channel_id"] in seen_ids or digest in seen_hashes:
            raise ValueError("duplicate channel identity or entry hash")
        seen_ids.add(item["channel_id"])
        seen_hashes.add(digest)
        if type(item["video_observed"]) is not bool or type(item["audio_observed"]) is not bool:
            raise ValueError("video/audio observations must be explicit booleans")
        if type(item["observed_seconds"]) is not int or item["observed_seconds"] <= 0:
            raise ValueError("observed_seconds must be a positive integer")
        refs = item["evidence_refs"]
        if not isinstance(refs, list) or not refs or any(not _nonempty(ref) for ref in refs):
            raise ValueError("each channel needs at least one evidence reference")
    if not isinstance(report["errors"], list) or any(not _nonempty(e) for e in report["errors"]):
        raise ValueError("errors must be a list of non-empty descriptions")
    if not isinstance(report["evidence_refs"], list) or not report["evidence_refs"] or any(not _nonempty(ref) for ref in report["evidence_refs"]):
        raise ValueError("session evidence references are required")
    complete = (
        all(ui.values())
        and all(x["video_observed"] and x["audio_observed"] for x in report["channel_results"])
        and not report["errors"]
    )
    return {
        "status": "EVIDENCE_COMPLETE_REQUIRES_HUMAN_REVIEW" if complete else "EVIDENCE_RECORDED_WITH_FAILURES",
        "production_accepted": False,
        "device_playback_certified": False,
        "channels_reviewed": len(report["channel_results"]),
        "channels_with_video_and_audio_observed": sum(
            x["video_observed"] and x["audio_observed"] for x in report["channel_results"]
        ),
        "ui_checks_passed": sum(ui.values()),
        "ui_checks_total": len(REQUIRED_UI_CHECKS),
        "errors_recorded": len(report["errors"]),
        "playlist_sha256": report["playlist_sha256"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = validate_report(json.loads(args.report.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

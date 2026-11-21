#!/usr/bin/env python3
"""Build a deterministic, read-only plan for the 685 historical uncertain rows.

This module performs no network requests, FFmpeg work, retries, playlist writes,
archive moves, or channel reclassification. It only binds the accepted #497
manifest to the exact current YEDEKLER block and URL identities.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
from pathlib import Path

from ibo_single_playlist_transfer import category, parse
from ibo_test_result_reconcile import digest

SOURCE_RUN_ID = 44640007709
SOURCE_HEAD_SHA = "1e8bd6d46762366f151e1270cc767f598c8e63e8"
SOURCE_ARTIFACT_ID = 14587983768
SOURCE_REPORT_FILE_SHA256 = "30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c"
SOURCE_REPORT_CANONICAL_SHA256 = "b48bd57ba03a7e4ee4eedf3f65355572e267db87b4d48c6d4fb390b8484dc55c"
SOURCE_PLAYLIST_SHA256 = "eee260cce3926caff18238f9583958b40475e362ce7650fb7fac51a66a84ee1c"
INITIAL_MANIFEST_SHA256 = "b001bf48f07437e9ae67ed9f73b12ea9cfcab653523973435cf3b1cee3c31fcc"
EXPECTED_CURRENT_YEDEKLER = 1792
EXPECTED_VERIFIED = 1107
EXPECTED_UNCERTAIN = 685
_HEX64 = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Missing source timestamp")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid source timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Source timestamp must include a timezone")
    return parsed.isoformat()


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def build_plan(raw, manifest, manifest_bytes, *, require_known_snapshot=False):
    if not isinstance(manifest, dict):
        raise ValueError("Initial preview manifest must be an object")
    manifest_sha = digest(manifest_bytes)
    if require_known_snapshot and manifest_sha != INITIAL_MANIFEST_SHA256:
        raise ValueError("Initial manifest SHA-256 mismatch")
    if manifest.get("source_run_id") != SOURCE_RUN_ID:
        raise ValueError("Historical source run mismatch")
    if manifest.get("source_head_sha") != SOURCE_HEAD_SHA:
        raise ValueError("Historical source commit mismatch")
    if manifest.get("source_artifact_id") != SOURCE_ARTIFACT_ID:
        raise ValueError("Historical source artifact mismatch")
    if manifest.get("source_report_file_sha256") != SOURCE_REPORT_FILE_SHA256:
        raise ValueError("Historical source report file hash mismatch")
    if manifest.get("source_report_canonical_sha256") != SOURCE_REPORT_CANONICAL_SHA256:
        raise ValueError("Historical source report canonical hash mismatch")
    if manifest.get("source_playlist_sha256") != SOURCE_PLAYLIST_SHA256:
        raise ValueError("Historical source playlist hash mismatch")
    if manifest.get("current_playlist_sha256") != digest(raw):
        raise ValueError("Current canonical playlist changed after accepted preview")
    if manifest.get("counts") != {"verified": EXPECTED_VERIFIED,
                                  "uncertain": EXPECTED_UNCERTAIN}:
        raise ValueError("Historical evidence counts mismatch")
    if (manifest.get("source_yedekler_count") != EXPECTED_CURRENT_YEDEKLER or
            manifest.get("current_yedekler_count") != EXPECTED_CURRENT_YEDEKLER or
            manifest.get("ordered_yedekler_blocks_identical") is not True):
        raise ValueError("Historical/current YEDEKLER identity snapshot mismatch")
    if (manifest.get("preview_only") is not True or
            manifest.get("new_scan_started") is not False or
            manifest.get("canonical_playlist_written") is not False):
        raise ValueError("Initial evidence is not an accepted read-only preview")

    selected = [block for block in parse(raw)[1]
                if category(block.splitlines()[0]) == "YEDEKLER"]
    if len(selected) != EXPECTED_CURRENT_YEDEKLER:
        raise ValueError("Current YEDEKLER count is not 1,792")
    blocks_by_hash = {}
    for position, block in enumerate(selected, 1):
        channel_hash = digest(block.encode("utf-8"))
        if channel_hash in blocks_by_hash:
            raise ValueError("Duplicate current immutable channel identity")
        blocks_by_hash[channel_hash] = (position, block)

    queue = manifest.get("retry_queue")
    if not isinstance(queue, list) or len(queue) != EXPECTED_UNCERTAIN:
        raise ValueError("Initial uncertain queue must contain exactly 685 rows")
    queue_by_hash = {}
    source_timestamp = None
    for item in queue:
        if not isinstance(item, dict):
            raise ValueError("Malformed initial retry queue item")
        channel_hash = item.get("channel_sha256")
        url_hash = item.get("url_sha256")
        if not isinstance(channel_hash, str) or not _HEX64.fullmatch(channel_hash):
            raise ValueError("Invalid immutable channel hash")
        if not isinstance(url_hash, str) or not _HEX64.fullmatch(url_hash):
            raise ValueError("Invalid URL hash")
        if channel_hash in queue_by_hash:
            raise ValueError("Duplicate channel in initial retry queue")
        if item.get("run_id") != SOURCE_RUN_ID:
            raise ValueError("Queue item source run mismatch")
        if item.get("evidence_sha256") != SOURCE_REPORT_CANONICAL_SHA256:
            raise ValueError("Queue item source evidence hash mismatch")
        if type(item.get("attempts")) is not int or item["attempts"] != 1:
            raise ValueError("Initial attempt count must be exactly one")
        if item.get("status") != "uncertain" or item.get("reason") != "recheck_required":
            raise ValueError("Only original uncertain/recheck-required rows are permitted")
        stamp = _timestamp(item.get("source_timestamp_utc"))
        if source_timestamp is None:
            source_timestamp = stamp
        elif stamp != source_timestamp:
            raise ValueError("Queue timestamps do not match the source snapshot")
        match = blocks_by_hash.get(channel_hash)
        if match is None:
            raise ValueError("Queue channel is absent from current YEDEKLER")
        position, block = match
        url = block.splitlines()[-1].strip()
        if digest(url.encode("utf-8")) != url_hash:
            raise ValueError("Queue URL hash does not match current channel identity")
        queue_by_hash[channel_hash] = {
            "position": position,
            "name": block.splitlines()[0].rsplit(",", 1)[-1].strip(),
            "channel_sha256": channel_hash,
            "url_sha256": url_hash,
            "source_run_id": SOURCE_RUN_ID,
            "source_artifact_id": SOURCE_ARTIFACT_ID,
            "source_timestamp_utc": stamp,
            "attempts_completed": 1,
            "next_attempt_number": 2,
            "source_status": "uncertain",
            "reason": "recheck_required",
            "plan_status": "PENDING_FINAL_TEST_AUTHORIZATION",
            "live_retry_authorized": False,
        }
    if len(queue_by_hash) != EXPECTED_UNCERTAIN:
        raise ValueError("Retry plan did not bind all 685 unique channels")
    if set(queue_by_hash) & (set(blocks_by_hash) - set(queue_by_hash)):
        raise ValueError("Retry queue identity overlap error")

    items = sorted(queue_by_hash.values(), key=lambda row: row["position"])
    plan = {
        "schema_version": 1,
        "plan_type": "READ_ONLY_UNCERTAIN_RETRY_PLAN",
        "plan_status": "PENDING_FINAL_TEST_AUTHORIZATION",
        "playlist_sha256": digest(raw),
        "initial_manifest_sha256": manifest_sha,
        "source_run_id": SOURCE_RUN_ID,
        "source_head_sha": SOURCE_HEAD_SHA,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_report_file_sha256": SOURCE_REPORT_FILE_SHA256,
        "source_report_canonical_sha256": SOURCE_REPORT_CANONICAL_SHA256,
        "source_timestamp_utc": source_timestamp,
        "inventory_count": EXPECTED_CURRENT_YEDEKLER,
        "historically_verified_count": EXPECTED_VERIFIED,
        "uncertain_retry_plan_count": EXPECTED_UNCERTAIN,
        "retry_scope": "uncertain_only",
        "items": items,
        "network_attempts": 0,
        "new_scan_started": False,
        "live_retry_authorized": False,
        "automatic_reclassification": False,
        "playlist_write_allowed": False,
        "archive_write_allowed": False,
        "category_mutation_allowed": False,
    }
    plan["plan_sha256"] = digest(_canonical(plan))
    return plan


def write_plan(path, plan):
    destination = Path(path)
    if destination.is_symlink():
        raise ValueError("Refusing symlink output")
    payload = json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    try:
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        if destination.is_file() and destination.read_bytes() == payload:
            return "ALREADY_PRESENT"
        raise ValueError("Refusing to overwrite a different retry plan")
    with os.fdopen(fd, "wb") as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    return "CREATED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path,
                        default=Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"))
    parser.add_argument("--initial-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
        parser.error("Only the canonical main playlist is supported")
    if args.output.resolve().is_relative_to(Path.cwd().resolve()):
        parser.error("Retry plan output must be outside the repository")
    raw = args.playlist.read_bytes()
    manifest_bytes = args.initial_manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    plan = build_plan(raw, manifest, manifest_bytes, require_known_snapshot=True)
    result = write_plan(args.output, plan)
    print(json.dumps({"result": result, "plan_sha256": plan["plan_sha256"],
                      "retry_count": plan["uncertain_retry_plan_count"],
                      "live_retry_authorized": False, "new_scan_started": False},
                     sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only retry of the 685 uncertain YEDEKLER entries from the accepted #497 manifest."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
from collections import Counter

from ibo_single_playlist_transfer import parse, category
from stream_probe import probe, verify_decoded_av

PLAYLIST = Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
WORKERS = 32
TIMEOUT = 15
SOURCE_RUN_ID = 44640007709
SOURCE_REPORT_SHA256 = "30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c"
SOURCE_PLAYLIST_SHA256 = "eee260cce3926caff18238f9583958b40475e362ce7650fb7fac51a66a84ee1c"
INITIAL_MANIFEST_RUN_ID = 44842556117
INITIAL_MANIFEST_ARTIFACT_ID = 14681083208
INITIAL_MANIFEST_ARTIFACT_SHA256 = "8e269517a92203131633e024c6329c8a5f9a9095746f2ee375d185e4cc3b0f45"
INITIAL_MANIFEST_SHA256 = "b001bf48f07437e9ae67ed9f73b12ea9cfcab653523973435cf3b1cee3c31fcc"
INITIAL_CURRENT_PLAYLIST_SHA256 = "18ac8386964e2f336105bb83f8f1be0af008b6b9ea83f679a2fd1ca582097abe"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def select_retry_blocks(raw, manifest):
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise ValueError("Invalid #497 initial manifest")
    if manifest.get("source_run_id") != SOURCE_RUN_ID:
        raise ValueError("Unexpected original audit run")
    if manifest.get("source_report_file_sha256") != SOURCE_REPORT_SHA256:
        raise ValueError("Original report hash mismatch")
    if manifest.get("source_playlist_sha256") != SOURCE_PLAYLIST_SHA256:
        raise ValueError("Original source playlist hash mismatch")
    if manifest.get("source_artifact_id") != 14587983768:
        raise ValueError("Original audit artifact identity mismatch")
    if manifest.get("source_yedekler_count") != 1792 or manifest.get("current_yedekler_count") != 1792:
        raise ValueError("Expected 1,792 current YEDEKLER entries")
    if manifest.get("current_playlist_sha256") != digest(raw):
        raise ValueError("Canonical playlist changed since initial preview")
    if digest(raw) != INITIAL_CURRENT_PLAYLIST_SHA256:
        raise ValueError("Unexpected canonical playlist snapshot")
    if manifest.get("ordered_yedekler_blocks_identical") is not True:
        raise ValueError("Initial source identity/order was not accepted")
    if manifest.get("preview_only") is not True or manifest.get("new_scan_started") is not False:
        raise ValueError("Initial preview provenance invalid")
    if manifest.get("canonical_playlist_written") is not False:
        raise ValueError("Initial run unexpectedly wrote the canonical playlist")
    if manifest.get("counts") != {"verified": 1107, "uncertain": 685}:
        raise ValueError("Initial 1,107/685 classification mismatch")
    if manifest.get("failed_count") != 0 or manifest.get("failed_tail_start_1based") is not None:
        raise ValueError("Initial report must not mark any channel failed")
    selected = [b for b in parse(raw)[1] if category(b.splitlines()[0]) == "YEDEKLER"]
    if len(selected) != 1792:
        raise ValueError("Expected exactly 1,792 YEDEKLER records")
    by_id = {}
    for pos, block in enumerate(selected, 1):
        channel_id = digest(block.encode("utf-8"))
        url = block.splitlines()[-1].strip()
        by_id[channel_id] = (pos, block, digest(url.encode("utf-8")))
    queue = manifest.get("retry_queue")
    if not isinstance(queue, list) or len(queue) != 685:
        raise ValueError("Expected exactly 685 uncertain retry records")
    chosen = []
    seen = set()
    last_pos = 0
    for item in queue:
        if not isinstance(item, dict) or item.get("status") != "uncertain":
            raise ValueError("Retry queue contains a non-uncertain record")
        if item.get("run_id") != SOURCE_RUN_ID:
            raise ValueError("Retry item source run mismatch")
        channel_id = item.get("channel_sha256")
        if channel_id in seen or channel_id not in by_id:
            raise ValueError("Duplicate or unmatched retry channel identity")
        pos, block, url_hash = by_id[channel_id]
        if item.get("url_sha256") != url_hash:
            raise ValueError("Retry queue URL identity mismatch")
        if pos <= last_pos:
            raise ValueError("Retry queue is not in canonical playlist order")
        last_pos = pos
        seen.add(channel_id)
        chosen.append((pos, block))
    if len(chosen) != 685:
        raise ValueError("Incomplete uncertain retry selection")
    return chosen

def audit_one(item):
    index, block = item
    url = block.splitlines()[-1].strip()
    first = probe(url, timeout=TIMEOUT)
    outcome = first
    attempts = 1
    if first.get("status") == "AV_STREAMS_PRESENT":
        decoded = verify_decoded_av(url, timeout=TIMEOUT)
        outcome = {**first, **decoded}
        outcome["status"] = "AV_VERIFIED" if decoded.get("decoded_av_verified") else decoded.get("decode_status", "DECODE_FAILED")
    if outcome.get("status") != "AV_VERIFIED":
        attempts = 2
        second = probe(url, timeout=TIMEOUT)
        if second.get("status") == "AV_STREAMS_PRESENT":
            decoded = verify_decoded_av(url, timeout=TIMEOUT)
            second = {**second, **decoded}
            second["status"] = "AV_VERIFIED" if decoded.get("decoded_av_verified") else decoded.get("decode_status", "DECODE_FAILED")
        outcome = second
    canonical = json.dumps(outcome, sort_keys=True, separators=(",", ":")).encode()
    deterministic = outcome.get("status") in ("NO_MEDIA", "NO_DECODED_FRAME")
    status = "verified" if outcome.get("status") == "AV_VERIFIED" else (
        "failed" if deterministic and attempts >= 2 else "uncertain")
    return {
        "ordinal": index,
        "channel_sha256": digest(block.encode("utf-8")),
        "url_sha256": digest(url.encode("utf-8")),
        "run_id": int(os.environ["GITHUB_RUN_ID"]),
        "evidence_sha256": digest(canonical),
        "attempts": attempts,
        "repeatable_av_failure": status == "failed",
        "status": status,
        "probe_status": outcome.get("status", "UNKNOWN"),
        "decode_status": outcome.get("decode_status", "NOT_RUN"),
        "evidence_level": outcome.get("evidence_level", "ffprobe_ffmpeg"),
        "decoded_av_verified": bool(outcome.get("decoded_av_verified")),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retry-manifest", type=Path, required=True)
    parser.add_argument("--playlist", type=Path, default=PLAYLIST)
    parser.add_argument("--output", type=Path, default=Path("retry-report.json"))
    args = parser.parse_args()
    if args.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
        raise SystemExit("Only the canonical main playlist is supported")
    if args.output.exists():
        raise SystemExit("Refusing to overwrite retry report")
    manifest_bytes = args.retry_manifest.read_bytes()
    if digest(manifest_bytes) != INITIAL_MANIFEST_SHA256:
        raise SystemExit("Initial retry manifest SHA-256 mismatch")
    manifest = json.loads(manifest_bytes)
    raw = args.playlist.read_bytes()
    chosen = select_retry_blocks(raw, manifest)
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        entries = list(pool.map(audit_one, chosen))
    counts = dict(Counter(item["status"] for item in entries))
    report = {
        "schema": 1,
        "playlist_sha256": digest(raw),
        "source_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "source_commit": os.environ["GITHUB_SHA"],
        "entries": entries,
        "counts": counts,
        "read_only": True,
        "retry_only": True,
        "retry_scanned_count": len(entries),
        "full_inventory_count": 1792,
        "retry_source_manifest_sha256": digest(manifest_bytes),
        "retry_source_manifest_artifact_id": INITIAL_MANIFEST_ARTIFACT_ID,
        "retry_source_manifest_run_id": INITIAL_MANIFEST_RUN_ID,
    }
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": report["source_run_id"], "retry_only": True,
                      "scanned": len(entries), "counts": counts,
                      "playlist_sha256": report["playlist_sha256"]}))

if __name__ == "__main__":
    main()

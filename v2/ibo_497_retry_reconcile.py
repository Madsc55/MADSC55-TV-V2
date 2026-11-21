#!/usr/bin/env python3
"""Combine original verified evidence with the targeted 685 retry and emit a read-only preview."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from ibo_single_playlist_transfer import parse, category
from ibo_test_result_reconcile import digest, reconcile

SOURCE_RUN_ID = 44640007709
SOURCE_REPORT_CANONICAL_SHA256 = "b48bd57ba03a7e4ee4ed3f65355572e267db87b4d48c6d4fb390b8484dc55c"
INITIAL_MANIFEST_SHA256 = "b001bf48f07437e9ae67ed9f73b12ea9cfcab653523973435cf3b1cee3c31fcc"

def build_full_report(raw, initial_manifest, initial_manifest_bytes, retry_report):
    if digest(initial_manifest_bytes) != INITIAL_MANIFEST_SHA256:
        raise ValueError("Initial manifest SHA-256 mismatch")
    if initial_manifest.get("source_run_id") != SOURCE_RUN_ID:
        raise ValueError("Initial evidence run mismatch")
    if initial_manifest.get("current_playlist_sha256") != digest(raw):
        raise ValueError("Playlist changed after the initial evidence preview")
    if initial_manifest.get("counts") != {"verified": 1107, "uncertain": 685}:
        raise ValueError("Initial evidence counts mismatch")
    if initial_manifest.get("source_report_canonical_sha256") != SOURCE_REPORT_CANONICAL_SHA256:
        raise ValueError("Initial report evidence digest mismatch")
    if retry_report.get("schema") != 1 or retry_report.get("retry_only") is not True:
        raise ValueError("Retry report schema/mode mismatch")
    if retry_report.get("playlist_sha256") != digest(raw):
        raise ValueError("Retry report playlist SHA mismatch")
    if retry_report.get("retry_source_manifest_sha256") != digest(initial_manifest_bytes):
        raise ValueError("Retry report was not generated from the accepted initial manifest")
    if retry_report.get("retry_source_manifest_artifact_id") != 14681083208:
        raise ValueError("Retry source artifact identity mismatch")
    if retry_report.get("retry_scanned_count") != 685 or retry_report.get("full_inventory_count") != 1792:
        raise ValueError("Retry report must contain exactly the 685 uncertain entries")
    retry_entries = retry_report.get("entries")
    if not isinstance(retry_entries, list) or len(retry_entries) != 685:
        raise ValueError("Retry report is incomplete")
    selected = [b for b in parse(raw)[1] if category(b.splitlines()[0]) == "YEDEKLER"]
    if len(selected) != 1792:
        raise ValueError("Expected 1,792 YEDEKLER records")
    ids = [digest(block.encode("utf-8")) for block in selected]
    if len(set(ids)) != 1792:
        raise ValueError("Duplicate immutable channel identities")
    queue = initial_manifest.get("retry_queue")
    if not isinstance(queue, list) or len(queue) != 685:
        raise ValueError("Initial retry queue is incomplete")
    uncertain = {x["channel_sha256"]: x for x in queue}
    if set(uncertain) - set(ids):
        raise ValueError("Initial retry queue contains unmatched channels")
    new = {}
    for item in retry_entries:
        if not isinstance(item, dict):
            raise ValueError("Malformed retry result")
        key = item.get("channel_sha256")
        if key not in uncertain or key in new:
            raise ValueError("Retry result is duplicate or outside the initial uncertain queue")
        block = selected[ids.index(key)]
        url_hash = digest(block.splitlines()[-1].strip().encode("utf-8"))
        if item.get("url_sha256") != url_hash:
            raise ValueError("Retry result URL hash mismatch")
        if item.get("run_id") != retry_report.get("source_run_id"):
            raise ValueError("Retry result run ID mismatch")
        if not isinstance(item.get("evidence_sha256"), str) or len(item["evidence_sha256"]) != 64:
            raise ValueError("Retry evidence hash missing")
        if item.get("status") not in ("verified", "uncertain", "failed"):
            raise ValueError("Unknown retry status")
        if not isinstance(item.get("attempts"), int) or item["attempts"] < 1:
            raise ValueError("Invalid retry attempt count")
        if item.get("status") == "failed" and not (
            item.get("repeatable_av_failure") is True and item["attempts"] >= 2
        ):
            raise ValueError("Failed status lacks repeatable AV failure evidence")
        new[key] = item
    if set(new) != set(uncertain):
        raise ValueError("Retry report does not cover the exact uncertain queue")
    entries = []
    for block, key in zip(selected, ids):
        if key in new:
            entries.append(new[key])
        else:
            entries.append({
                "channel_sha256": key,
                "url_sha256": digest(block.splitlines()[-1].strip().encode("utf-8")),
                "run_id": SOURCE_RUN_ID,
                "evidence_sha256": SOURCE_REPORT_CANONICAL_SHA256,
                "attempts": 1,
                "repeatable_av_failure": False,
                "status": "verified",
                "reason": "original_decoded_av_verified",
            })
    full = {"schema": 1, "playlist_sha256": digest(raw), "entries": entries}
    canonical = json.dumps(full, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return full, digest(canonical)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist", type=Path, default=Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"))
    parser.add_argument("--initial-manifest", type=Path, required=True)
    parser.add_argument("--retry-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
        raise SystemExit("Only canonical main playlist is supported")
    if args.output_dir.exists():
        raise SystemExit("Refusing to overwrite preview output")
    raw = args.playlist.read_bytes()
    initial_bytes = args.initial_manifest.read_bytes()
    initial = json.loads(initial_bytes)
    retry = json.loads(args.retry_report.read_text(encoding="utf-8"))
    full, full_sha = build_full_report(raw, initial, initial_bytes, retry)
    preview, manifest = reconcile(raw, full, digest(raw), full_sha)
    if len([b for b in parse(preview)[1] if category(b.splitlines()[0]) == "YEDEKLER"]) != 1792:
        raise ValueError("YEDEKLER count changed")
    original_other = [b for b in parse(raw)[1] if category(b.splitlines()[0]) != "YEDEKLER"]
    preview_other = [b for b in parse(preview)[1] if category(b.splitlines()[0]) != "YEDEKLER"]
    if original_other != preview_other or parse(raw)[0] != parse(preview)[0]:
        raise ValueError("Non-YEDEKLER records or playlist header changed")
    manifest.update({
        "initial_source_run_id": SOURCE_RUN_ID,
        "initial_source_report_canonical_sha256": SOURCE_REPORT_CANONICAL_SHA256,
        "initial_manifest_sha256": digest(initial_bytes),
        "retry_run_id": retry.get("source_run_id"),
        "retry_report_sha256": digest(args.retry_report.read_bytes()),
        "retry_source_manifest_artifact_id": 14681083208,
        "preview_only": True,
        "new_scan_started": False,
        "canonical_playlist_written": False,
        "non_yedekler_unchanged": True,
    })
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "preview.m3u8").write_bytes(preview)
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "retry-report.json").write_bytes(args.retry_report.read_bytes())
    print(json.dumps({"preview_only": True, "counts": manifest["counts"],
                      "failed_count": manifest["failed_count"],
                      "retry_queue_count": len(manifest["retry_queue"]),
                      "playlist_changed": preview != raw}))

if __name__ == "__main__":
    main()

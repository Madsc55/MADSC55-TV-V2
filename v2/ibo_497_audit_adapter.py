#!/usr/bin/env python3
"""#497: adapt an EXISTING read-only YEDEKLER AV audit, without probing streams.

Only accepts a complete, playlist-SHA-bound 1792-result report. Never changes
the canonical playlist; output is an offline reconciliation preview and queue.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from ibo_single_playlist_transfer import category, parse
from ibo_test_result_reconcile import digest, reconcile


def convert(raw, audit, run_id):
    if not isinstance(run_id, int) or run_id < 1:
        raise ValueError("A positive source Actions run ID is required")
    if audit.get("schema_version") != 1 or audit.get("category") != "YEDEKLER":
        raise ValueError("Unexpected source audit schema/category")
    if audit.get("playlist_sha256") != digest(raw):
        raise ValueError("Source playlist SHA mismatch; refusing positional guesses")
    selected = [b for b in parse(raw)[1]
                if category(b.split("\n", 1)[0]) == "YEDEKLER"]
    results = audit.get("results")
    if len(selected) != 1792 or audit.get("total") != 1792:
        raise ValueError("Expected exactly 1792 YEDEKLER channels")
    if not isinstance(results, list) or len(results) != len(selected):
        raise ValueError("Incomplete audit results")
    source_counts = audit.get("counts")
    if source_counts != {"WORKING": 1107, "RECHECK_REQUIRED": 685}:
        raise ValueError("Actual audit counts do not match 1107/685")
    report_hash = digest(json.dumps(audit, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8"))
    entries = []
    for position, (block, item) in enumerate(zip(selected, results), 1):
        if not isinstance(item, dict) or item.get("position") != position:
            raise ValueError("Invalid position or reordered audit")
        url = block.splitlines()[-1].strip()
        if item.get("url_sha256") != digest(url.encode("utf-8")):
            raise ValueError("URL mismatch at position %d" % position)
        name = block.splitlines()[0].rsplit(",", 1)[-1].strip()
        if item.get("name") != name:
            raise ValueError("Channel name mismatch at position %d" % position)
        working = item.get("classification") == "WORKING"
        uncertain = item.get("classification") == "RECHECK_REQUIRED"
        if not (working or uncertain):
            raise ValueError("Unknown audit classification")
        if working and (item.get("status") != "AV_VERIFIED" or
                        item.get("decoded_av_verified") is not True):
            raise ValueError("Unproven working status")
        if uncertain and (item.get("status") == "AV_VERIFIED" or
                          item.get("decoded_av_verified") is True):
            raise ValueError("Conflicting uncertain status")
        entries.append({
            "channel_sha256": digest(block.encode("utf-8")),
            "url_sha256": digest(url.encode("utf-8")),
            "run_id": run_id,
            "evidence_sha256": report_hash,
            "attempts": 1,
            "status": "verified" if working else "uncertain",
            "reason": "decoded_av_verified" if working else "recheck_required",
            "source_timestamp_utc": audit.get("timestamp_utc"),
        })
    actual_counts = Counter(item["classification"] for item in results)
    if dict(actual_counts) != source_counts:
        raise ValueError("Reported counts disagree with individual channel classifications")
    report = {"schema": 1, "playlist_sha256": digest(raw), "entries": entries}
    return report, report_hash


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--playlist", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    p.add_argument("--run-id", type=int, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    if a.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
        p.error("Only canonical playlist supported")
    if a.output_dir.exists():
        p.error("Refusing to overwrite output")
    raw = a.playlist.read_bytes()
    audit = json.loads(a.audit.read_text(encoding="utf-8"))
    report, source_hash = convert(raw, audit, a.run_id)
    canonical = json.dumps(report, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    preview, manifest = reconcile(raw, report, digest(raw), digest(canonical))
    if preview != raw or manifest["counts"] != {"verified": 1107, "uncertain": 685}:
        raise ValueError("Unexpected playlist change or classification totals")
    manifest.update({"source_run_id": a.run_id, "source_audit_sha256": source_hash,
                     "preview_only": True, "new_scan_started": False})
    a.output_dir.mkdir(parents=True, exist_ok=False)
    (a.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (a.output_dir / "preview.m3u8").write_bytes(preview)
    print(json.dumps({"counts": manifest["counts"], "preview_only": True}))


if __name__ == "__main__":
    main()

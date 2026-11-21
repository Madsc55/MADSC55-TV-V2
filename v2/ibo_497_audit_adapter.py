#!/usr/bin/env python3
"""Adapt the real #495 read-only AV report to #497; never probes streams."""
import argparse
import json
from collections import Counter
from pathlib import Path

from ibo_single_playlist_transfer import category, parse
from ibo_test_result_reconcile import digest, reconcile


def convert(raw, audit, run_id):
    if not isinstance(audit, dict) or audit.get("schema") != 1 or audit.get("read_only") is not True:
        raise ValueError("Unexpected #495 report schema or read_only marker")
    if not isinstance(run_id, int) or run_id < 1 or audit.get("source_run_id") != run_id:
        raise ValueError("Source Actions run ID mismatch")
    if audit.get("playlist_sha256") != digest(raw):
        raise ValueError("Source playlist SHA mismatch")
    selected = [b for b in parse(raw)[1]
                if category(b.split("\\n", 1)[0]) == "YEDEKLER"]
    if len(selected) != 1792:
        raise ValueError("Expected exactly 1792 YEDEKLER channels")
    source_entries = audit.get("entries")
    if not isinstance(source_entries, list) or len(source_entries) != len(selected):
        raise ValueError("Incomplete source entries")
    counts = Counter()
    report_hash = digest(json.dumps(audit, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8"))
    entries = []
    seen = set()
    for ordinal, (block, item) in enumerate(zip(selected, source_entries), 1):
        if not isinstance(item, dict) or item.get("ordinal") != ordinal:
            raise ValueError("Invalid or reordered source ordinal")
        channel_hash = digest(block.encode("utf-8"))
        url = block.splitlines()[-1].strip()
        url_hash = digest(url.encode("utf-8"))
        if item.get("channel_sha256") != channel_hash or item.get("url_sha256") != url_hash:
            raise ValueError("Immutable channel/URL identity mismatch at ordinal %d" % ordinal)
        if item.get("run_id") != run_id or item.get("evidence_sha256") is None:
            raise ValueError("Missing or inconsistent per-entry provenance")
        if channel_hash in seen:
            raise ValueError("Duplicate immutable channel identity")
        seen.add(channel_hash)
        status = item.get("status")
        if status == "verified":
            if item.get("decoded_av_verified") is not True or item.get("decode_status") != "DECODED_AV":
                raise ValueError("Unproven AV_VERIFIED result")
            mapped = "verified"
        elif status == "uncertain":
            if item.get("decoded_av_verified") is True:
                raise ValueError("Conflicting uncertain result")
            mapped = "uncertain"
        else:
            # Do not silently turn repeatable failures into an uncertain retry.
            raise ValueError("Source status is not verified/uncertain: %r" % status)
        counts[mapped] += 1
        entries.append({
            "channel_sha256": channel_hash,
            "url_sha256": url_hash,
            "run_id": run_id,
            "evidence_sha256": item["evidence_sha256"],
            "attempts": item.get("attempts"),
            "status": mapped,
            "reason": "decoded_av_verified" if mapped == "verified" else "source_audit_uncertain",
            "source_ordinal": ordinal,
        })
    if dict(counts) != {"verified": 1107, "uncertain": 685}:
        raise ValueError("Source counts are not the required 1107 verified / 685 uncertain")
    declared = audit.get("counts")
    if declared != dict(counts):
        raise ValueError("Declared source counts disagree with entries")
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
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    (a.output_dir / "preview.m3u8").write_bytes(preview)
    print(json.dumps({"counts": manifest["counts"], "preview_only": True}))


if __name__ == "__main__":
    main()

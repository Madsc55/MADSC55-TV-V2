#!/usr/bin/env python3
"""#497: fail-closed, offline evidence reconciliation; never launches a new scan."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from ibo_single_playlist_transfer import parse, category, sha

def digest(data):
    return hashlib.sha256(data).hexdigest()

def identity(block):
    lines = block.splitlines()
    url = lines[-1].strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("Non-HTTP stream URL")
    return digest(url.encode())

def reconcile(playlist_bytes, report, expected_playlist_sha, expected_report_sha):
    if sha(playlist_bytes) != expected_playlist_sha:
        raise ValueError("Playlist SHA mismatch")
    canonical = json.dumps(report, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    if digest(canonical) != expected_report_sha:
        raise ValueError("Report SHA mismatch")
    if report.get("schema") != 1 or report.get("playlist_sha256") != expected_playlist_sha:
        raise ValueError("Report schema or source mismatch")
    prefix, blocks = parse(playlist_bytes)
    selected = [b for b in blocks if category(b.split("\n", 1)[0]) == "YEDEKLER"]
    entries = report.get("entries")
    if not isinstance(entries, list) or len(entries) != len(selected):
        raise ValueError("Missing or extra evidence")
    # Repeated stream URLs cannot be disambiguated by URL alone: require
    # immutable EXTINF+URL identity, and quarantine any collisions.
    ids = [digest(b.encode()) for b in selected]
    if len(set(ids)) != len(ids):
        raise ValueError("Ambiguous duplicate channel identity")
    lookup = {item: i for i, item in enumerate(ids)}
    seen, decisions = set(), {}
    for item in entries:
        if not isinstance(item, dict) or item.get("channel_sha256") not in lookup:
            raise ValueError("Unmatched channel identity")
        key = item["channel_sha256"]
        if key in seen:
            raise ValueError("Duplicate report entry")
        seen.add(key)
        if item.get("url_sha256") != identity(selected[lookup[key]]):
            raise ValueError("URL hash mismatch")
        if not isinstance(item.get("run_id"), int) or not item.get("evidence_sha256"):
            raise ValueError("Missing evidence provenance")
        if not isinstance(item.get("attempts"), int) or item["attempts"] < 1:
            raise ValueError("Invalid attempts")
        status = item.get("status")
        if status not in ("verified", "uncertain", "failed"):
            raise ValueError("Unknown status")
        if status == "failed" and not (item.get("repeatable_av_failure") is True and item["attempts"] >= 2):
            status = "uncertain"
        decisions[key] = {**item, "status": status}
    if seen != set(ids):
        raise ValueError("Incomplete report")
    counts = Counter(x["status"] for x in decisions.values())
    queue = [decisions[key] for key in ids if decisions[key]["status"] == "uncertain"]
    # Preserve original order within every partition; only proven failures go last.
    good = [b for b, key in zip(selected, ids) if decisions[key]["status"] != "failed"]
    bad = [b for b, key in zip(selected, ids) if decisions[key]["status"] == "failed"]
    it = iter(good + bad)
    updated = [next(it) if category(b.split("\n", 1)[0]) == "YEDEKLER" else b for b in blocks]
    result = (prefix + "".join(updated)).encode()
    if Counter(updated) != Counter(blocks):
        raise ValueError("Playlist multiset changed")
    if len(selected) != counts["verified"] + counts["uncertain"] + counts["failed"]:
        raise ValueError("Count mismatch")
    manifest = {"schema": 1, "source_sha256": sha(playlist_bytes),
                "result_sha256": sha(result), "counts": dict(counts),
                "failed_tail_start_1based": len(selected)-len(bad)+1 if bad else None,
                "failed_count": len(bad), "retry_queue": queue}
    return result, manifest

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--playlist", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--playlist-sha256", required=True)
    p.add_argument("--report-sha256", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists() or args.out.with_suffix(".json").exists():
        raise ValueError("Refusing overwrite")
    raw = args.playlist.read_bytes()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    result, manifest = reconcile(raw, report, args.playlist_sha256, args.report_sha256)
    # Preview only: main playlist publication requires separate security gate.
    args.out.write_bytes(result)
    args.out.with_suffix(".json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False)+"\n")
    print(json.dumps({"preview_only": True, "counts": manifest["counts"]}))

if __name__ == "__main__":
    main()

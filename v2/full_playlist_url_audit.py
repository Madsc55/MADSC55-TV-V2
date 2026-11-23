#!/usr/bin/env python3
"""Read-only full-playlist, SHA-bound, bounded network sampling.

All canonical records are indexed; every distinct HTTP(S) URL is sampled at
most once across non-overlapping fixed-size shards. No channel is removed,
retagged, marked working/broken, or published. No remote URL is persisted.
This reports MPEG-TS program/stream metadata, NOT decoded AV or broadcaster
identity. Network requests use shared_url_safe_probe's pinned public IP policy.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from discover import entries, ROOT
from shared_url_identity import normalized_url
from shared_url_safe_probe import bounded_get, inspect_url

PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
MAX_SHARDS = 36
SHARD_SIZE = 500
MAX_SAMPLE_BYTES = 192 * 1024
PROBE_WORKERS = 6
POLICY = "READ_ONLY_SHARED_URL_SAMPLE_V1_NO_DECODE_NO_MUTATIONS"


def safe_label(value):
    text = str(value or "").strip()
    if "://" in text or "\x00" in text or any(ord(c) < 32 for c in text):
        return "[redacted]"
    return text[:160]


def index_playlist(text):
    """Return exact record count and sorted unique URL index, with no data loss."""
    by_url = {}
    records = 0
    for rec in entries(text):
        records += 1
        raw_url = rec["url"]
        url = normalized_url(raw_url)
        # Preserve invalid URL records in the inventory; fail closed on probe.
        url = url if url is not None else raw_url
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        if digest not in by_url:
            by_url[digest] = {"url": url, "records": []}
        by_url[digest]["records"].append({
            "ordinal": records,
            "name": safe_label(rec.get("name")),
            "tvg_id": safe_label(rec.get("tvg_id")),
            "category": safe_label(rec.get("group")),
            "program_selector": rec.get("program_number"),
        })
    return records, sorted(by_url.items())


def probe_once(url):
    try:
        # Smaller than the detailed 101-URL investigation: this is a
        # fleet-wide lightweight metadata sampling, not a deep AV decode.
        return inspect_url(
            url,
            fetch=lambda target, size: bounded_get(
                target, limit=min(size, MAX_SAMPLE_BYTES), timeout=6))
    except Exception:
        # Do not emit exception details; they may contain signed stream URLs.
        return {
            "status": "UNEXPECTED_PROBE_ERROR", "sample_bytes": 0,
            "programs": [], "distinct_broadcasters_verified": False,
            "audio_video_decoded_verified": False,
        }


def write_json_atomic(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", prefix="audit-",
                            suffix=".json", dir=path.parent, delete=False) as tmp:
        os.chmod(tmp.name, 0o600)
        json.dump(payload, tmp, ensure_ascii=False, sort_keys=True)
        tmp.write("\n")
        name = tmp.name
    os.replace(name, path)


def batch(text, shard, probe=probe_once, checkpoint=None):
    if not 0 <= shard < MAX_SHARDS:
        raise ValueError("Invalid shard")
    records, ordered = index_playlist(text)
    if not ordered or len(ordered) > MAX_SHARDS * SHARD_SIZE:
        raise ValueError("Full inventory exceeds bounded scan coverage")
    selected = ordered[shard * SHARD_SIZE:(shard + 1) * SHARD_SIZE]
    result = {
        "schema": 1, "policy": POLICY,
        "playlist_records": records,
        "unique_url_count": len(ordered),
        "shard": shard,
        "shard_count": MAX_SHARDS,
        "shard_size": SHARD_SIZE,
        "expected_in_shard": len(selected),
        "playlist_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "results": [],
        "complete": False,
    }
    if checkpoint:
        write_json_atomic(checkpoint, result)

    def task(item):
        digest, value = item
        evidence = probe(value["url"])
        return {
            "url_sha256": digest,
            "channel_records": value["records"],
            "evidence": evidence,
            "safe_to_delete_or_merge": False,
            "broadcast_identity_verified": False,
        }

    with ThreadPoolExecutor(max_workers=PROBE_WORKERS) as pool:
        futures = [pool.submit(task, item) for item in selected]
        for future in as_completed(futures):
            result["results"].append(future.result())
            if checkpoint and len(result["results"]) % 25 == 0:
                write_json_atomic(checkpoint, result)
    result["results"].sort(key=lambda x: x["url_sha256"])
    result["complete"] = len(result["results"]) == len(selected)
    result["status_counts"] = dict(sorted(
        Counter(row["evidence"]["status"] for row in result["results"]).items()))
    if checkpoint:
        write_json_atomic(checkpoint, result)
    return result


def consolidate(text, reports):
    """Fail closed on missing, stale, duplicate or inconsistent shard results."""
    records, ordered = index_playlist(text)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    expected = {digest for digest, _ in ordered}
    found = set()
    issues = []
    counts = Counter()
    seen_shards = set()
    for report in reports:
        if (not isinstance(report, dict)
                or report.get("policy") != POLICY
                or report.get("playlist_sha256") != sha
                or report.get("unique_url_count") != len(expected)
                or report.get("playlist_records") != records
                or report.get("shard_size") != SHARD_SIZE):
            issues.append("STALE_OR_INVALID_SHARD")
            continue
        shard = report.get("shard")
        if type(shard) is not int or not 0 <= shard < MAX_SHARDS or shard in seen_shards:
            issues.append("INVALID_OR_DUPLICATE_SHARD")
            continue
        seen_shards.add(shard)
        listed = report.get("results", [])
        expected_slice = {digest for digest, _ in
                          ordered[shard * SHARD_SIZE:(shard + 1) * SHARD_SIZE]}
        digests = [item.get("url_sha256") for item in listed]
        if (not report.get("complete") or len(digests) != len(expected_slice)
                or len(set(digests)) != len(digests)
                or set(digests) != expected_slice):
            issues.append("INCOMPLETE_SHARD")
            continue
        found.update(digests)
        for item in listed:
            counts[item["evidence"]["status"]] += 1
    if seen_shards != set(range(MAX_SHARDS)):
        issues.append("MISSING_SHARDS")
    if found != expected:
        issues.append("NOT_ALL_URLS_REVIEWED")
    return {
        "schema": 1, "policy": POLICY,
        "playlist_sha256": sha,
        "channel_records": records,
        "unique_url_count": len(expected),
        "unique_urls_reviewed": len(found),
        "missing_urls": len(expected - found),
        "shards_present": len(seen_shards),
        "shards_expected": MAX_SHARDS,
        "sample_status_counts": dict(sorted(counts.items())),
        "audio_video_decode_verified": False,
        "broadcast_identity_verified": False,
        "playlist_modified": False,
        "audit_complete": not issues,
        "issues": sorted(set(issues)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--merge-dir", type=Path)
    args = ap.parse_args()
    before = PLAYLIST.read_bytes()
    text = before.decode("utf-8-sig")
    if args.merge_dir:
        reports = []
        for file in sorted(args.merge_dir.rglob("shard-*.json")):
            reports.append(json.loads(file.read_text(encoding="utf-8")))
        summary = consolidate(text, reports)
        write_json_atomic(args.output, summary)
        print(json.dumps(summary, ensure_ascii=False))
        if not summary["audit_complete"]:
            raise SystemExit(2)
    else:
        if args.shard is None:
            ap.error("--shard is required without --merge-dir")
        result = batch(text, args.shard, checkpoint=args.output)
        print(json.dumps({
            "shard": result["shard"], "record_count": result["playlist_records"],
            "unique_url_count": result["unique_url_count"],
            "sampled": len(result["results"]),
            "complete": result["complete"],
            "status_counts": result["status_counts"],
        }, ensure_ascii=False))
    if PLAYLIST.read_bytes() != before:
        raise SystemExit("Canonical playlist changed during read-only audit")


if __name__ == "__main__":
    main()

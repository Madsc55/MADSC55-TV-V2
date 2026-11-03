#!/usr/bin/env python3
"""Verify the real #60->#72 historical loss set, without media scans or URL disclosure.

Input: original GitHub Actions playback aggregates and #60 anonymous M3U
candidate metadata. Output: hash-only recovered identities and public counts.
No URL reconstruction is possible from SHA256 identifiers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from historical_inventory_guard import classify

HASH = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "real-stage3-historical-hash-only-v1"


def _index_aggregate(document, label):
    if not isinstance(document, dict) or document.get("coverage_complete") is not True:
        raise ValueError(label + ": playback coverage incomplete")
    rows = document.get("channel_results")
    if not isinstance(rows, list) or type(document.get("unique_tested")) is not int or len(rows) != document["unique_tested"]:
        raise ValueError(label + ": inconsistent tested count")
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(label + ": non-object playback entry")
        key = row.get("url_sha256")
        if not isinstance(key, str) or not HASH.fullmatch(key) or key in indexed:
            raise ValueError(label + ": missing/duplicate/invalid stream hash")
        indexed[key] = row
    return indexed


def _index_candidates(document, expected):
    if (not isinstance(document, dict) or document.get("candidates_truncated") is not False
            or type(document.get("total_unique_candidates")) is not int
            or document["total_unique_candidates"] != expected):
        raise ValueError("#60 candidate inventory missing or truncated")
    rows = document.get("candidates")
    if not isinstance(rows, list) or len(rows) != expected:
        raise ValueError("#60 candidate rows are not complete")
    indexed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("#60 candidate record must be an object")
        key = row.get("url_sha256")
        if not isinstance(key, str) or not HASH.fullmatch(key) or key in indexed:
            raise ValueError("#60 candidates include a duplicate/invalid hash")
        # This is a *public anonymous report*; reject any unexpected clear URLs.
        if "url" in row:
            raise ValueError("#60 public candidates unexpectedly contain a clear stream URL")
        indexed[key] = row
    return indexed


def recover(old_report, new_report, original_candidates, expected_missing=4955):
    """Produce full historical hash-only evidence with no fabricated URL."""
    before = _index_aggregate(old_report, "#60")
    after = _index_aggregate(new_report, "#72")
    metadata = _index_candidates(original_candidates, len(before))
    if set(metadata) != set(before):
        raise ValueError("#60 candidate/playback stream identities differ")

    old_only = set(before) - set(after)
    missed = sorted(key for key in old_only
                    if before[key].get("playback") == "VIDEO_DECODED")
    if expected_missing is not None and len(missed) != expected_missing:
        raise ValueError("Actual missing historical decoded count differs from baseline")

    records = []
    region_counts = {"TR": 0, "AZ": 0, "UNKNOWN": 0}
    evidence_counts = {}
    for key in missed:
        item = metadata[key]
        region = classify(item)
        region_counts[region["region_candidate"]] += 1
        label = region["classification_evidence"]
        evidence_counts[label] = evidence_counts.get(label, 0) + 1
        records.append({
            "url_sha256": key,
            "source": str(before[key].get("source") or ""),
            "region_candidate": region["region_candidate"],
            "classification_evidence": label,
            "playback_at_run60": "VIDEO_DECODED",
            "historical_not_reverified": True,
            "spoken_language_verified": False,
            "device_verified": False,
        })
    if len(records) != len({row["url_sha256"] for row in records}):
        raise ValueError("Deduplicated history identities are inconsistent")
    if any(x["url_sha256"] in after for x in records):
        raise ValueError("Current archive overlap mistakenly marked as missing")

    summary = {
        "schema": 1, "policy": "REAL_HASH_ONLY_HISTORY_NO_STREAM_URLS_NO_AUTOPUBLISH",
        "source_run_old": 40743765437, "source_run_new": 40948768782,
        "old_coverage_complete": True, "new_coverage_complete": True,
        "old_unique_tested": len(before), "new_unique_tested": len(after),
        "old_video_decoded": sum(row.get("playback") == "VIDEO_DECODED"
                                 for row in before.values()),
        "old_only_identities": len(old_only),
        "previously_decoded_not_in_new": len(missed),
        "hash_only_records_preserved": len(records),
        "duplicate_hashes_in_preserved_view": 0,
        "region_candidates": region_counts,
        "classification_evidence_counts": evidence_counts,
        "hash_only_inventory_sha256": hashlib.sha256("".join(missed).encode("ascii")).hexdigest(),
        "real_stream_url_records_recovered": 0,
        "spoken_language_verified": False, "device_verified": False,
        "main_playlist_modified": False,
        "notes": "Original #60 decoded stream hash identities; missing from #72. "
                 "Metadata region hints are not speech or present-day playback verification."
    }
    return records, summary


def write_outputs(records, summary, index_path, report_path):
    """Only anonymous historical hashes to files; no stream URLs/tokens."""
    index_path, report_path = Path(index_path), Path(report_path)
    if index_path.resolve() == report_path.resolve() or index_path.exists() or report_path.exists():
        raise ValueError("Refusing to overwrite or collide evidence files")
    if index_path.suffix != ".jsonl" or report_path.suffix != ".json":
        raise ValueError("Expected .jsonl hash-only index and .json summary")
    index_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("x", encoding="utf-8") as file:
        for row in records:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    report_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Compare actual #60 and #72 historical evidence; no scanning")
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--old-candidates", type=Path, required=True)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-missing", type=int, default=4955)
    args = parser.parse_args()
    source_paths = [x.resolve() for x in (args.old, args.new, args.old_candidates)]
    output_paths = [x.resolve() for x in (args.index, args.report)]
    if args.expected_missing <= 0 or len(set(source_paths + output_paths)) != 5:
        parser.error("Invalid expected count or overlapping paths")
    inputs = [json.loads(p.read_text(encoding="utf-8")) for p in
              (args.old, args.new, args.old_candidates)]
    records, summary = recover(*inputs, expected_missing=args.expected_missing)
    write_outputs(records, summary, args.index, args.report)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

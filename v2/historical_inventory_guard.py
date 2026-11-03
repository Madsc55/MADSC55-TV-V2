#!/usr/bin/env python3
"""Lossless, offline historical inventory reconciliation and AES-GCM preservation.

Preserve every historical record including failed/duplicate/hash-only evidence.
Only the *candidate view* is deduplicated by exact stream URL SHA256.
No private stream URLs are written to plaintext files, stdout or CI reports.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re

from encrypted_archive import _cipher, append, restore, MAX_RECORD_BYTES
from historical_url_recovery import read_records, validate_url

SHA256 = re.compile(r"^[0-9a-f]{64}$")
TR_HINT = re.compile(r"(?i)(?:trt(?:\s|[._-]|\d|$)|türk|turk(?:ish|ey|iye)?|türkiye)")
AZ_HINT = re.compile(r"(?i)(?:azer(?:i|baijan|baycan)?|azər|azərbaycan)")
TVG_TR = re.compile(r"(?i)(?:^|[._-])tr(?:$|[._-])")
TVG_AZ = re.compile(r"(?i)(?:^|[._-])az(?:$|[._-])")
SCHEMA = "historical-inventory-guard-v1"


def digest(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def identity(row):
    """Identity is a real URL hash or previously recorded 64-char SHA256 only."""
    url = row.get("url")
    if validate_url(url):
        return digest(url)
    stored = row.get("url_sha256")
    return stored.lower() if isinstance(stored, str) and SHA256.fullmatch(stored.lower()) else None


def classify(row):
    """Country/metadata *candidate* evidence, never verified spoken language."""
    # Preserve already-reviewed region *metadata* in hash-only historical records.
    # A hash has no URL and must never become an exportable stream address.
    if (not validate_url(row.get("url"))
            and isinstance(row.get("url_sha256"), str)
            and SHA256.fullmatch(row["url_sha256"].lower())
            and row.get("region_candidate") in ("TR", "AZ", "UNKNOWN")
            and row.get("classification_evidence") in ("SOURCE_GEO", "TVG_ID", "METADATA", "NONE", "CONFLICTING_TR_AZ_EVIDENCE")):
        return {"region_candidate": row["region_candidate"],
                "classification_evidence": row["classification_evidence"],
                "spoken_language_verified": False}
    fields = (row.get("scope"), row.get("country"), row.get("region"), row.get("country_code"))
    for value in fields:
        if not isinstance(value, str):
            continue
        scope = value.strip().casefold()
        if scope in ("az", "azerbaijan", "azerbaycan", "azərbaycan"):
            return {"region_candidate": "AZ", "classification_evidence": "SOURCE_GEO",
                    "spoken_language_verified": False}
        if scope in ("tr", "turkey", "turkiye", "türkiye"):
            return {"region_candidate": "TR", "classification_evidence": "SOURCE_GEO",
                    "spoken_language_verified": False}
    tvg = str(row.get("tvg_id") or "")
    if TVG_AZ.search(tvg):
        region, evidence = "AZ", "TVG_ID"
    elif TVG_TR.search(tvg):
        region, evidence = "TR", "TVG_ID"
    else:
        name_group = " ".join(str(row.get(k) or "") for k in ("name", "group"))
        if AZ_HINT.search(name_group):
            region, evidence = "AZ", "METADATA"
        elif TR_HINT.search(name_group):
            region, evidence = "TR", "METADATA"
        else:
            region, evidence = "UNKNOWN", "NONE"
    return {"region_candidate": region, "classification_evidence": evidence,
            "spoken_language_verified": False}


def source_ids(row):
    values = []
    supplied = row.get("source_ids", [])
    if isinstance(supplied, list):
        values.extend(x for x in supplied if isinstance(x, str) and x)
    source = row.get("source")
    if isinstance(source, str) and source:
        values.append(source)
    return list(dict.fromkeys(values))


def reconcile(historical_records, current_records=(), expected_historical_records=None):
    """Return (all preserved raw records, distinct URL candidate view, public counts).

    Never drop a historical input row, even when it is dead, unsafe, duplicated
    or contains only an anonymized hash. An unusable address is not exportable.
    """
    historical = list(historical_records)
    current = list(current_records)
    if expected_historical_records is not None and len(historical) != expected_historical_records:
        raise ValueError("Historical record count does not match required baseline")
    if not historical:
        raise ValueError("Missing historical inventory; cannot prove loss protection")
    for row in historical + current:
        if not isinstance(row, dict):
            raise ValueError("Inventory contains a non-object record")
    # Raw historical evidence is immutable in the protected snapshot.
    protected = [dict(row) for row in historical]
    indexed = {}
    all_ids, hashed_only, unknown = set(), set(), 0
    duplicate_historical = 0
    historical_with_url = set()
    for row in historical:
        key = identity(row)
        if key is None:
            unknown += 1
            continue
        all_ids.add(key)
        url = row.get("url")
        if not validate_url(url):
            hashed_only.add(key)
            continue
        historical_with_url.add(key)
        if key in indexed:
            duplicate_historical += 1
            item = indexed[key]
            if item["url"] != url:
                raise ValueError("Conflicting URL identity")
            item["source_ids"] = list(dict.fromkeys(item["source_ids"] + source_ids(row)))
            # Keep the original metadata; fill only absent attributes.
            for attr in ("name", "tvg_id", "logo", "group"):
                if not item.get(attr) and row.get(attr):
                    item[attr] = row[attr]
        else:
            item = dict(row)
            item["source_ids"] = source_ids(row)
            item["historical_not_reverified"] = True
            indexed[key] = item
    current_identity = set()
    current_invalid = 0
    current_duplicates = 0
    hash_evidence_linked = set()
    for row in current:
        url = row.get("url")
        if not validate_url(url):
            current_invalid += 1
            continue
        key = digest(url)
        if key in current_identity:
            current_duplicates += 1
        current_identity.add(key)
        if key in hashed_only:
            hash_evidence_linked.add(key)
        if key in indexed:
            item = indexed[key]
            if item["url"] != url:
                raise ValueError("Conflicting URL identity")
            item["source_ids"] = list(dict.fromkeys(item["source_ids"] + source_ids(row)))
            for attr in ("name", "tvg_id", "logo", "group", "scope", "country"):
                if not item.get(attr) and row.get(attr):
                    item[attr] = row[attr]
        else:
            item = dict(row)
            item["source_ids"] = source_ids(row)
            item["historical_not_reverified"] = key in all_ids
            indexed[key] = item
            # New real URL evidence supplements, never replaces historic rows.
            protected.append(dict(row))
    # A stream URL can be listed as TR in one historical source and AZ in
    # another. Preserve both raw records, but never silently assign the first
    # region to the deduplicated candidate when evidence conflicts.
    region_evidence = {}
    for row in historical + current:
        url = row.get("url")
        if not validate_url(url):
            continue
        key = digest(url)
        region = classify(row)["region_candidate"]
        if region in ("TR", "AZ"):
            region_evidence.setdefault(key, set()).add(region)
    conflicting_region_ids = {key for key, regions in region_evidence.items()
                              if len(regions) > 1}

    candidates = []
    for key, item in indexed.items():
        candidate = dict(item)
        candidate["url_sha256"] = key
        candidate.update(classify(candidate))
        if key in conflicting_region_ids:
            candidate.update(region_candidate="UNKNOWN",
                             classification_evidence="CONFLICTING_TR_AZ_EVIDENCE",
                             spoken_language_verified=False)
        candidate["device_verified"] = False
        # Existing flags cannot turn historical evidence into media proof.
        candidate["historical_not_reverified"] = key in all_ids
        candidates.append(candidate)
    unresolved = all_ids - current_identity
    summary = {
        "schema": 1, "policy": "LOSSLESS_HISTORICAL_EVIDENCE_NO_AUTOPUBLISH",
        "historical_records_expected": expected_historical_records,
        "historical_records_observed": len(historical),
        "historical_records_preserved": len(historical),
        "historical_tr_candidate_records": sum(classify(row)["region_candidate"] == "TR" for row in historical),
        "historical_az_candidate_records": sum(classify(row)["region_candidate"] == "AZ" for row in historical),
        "historical_unknown_region_records": sum(classify(row)["region_candidate"] == "UNKNOWN" for row in historical),
        "historical_unique_identities": len(all_ids),
        "historical_unique_real_urls": len(historical_with_url),
        "historical_duplicate_url_rows": duplicate_historical,
        "historical_hash_only_identities": len(hashed_only),
        "historical_unidentified_records_preserved": unknown,
        "historical_identities_present_in_current": len(all_ids & current_identity),
        "historical_identities_not_in_current": len(unresolved),
        "historical_hash_only_linked_to_real_urls": len(hash_evidence_linked),
        "current_distinct_real_urls": len(current_identity),
        "current_invalid_url_records": current_invalid,
        "current_duplicate_url_rows": current_duplicates,
        "unique_candidate_urls": len(candidates),
        "tr_candidates": sum(x["region_candidate"] == "TR" for x in candidates),
        "az_candidates": sum(x["region_candidate"] == "AZ" for x in candidates),
        "unknown_region_candidates": sum(x["region_candidate"] == "UNKNOWN" for x in candidates),
        "conflicting_tr_az_candidate_urls": len(conflicting_region_ids),
        "historical_identity_sha256": hashlib.sha256("".join(sorted(all_ids)).encode()).hexdigest(),
        "historical_preservation_verified": False,
        "real_streams_reverified": 0, "device_verified": False, "channel_playlist_modified": False,
    }
    return protected, candidates, summary


def _chunks(records, kind):
    batch, length = [], 0
    for record in records:
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(payload) > MAX_RECORD_BYTES // 2:
            raise ValueError("Inventory record too large")
        if batch and (length + len(payload) > MAX_RECORD_BYTES // 2 or len(batch) >= 100):
            yield {"kind": kind, "guard_schema": SCHEMA, "records": batch}
            batch, length = [], 0
        batch.append(record)
        length += len(payload)
    if batch:
        yield {"kind": kind, "guard_schema": SCHEMA, "records": batch}


def preserve_to_new_archive(path, protected, candidates):
    """Create a *new* encrypted archive; compare its full decrypt with inputs."""
    path = Path(path)
    if path.exists() or path.is_symlink() or path.suffix != ".enc":
        raise ValueError("Refusing to overwrite archive or write non-encrypted output")
    _cipher()
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    os.close(fd)
    expected = list(_chunks(protected, "raw_historical_and_new")) + list(_chunks(candidates, "deduplicated_view"))
    for block in expected:
        append(path, block)
    verified = restore(path) == expected
    if not verified:
        raise RuntimeError("Encrypted historical archive restore mismatch")
    return verified


def read_historical_csv(path):
    """Consume a genuine SHA256-only historical comparison CSV without URLs."""
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "url_sha256" not in reader.fieldnames:
            raise ValueError("Historical comparison CSV must contain url_sha256")
        for row in reader:
            yield dict(row)


def read_historical_aggregate(path):
    """Consume prior complete video-playback aggregate without inventing URLs."""
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = report.get("channel_results") if isinstance(report, dict) else None
    if (not isinstance(rows, list) or not report.get("coverage_complete")
            or report.get("unique_tested") != len(rows)):
        raise ValueError("Historical playback aggregate is incomplete")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Historical playback aggregate has invalid record")
        yield row


def main():
    parser = argparse.ArgumentParser(description="Offline historical loss guard, no stream requests")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--historical-jsonl", type=Path)
    source.add_argument("--historical-archive", type=Path)
    source.add_argument("--historical-csv", type=Path, help="Legacy hash-only recovery CSV")
    source.add_argument("--historical-aggregate", type=Path, help="Legacy complete playback JSON")
    parser.add_argument("--current-jsonl", type=Path)
    parser.add_argument("--out-archive", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-historical-records", type=int, default=4955)
    args = parser.parse_args()
    inputs = [x for x in (args.historical_jsonl, args.historical_archive, args.historical_csv,
                          args.historical_aggregate, args.current_jsonl) if x]
    outputs = (args.out_archive, args.report)
    if (args.expected_historical_records <= 0 or len({x.resolve(strict=False) for x in inputs + list(outputs)}) != len(inputs) + len(outputs)
            or any(x.exists() or x.is_symlink() for x in outputs)
            or args.report.suffix != ".json"):
        parser.error("Unsafe output/input collision or invalid expected history count")
    if args.historical_archive:
        historical = restore(args.historical_archive)
        if any(isinstance(x, dict) and x.get("guard_schema") == SCHEMA for x in historical):
            historical = [row for block in historical
                          for row in (block["records"] if block.get("kind") == "raw_historical_and_new"
                                      else [block] if "kind" not in block else [])]
    elif args.historical_csv:
        historical = list(read_historical_csv(args.historical_csv))
    elif args.historical_aggregate:
        historical = list(read_historical_aggregate(args.historical_aggregate))
    else:
        historical = list(read_records(args.historical_jsonl))
    current = list(read_records(args.current_jsonl)) if args.current_jsonl else []
    protected, indexed, report = reconcile(historical, current, args.expected_historical_records)
    report["historical_preservation_verified"] = preserve_to_new_archive(args.out_archive, protected, indexed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

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
import tempfile

from encrypted_archive import _cipher, append, restore, MAX_RECORD_BYTES
from historical_url_recovery import read_records, validate_url

SHA256 = re.compile(r"^[0-9a-f]{64}$")
TR_HINT = re.compile(r"(?i)(?:trt(?:\s|[._-]|\d|$)|türk|turk(?:ish|ey|iye)?|türkiye)")
AZ_HINT = re.compile(r"(?i)(?:azer(?:i|baijan|baycan)?|azər|azərbaycan)")
TVG_TR = re.compile(r"(?i)(?:^|[._-])tr(?:$|[._-])")
TVG_AZ = re.compile(r"(?i)(?:^|[._-])az(?:$|[._-])")
SCHEMA = "historical-inventory-guard-v1"
SCHEMA_V2 = "historical-inventory-guard-v2"


def digest(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def identity(row):
    """Identity is a real URL hash or previously recorded 64-char SHA256 only."""
    url = row.get("url")
    if validate_url(url):
        key = digest(url)
        # A claimed SHA associated with a real URL must be an exact identity,
        # not a second, unrelated historical identity.
        if "url_sha256" in row:
            stored = row["url_sha256"]
            if not isinstance(stored, str) or not SHA256.fullmatch(stored.lower()) or stored.lower() != key:
                raise ValueError("Stream URL and claimed SHA256 identity disagree")
        return key
    stored = row.get("url_sha256")
    return stored.lower() if isinstance(stored, str) and SHA256.fullmatch(stored.lower()) else None


def _classify_preferred(row):
    """Original preferred evidence; never a spoken-language verification."""
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


def region_signals(row):
    """Collect independent TR/AZ hints; contradictory hints require review.

    A single field may itself contain both hints. Historical hash-only
    metadata is advisory, not evidence of a playable URL or spoken language.
    """
    signals = set()
    baseline = _classify_preferred(row)["region_candidate"]
    if baseline in ("TR", "AZ"):
        signals.add(baseline)
    for field in ("scope", "country", "region", "country_code"):
        value = row.get(field)
        if not isinstance(value, str):
            continue
        normalized = value.strip().casefold()
        if normalized in ("tr", "turkey", "turkiye", "türkiye"):
            signals.add("TR")
        if normalized in ("az", "azerbaijan", "azerbaycan", "azərbaycan"):
            signals.add("AZ")
    tvg = row.get("tvg_id")
    if isinstance(tvg, str):
        if TVG_TR.search(tvg):
            signals.add("TR")
        if TVG_AZ.search(tvg):
            signals.add("AZ")
    metadata = " ".join(row.get(k) for k in ("name", "group")
                        if isinstance(row.get(k), str))
    if TR_HINT.search(metadata):
        signals.add("TR")
    if AZ_HINT.search(metadata):
        signals.add("AZ")
    return signals


def classify(row):
    """Conservatively classify TR/AZ with all independent hints considered."""
    preferred = _classify_preferred(row)
    # Never undo an earlier review of conflicting historical evidence.
    if (row.get("region_candidate") == "UNKNOWN"
            and row.get("classification_evidence") == "CONFLICTING_TR_AZ_EVIDENCE"):
        return {"region_candidate": "UNKNOWN",
                "classification_evidence": "CONFLICTING_TR_AZ_EVIDENCE",
                "spoken_language_verified": False}
    if len(region_signals(row)) > 1:
        return {"region_candidate": "UNKNOWN",
                "classification_evidence": "CONFLICTING_TR_AZ_EVIDENCE",
                "spoken_language_verified": False}
    return preferred


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
        # Fail before creating any encrypted or public output on corrupt
        # URL/hash pairs, even when the record would otherwise be skipped.
        identity(row)
    # Preserve every original historical and incoming record in the encrypted
    # raw evidence. Even failed/unsafe/hash-only/duplicate incoming rows remain
    # auditable. Only the candidate *view* is deduplicated by valid URL.
    # The first N records are always the immutable historical baseline.
    protected = [dict(row) for row in historical + current]
    indexed = {}
    all_ids, hashed_only, unknown = set(), set(), 0
    duplicate_historical = 0
    historical_with_url = set()
    hash_only_sources = {}
    seen_historical_keys = set()
    duplicate_historical_identities = 0
    for row in historical:
        key = identity(row)
        if key is None:
            unknown += 1
            continue
        if key in seen_historical_keys:
            duplicate_historical_identities += 1
        seen_historical_keys.add(key)
        all_ids.add(key)
        url = row.get("url")
        if not validate_url(url):
            hashed_only.add(key)
            prior = hash_only_sources.setdefault(key, [])
            prior.extend(x for x in source_ids(row) if x not in prior)
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
    current_hash_only_sources = {}
    for row in current:
        url = row.get("url")
        if not validate_url(url):
            current_invalid += 1
            key = identity(row)
            if key is not None:
                prior = current_hash_only_sources.setdefault(key, [])
                prior.extend(x for x in source_ids(row) if x not in prior)
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
    # Link SHA-only source provenance to a *real, exact* URL identity when
    # available, whether its hash evidence came from #60 or a later backup.
    # All original hash-only evidence stays separately in protected.
    for key, old_sources in hash_only_sources.items():
        if key in indexed:
            item = indexed[key]
            item["source_ids"] = list(dict.fromkeys(old_sources + item["source_ids"]))
    for key, newer_sources in current_hash_only_sources.items():
        if key in indexed:
            item = indexed[key]
            item["source_ids"] = list(dict.fromkeys(item["source_ids"] + newer_sources))

    # Evaluate both real-URL and hash-only evidence for the SAME verified digest.
    # Otherwise a #60 TR hash and a newer AZ URL could be silently mislabelled.
    region_evidence, historical_conflicts = {}, set()
    for position, row in enumerate(historical + current):
        key = identity(row)
        if key is None or key not in indexed:
            continue
        region_evidence.setdefault(key, set()).update(region_signals(row))
        if (position < len(historical)
                and row.get("classification_evidence") == "CONFLICTING_TR_AZ_EVIDENCE"):
            historical_conflicts.add(key)
    conflicting_region_ids = {key for key, regions in region_evidence.items()
                              if len(regions) > 1} | historical_conflicts

    candidates = []
    for key, item in indexed.items():
        candidate = dict(item)
        candidate["url_sha256"] = key
        candidate.update(classify(candidate))
        if key in conflicting_region_ids:
            candidate.update(region_candidate="UNKNOWN",
                             classification_evidence="CONFLICTING_TR_AZ_EVIDENCE",
                             spoken_language_verified=False)
        elif (candidate["region_candidate"] == "UNKNOWN"
              and len(region_evidence.get(key, ())) == 1):
            # Historical metadata can be a regional candidate hint, never
            # evidence of current broadcast health or spoken language.
            candidate.update(region_candidate=next(iter(region_evidence[key])),
                             classification_evidence="HISTORICAL_REGION_EVIDENCE",
                             spoken_language_verified=False)
        # Discovery/deduplication is not a new FFmpeg probe. Keep all claimed
        # flags in encrypted raw evidence, but never promote the candidate view.
        candidate["av_verified"] = False
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
        "current_records_preserved": len(current),
        "current_invalid_records_preserved": current_invalid,
        "current_duplicate_url_rows_preserved": current_duplicates,
        "total_raw_records_preserved": len(protected),
        "historical_tr_candidate_records": sum(classify(row)["region_candidate"] == "TR" for row in historical),
        "historical_az_candidate_records": sum(classify(row)["region_candidate"] == "AZ" for row in historical),
        "historical_unknown_region_records": sum(classify(row)["region_candidate"] == "UNKNOWN" for row in historical),
        "historical_unique_identities": len(all_ids),
        "historical_unique_real_urls": len(historical_with_url),
        "historical_duplicate_url_rows": duplicate_historical,
        "historical_duplicate_identity_rows": duplicate_historical_identities,
        "historical_hash_only_identities": len(hashed_only),
        "historical_unidentified_records_preserved": unknown,
        "historical_identities_present_in_current": len(all_ids & current_identity),
        "historical_identities_not_in_current": len(unresolved),
        "historical_hash_only_linked_to_real_urls": len(hash_evidence_linked),
        "historical_hash_only_provenance_linked": sum(key in indexed for key in hash_only_sources),
        "current_distinct_real_urls": len(current_identity),
        "current_invalid_url_records": current_invalid,
        "current_duplicate_url_rows": current_duplicates,
        "unique_candidate_urls": len(candidates),
        "tr_candidates": sum(x["region_candidate"] == "TR" for x in candidates),
        "az_candidates": sum(x["region_candidate"] == "AZ" for x in candidates),
        "unknown_region_candidates": sum(x["region_candidate"] == "UNKNOWN" for x in candidates),
        "conflicting_tr_az_candidate_urls": len(conflicting_region_ids),
        "historical_rows_with_internal_region_conflict": sum(
            len(region_signals(row)) > 1 for row in historical),
        "historical_identity_sha256": hashlib.sha256("".join(sorted(all_ids)).encode()).hexdigest(),
        "historical_preservation_verified": False,
        "real_streams_reverified": 0, "device_verified": False, "channel_playlist_modified": False,
    }
    return protected, candidates, summary


def _chunks(records, kind, schema=SCHEMA_V2):
    batch, length = [], 0
    for record in records:
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(payload) > MAX_RECORD_BYTES // 2:
            raise ValueError("Inventory record too large")
        if batch and (length + len(payload) > MAX_RECORD_BYTES // 2 or len(batch) >= 100):
            yield {"kind": kind, "guard_schema": schema, "records": batch}
            batch, length = [], 0
        batch.append(record)
        length += len(payload)
    if batch:
        yield {"kind": kind, "guard_schema": schema, "records": batch}


def _archive_payload_sha256(blocks):
    """Stable digest over all original records, their order and source metadata."""
    data = json.dumps(blocks, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def preserve_to_new_archive(path, protected, candidates):
    """Create a complete authenticated archive, including a final manifest.

    AES-GCM authenticates each block but cannot independently detect deletion of
    a *whole* valid block. The final encrypted manifest binds count and digest
    of every preceding block; V1 archives remain readable for migration.
    """
    path = Path(path)
    if path.exists() or path.is_symlink() or path.suffix != ".enc":
        raise ValueError("Refusing to overwrite archive or write non-encrypted output")
    _cipher()
    protected, candidates = list(protected), list(candidates)
    payload = list(_chunks(protected, "raw_historical_and_new"))
    payload.extend(_chunks(candidates, "deduplicated_view"))
    if not payload:
        raise ValueError("Cannot create empty historical archive")
    manifest = {
        "kind": "archive_manifest",
        "guard_schema": SCHEMA_V2,
        "block_count": len(payload),
        "raw_record_count": len(protected),
        "candidate_record_count": len(candidates),
        "payload_sha256": _archive_payload_sha256(payload),
    }
    expected = payload + [manifest]
    path.parent.mkdir(parents=True, exist_ok=True)
    # Stage privately in the SAME directory. Never leave an incomplete .enc
    # at the requested final path when encryption, fsync, or restore fails.
    fd, staging_name = tempfile.mkstemp(prefix=".stage3-archive-", suffix=".enc",
                                         dir=path.parent)
    os.close(fd)
    staging = Path(staging_name)
    try:
        for block in expected:
            append(staging, block)
        recovered = restore(staging)
        verified = recovered == expected
        if verified:
            decoded_raw, decoded_view = _verify_archive_envelope(recovered)
            verified = decoded_raw == protected and decoded_view == candidates
        if not verified:
            raise RuntimeError("Encrypted historical archive restore mismatch")
        # Hard link publication is atomic and fails when a concurrent writer
        # created the final destination. os.replace would overwrite evidence.
        os.link(staging, path, follow_symlinks=False)
        return True
    finally:
        staging.unlink(missing_ok=True)


def _verify_archive_envelope(blocks):
    """Reject fully removed, reordered or swapped valid encrypted V2 blocks."""
    if not blocks:
        raise ValueError("Encrypted archive is empty")
    formats = [block.get("guard_schema") if isinstance(block, dict) else None
               for block in blocks]
    if SCHEMA_V2 not in formats:
        return None, None  # Historical V1 without a final manifest.
    if any(schema != SCHEMA_V2 for schema in formats):
        raise ValueError("Mixed historical archive schemas")
    manifest = blocks[-1]
    expected_keys = {"kind", "guard_schema", "block_count", "raw_record_count",
                     "candidate_record_count", "payload_sha256"}
    if set(manifest) != expected_keys or manifest.get("kind") != "archive_manifest":
        raise ValueError("V2 encrypted archive manifest missing")
    payload = blocks[:-1]
    if (type(manifest["block_count"]) is not int or
            manifest["block_count"] != len(payload)):
        raise ValueError("Encrypted archive block count differs from manifest")
    if manifest["payload_sha256"] != _archive_payload_sha256(payload):
        raise ValueError("Encrypted archive payload differs from manifest")
    raw, view, after_view = [], [], False
    for block in payload:
        if set(block) != {"kind", "guard_schema", "records"}:
            raise ValueError("Invalid encrypted archive block fields")
        records = block["records"]
        if not isinstance(records, list) or not records or not all(
                isinstance(record, dict) for record in records):
            raise ValueError("Invalid encrypted archive block records")
        if block["kind"] == "raw_historical_and_new":
            if after_view:
                raise ValueError("Historical evidence follows candidate view")
            raw.extend(records)
        elif block["kind"] == "deduplicated_view":
            after_view = True
            view.extend(records)
        else:
            raise ValueError("Unknown encrypted archive block kind")
    if (type(manifest["raw_record_count"]) is not int or
            type(manifest["candidate_record_count"]) is not int or
            len(raw) != manifest["raw_record_count"] or
            len(view) != manifest["candidate_record_count"]):
        raise ValueError("Encrypted archive record counts differ from manifest")
    return raw, view


def unpack_archive_snapshot(blocks, expected_historical_records):
    """Restore historic prefix and later URL evidence without losing either.

    V1 encrypted blocks use raw_historical_and_new for both groups. Since
    reconcile always writes all historical rows first, the required baseline
    count defines an unambiguous split. Fail closed on mixed or damaged blocks.
    """
    if not isinstance(blocks, list) or not blocks:
        raise ValueError("Missing encrypted archive records")
    wrapped = [isinstance(block, dict) and block.get("guard_schema") in
               (SCHEMA, SCHEMA_V2) for block in blocks]
    if not any(wrapped):
        if not all(isinstance(row, dict) and "kind" not in row for row in blocks):
            raise ValueError("Invalid legacy encrypted historical archive")
        if len(blocks) != expected_historical_records:
            raise ValueError("Legacy archive does not match historical baseline")
        return list(blocks), [], None
    if not all(wrapped):
        raise ValueError("Mixed or unrecognized encrypted archive formats")
    if any(block.get("guard_schema") == SCHEMA_V2 for block in blocks):
        raw, view = _verify_archive_envelope(blocks)
        if len(raw) < expected_historical_records:
            raise ValueError("Encrypted history shorter than baseline")
        return raw[:expected_historical_records], raw[expected_historical_records:], view
    raw, view, seen_view = [], [], False
    for block in blocks:
        if set(block) != {"kind", "guard_schema", "records"}:
            raise ValueError("Invalid encrypted archive block fields")
        rows = block["records"]
        if not isinstance(rows, list) or not rows or not all(isinstance(x, dict) for x in rows):
            raise ValueError("Invalid encrypted archive block records")
        if block["kind"] == "raw_historical_and_new":
            if seen_view:
                raise ValueError("Historical evidence follows candidate view")
            raw.extend(rows)
        elif block["kind"] == "deduplicated_view":
            seen_view = True
            view.extend(rows)
        else:
            raise ValueError("Unknown encrypted archive block kind")
    if len(raw) < expected_historical_records:
        raise ValueError("Encrypted history shorter than baseline")
    return raw[:expected_historical_records], raw[expected_historical_records:], view


def verify_historical_baseline(historical, baseline_records):
    """Require complete immutable historical records, not merely the same hashes.

    A modified region candidate, source, playback status or review flag is
    historical data corruption even when its SHA-256 URL identity is unchanged.
    Record ordering and JSON key order do not affect the check.
    """
    historical, baseline_records = list(historical), list(baseline_records)
    if not all(isinstance(row, dict) for row in historical + baseline_records):
        raise ValueError("Historical baseline contains a non-object record")
    expected = [identity(row) for row in baseline_records]
    observed = [identity(row) for row in historical]
    if (not expected or None in expected or None in observed or
            len(expected) != len(set(expected)) or
            len(expected) != len(observed) or
            set(expected) != set(observed)):
        raise ValueError("Historical identities do not match immutable baseline")
    reference = {identity(row): row for row in baseline_records}
    if any(row != reference[identity(row)] for row in historical):
        raise ValueError("Historical record metadata differs from immutable baseline")
    return hashlib.sha256("".join(sorted(expected)).encode("ascii")).hexdigest()


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
    parser.add_argument("--baseline-index", type=Path,
                        help="Require exact SHA256 identity set of immutable historical index")
    parser.add_argument("--out-archive", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-historical-records", type=int, default=4955)
    args = parser.parse_args()
    inputs = [x for x in (args.historical_jsonl, args.historical_archive, args.historical_csv,
                          args.historical_aggregate, args.current_jsonl, args.baseline_index) if x]
    outputs = (args.out_archive, args.report)
    if (args.expected_historical_records <= 0 or len({x.resolve(strict=False) for x in inputs + list(outputs)}) != len(inputs) + len(outputs)
            or any(x.exists() or x.is_symlink() for x in outputs)
            or args.report.suffix != ".json"):
        parser.error("Unsafe output/input collision or invalid expected history count")
    earlier_current, archived_view = [], None
    if args.historical_archive:
        historical, earlier_current, archived_view = unpack_archive_snapshot(
            restore(args.historical_archive), args.expected_historical_records)
    elif args.historical_csv:
        historical = list(read_historical_csv(args.historical_csv))
    elif args.historical_aggregate:
        historical = list(read_historical_aggregate(args.historical_aggregate))
    else:
        historical = list(read_records(args.historical_jsonl))
    if args.baseline_index:
        baseline = list(read_records(args.baseline_index))
        verify_historical_baseline(historical, baseline)
    current = earlier_current + (list(read_records(args.current_jsonl)) if args.current_jsonl else [])
    protected, indexed, report = reconcile(historical, current, args.expected_historical_records)
    if archived_view is not None:
        # An existing encrypted view may have older classification rules;
        # stream URL identities may never disappear or change.
        original_ids = [identity(row) for row in archived_view]
        new_ids = [identity(row) for row in indexed]
        if (None in original_ids or len(set(original_ids)) != len(original_ids)
                or not set(original_ids).issubset(set(new_ids))):
            raise ValueError("Encrypted archive candidate identities disagree")
    report["historical_preservation_verified"] = preserve_to_new_archive(args.out_archive, protected, indexed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

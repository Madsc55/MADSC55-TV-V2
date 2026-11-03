#!/usr/bin/env python3
"""Immutable SHA-only ledger guard for the four upstream M3U orphan sources.

No stream URL or channel title is persisted. A later upstream update must not
silently erase a previously broken channel identity, even if its URL remains
missing or its status changes to a valid M3U location. This check does not
prove A/V playback and never mutates the protected IBO playlist.
"""
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import zlib

HEX = re.compile(r"[0-9a-f]{64}\Z")
SOURCES = ("discevisita-tr", "github-auto-24",
           "onureroz-turk-karma", "onureroz-turk-all")


def load_immutable_baseline(path):
    envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    if (envelope.get("schema") != 1 or envelope.get("format") != "zlib+base64"
            or envelope.get("expected_orphan_occurrences") != 55
            or envelope.get("expected_unique_sha256") != 50):
        raise ValueError("Missing immutable 55/50 original source-identity envelope")
    encoded = envelope.get("content_base64")
    if not isinstance(encoded, str) or len(encoded) > 16384:
        raise ValueError("Oversized or missing source-identity evidence")
    compressed = base64.b64decode(encoded, validate=True)
    if len(compressed) > 12000:
        raise ValueError("Oversized compressed source-identity evidence")
    # Strict bounded expansion prevents accidentally accepting a decompression bomb.
    dec = zlib.decompressobj()
    raw = dec.decompress(compressed, 65000)
    if dec.unconsumed_tail or dec.unused_data or not dec.eof or len(raw) > 64000:
        raise ValueError("Invalid compressed immutable source identities")
    sha = hashlib.sha256(raw).hexdigest()
    if sha != envelope.get("decompressed_sha256"):
        raise ValueError("Immutable source SHA-256 proof mismatch")
    baseline = json.loads(raw)
    if (baseline.get("schema") != 1 or
            baseline.get("kind") != "V2_ORPHAN_SOURCE_IDENTITY_IMMUTABLE_HASH_BASELINE"
            or baseline.get("report_run_id") != envelope.get("source_run_id")
            or baseline.get("source_workflow_artifact_id") !=
               envelope.get("archive_artifact_id")):
        raise ValueError("Original orphan report provenance differs")
    sources = baseline.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(SOURCES):
        raise ValueError("Wrong upstream source identities")
    expected_per_source = {"discevisita-tr": 19, "github-auto-24": 21,
                           "onureroz-turk-karma": 8, "onureroz-turk-all": 7}
    all_hashes = []
    for source_id, expected in expected_per_source.items():
        items = sources[source_id]
        if (not isinstance(items, list) or len(items) != expected or
                len(set(items)) != len(items) or
                any(not isinstance(x, str) or not HEX.fullmatch(x) for x in items)):
            raise ValueError("Invalid or missing original orphan SHA identities")
        all_hashes.extend(items)
    if len(all_hashes) != 55 or len(set(all_hashes)) != 50:
        raise ValueError("Original 55 occurrences / 50 identities not preserved")
    return baseline


def reconcile_immutable_sources(baseline, source_documents):
    """Classify each original EXTINF identity as still absent, valid, or lost.

    A valid current HTTP stream is only a source-level fix; it is NOT proof
    that the media decodes or plays on the user's IBO Player.
    """
    if set(source_documents) != set(baseline["sources"]):
        raise ValueError("All four original source documents are required")
    source_evidence = {}
    all_missing = []
    present_count = restored_uri_count = still_orphan_count = 0
    new_orphans_total = 0
    for source_id, baseline_hashes in baseline["sources"].items():
        payload = source_documents[source_id]
        if not isinstance(payload, str):
            raise ValueError("Invalid M3U source document")
        # Runtime import avoids a dependency cycle with orphan_m3u_recovery.audit.
        from orphan_m3u_recovery import parse_exact_pairs, _hash
        valid_pairs, orphans = parse_exact_pairs(payload)
        current_extinf_hashes = {
            _hash(line.strip())
            for line in payload.splitlines()
            if line.strip().startswith("#EXTINF:")
        }
        valid_hashes = {_hash(meta) for meta in valid_pairs}
        orphan_hashes = {item["extinf_sha256"] for item in orphans}
        expected = set(baseline_hashes)
        missing = sorted(expected - current_extinf_hashes)
        still_orphan = expected & orphan_hashes
        restored = expected & valid_hashes
        present = expected & current_extinf_hashes
        new_orphans = orphan_hashes - expected
        present_count += len(present)
        still_orphan_count += len(still_orphan)
        restored_uri_count += len(restored)
        new_orphans_total += len(new_orphans)
        all_missing.extend(missing)
        source_evidence[source_id] = {
            "original_orphan_identities": len(expected),
            "present_original_identities": len(present),
            "original_orphans_still_without_valid_uri": len(still_orphan),
            "original_orphans_with_current_valid_source_uri_not_playback_verified": len(restored),
            "original_identities_missing_from_current_source": len(missing),
            "newly_unpaired_current_source_identities": len(new_orphans),
            "missing_extinf_sha256": missing[:55],
        }
    return {
        "schema": 1,
        "kind": "IMMUTABLE_55_ORPHAN_PROVENANCE_GUARD_NOT_PLAYBACK",
        "status": "LOSS_RISK_REVIEW_REQUIRED" if all_missing else
                  "NO_ORIGINAL_METADATA_IDENTITY_LOSS",
        "original_source_occurrences": 55,
        "original_distinct_extinf_identities": 50,
        "original_source_occurrences_still_present": present_count,
        "original_occurrences_with_current_valid_source_uri": restored_uri_count,
        "original_occurrences_still_unpaired": still_orphan_count,
        "original_occurrences_missing_metadata": len(all_missing),
        "new_orphan_occurrences": new_orphans_total,
        "sources": source_evidence,
        "no_plaintext_stream_urls": True,
        "playback_verified": False,
        "protected_playlist_modified": False,
    }

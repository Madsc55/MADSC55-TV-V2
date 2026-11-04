#!/usr/bin/env python3
"""One guarded, read-only search for exact Onureroz 10 identities in public M3U/M3U8."""
import argparse
import hashlib
import json
from pathlib import Path

from orphan_baseline_guard import load_immutable_baseline
from orphan_m3u_recovery import (ONUR_SOURCES, _read_document, parse_exact_pairs,
                                 find_existing_exact_identity, existing_source_catalog)
from orphan_targeted_github_code import targeted_source_references
from stage3_sealed_export import seal_rows

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "history/orphan-10-no-candidate-public-hashes.json"
BASELINE = ROOT / "history/m3u-orphan-50-hash-baseline.json"


def verified_targets(baseline, manifest, source_docs):
    hashes = manifest.get("no_candidate_hashes")
    if (manifest.get("schema") != 1 or
            manifest.get("kind") != "ORPHAN_10_SHA_ONLY_SOURCE_RECHECK" or
            manifest.get("source_run_id") != 41930930982 or
            manifest.get("original_occurrences") != 55 or
            manifest.get("original_identities") != 50 or
            not isinstance(hashes, list) or len(hashes) != 10 or
            len(set(hashes)) != 10 or
            any(not isinstance(x, str) or len(x) != 64 or
                any(c not in "0123456789abcdef" for c in x) for x in hashes)):
        raise ValueError("Missing exact 10-identity provenance")
    allowed = set(baseline["sources"]["onureroz-turk-all"]) | set(
        baseline["sources"]["onureroz-turk-karma"])
    if not set(hashes) <= allowed:
        raise ValueError("Unexpected identity outside original Onureroz evidence")
    if set(source_docs) != {sid for sid, _ in ONUR_SOURCES}:
        raise ValueError("Incomplete exact original publisher documents")
    matches = {}
    for sid, _ in ONUR_SOURCES:
        _, orphan_rows = parse_exact_pairs(source_docs[sid])
        for row in orphan_rows:
            digest = row["extinf_sha256"]
            if digest in hashes and digest in baseline["sources"][sid]:
                old = matches.setdefault(digest, row)
                if old["extinf"] != row["extinf"]:
                    raise ValueError("Contradictory original EXTINF bytes")
    if set(matches) != set(hashes):
        raise ValueError("Original ten metadata identities missing; no speculative reconstruction")
    return [matches[x] for x in sorted(hashes)]


def source_only_scan(targets, *, search=targeted_source_references,
                     match=find_existing_exact_identity, known=None):
    if len(targets) != 10 or len({x["extinf_sha256"] for x in targets}) != 10:
        raise ValueError("Expected 10 unique original identities")
    refs, lookup = search(targets, set() if known is None else set(known))
    if any(row.get("origin") != "orphan-discovery-reference" for row in refs):
        raise ValueError("Untrusted public source discovery reference")
    matched, review = match(targets, refs)
    if not set(matched) <= {x["extinf_sha256"] for x in targets}:
        raise ValueError("Source introduced unrequested original identity")
    private_rows = []
    for ident, candidates in sorted(matched.items()):
        for digest, record in sorted(candidates.items()):
            if hashlib.sha256(record["url"].encode("utf-8")).hexdigest() != digest:
                raise ValueError("Unverified candidate URL hash")
            private_rows.append({"url": record["url"], "url_sha256": digest,
                                 "original_extinf_sha256": ident,
                                 "proof_rules": record["proof_rules"],
                                 "proof_existing_source_ids": record["proof_existing_source_ids"],
                                 "av_verified": False})
    result = {
        "schema": 1, "kind": "V2_ORPHAN_10_SOURCE_ONLY_NO_AV",
        "original_occurrences_preserved": 55, "original_identities_preserved": 50,
        "original_no_candidate_identities_checked": 10,
        "queries_attempted": lookup["queries_attempted"],
        "queries_deferred_due_rate_limit": lookup.get("queries_deferred_due_rate_limit", 0),
        "failed_or_unavailable_queries": lookup["unavailable_or_failed_queries"],
        "anonymous_code_search_error_categories": lookup.get("anonymous_error_categories", {}),
        "incomplete_queries": lookup["incomplete_search_queries"],
        "source_document_references": len(refs),
        "unavailable_source_documents": review["source_documents_unavailable_count"],
        "exact_identity_matches": len(matched),
        "encrypted_candidate_rows": len(private_rows),
        "still_without_exact_candidate": 10 - len(matched),
        "source_reference_hashes": sorted(hashlib.sha256(
            item["url"].encode()).hexdigest() for item in refs),
        "candidate_url_hashes": sorted({x["url_sha256"] for x in private_rows}),
        "discovery_complete": (not lookup["unavailable_or_failed_queries"] and
                               not lookup["incomplete_search_queries"] and
                               not lookup["truncated_queries_or_references"] and
                               not review["source_documents_unavailable_count"]),
        "video_audio_verified": False, "ibo_device_verified": False,
        "protected_playlist_modified": False, "stream_urls_plaintext_reported": False}
    return result, private_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--sealed", type=Path, required=True)
    a = parser.parse_args()
    if (a.report.exists() or a.sealed.exists() or a.report.is_symlink()
            or a.sealed.is_symlink() or a.report.resolve() == a.sealed.resolve()):
        parser.error("Refuse overwrite or overlapping evidence outputs")
    base = load_immutable_baseline(BASELINE)
    snapshot = json.loads(MANIFEST.read_text(encoding="utf-8"))
    docs = {sid: _read_document(uri) for sid, uri in ONUR_SOURCES}
    targets = verified_targets(base, snapshot, docs)
    known = {x["url"] for x in existing_source_catalog()}
    report, private_rows = source_only_scan(targets, known=known)
    if private_rows:
        seal_rows(private_rows, ROOT / "config/stage3_transit_public.pem", a.sealed)
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                        encoding="utf-8")
    print("ORPHAN_10_SOURCE_ONLY", json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

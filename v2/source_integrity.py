#!/usr/bin/env python3
"""Independent loss audit for V2 discovery; no stream requests or plaintext URLs in reports."""
import hashlib

def sha(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

def verify(source_texts, live_text, scopes, candidates, parser, predicate, known_ids, source_audit, errors):
    """Rebuild the eligible URL set independently and fail closed on any lost candidate."""
    existing = {item["url"] for item in parser(live_text)}
    expected = {}
    all_parsed = 0
    eligible_entries = 0
    for source_id, content in source_texts:
        for item in parser(content):
            all_parsed += 1
            channel_id = item.get("tvg_id", "").strip().casefold()
            if not (predicate(item, scopes.get(source_id, "candidate")) or (channel_id and channel_id in known_ids)):
                continue
            eligible_entries += 1
            if item["url"] in existing:
                continue
            digest = sha(item["url"])
            expected.setdefault(digest, set()).add(source_id)
    observed = {}
    duplicates = 0
    malformed = 0
    for item in candidates:
        if not isinstance(item, dict):
            malformed += 1
            continue
        digest = item.get("url_sha256")
        sources = item.get("source_ids")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)
                or not isinstance(sources, list)
                or not sources or not all(isinstance(s, str) and s for s in sources)
                or len(sources) != len(set(sources))):
            malformed += 1
            continue
        if digest in observed:
            duplicates += 1
        observed[digest] = set(sources)
    missing = set(expected) - set(observed)
    unexpected = set(observed) - set(expected)
    provenance_mismatch = {digest for digest in expected.keys() & observed.keys()
                           if expected[digest] != observed[digest]}
    audit_failures = [row for row in source_audit
                      if not isinstance(row, dict) or row.get("status") == "FETCH_FAILED"]
    verified = not (missing or unexpected or provenance_mismatch or duplicates or malformed or errors or audit_failures)
    return {
        "schema": 1,
        "status": "COMPLETE" if verified else "INCOMPLETE",
        "verified": verified,
        "parsed_entries": all_parsed,
        "eligible_entries_including_duplicates": eligible_entries,
        "expected_unique_new_candidates": len(expected),
        "observed_unique_new_candidates": len(observed),
        "missing_candidate_count": len(missing),
        "unexpected_candidate_count": len(unexpected),
        "duplicate_candidate_count": duplicates,
        "malformed_candidate_count": malformed,
        "provenance_mismatch_count": len(provenance_mismatch),
        "source_error_count": len(errors),
        "missing_candidate_sha256": sorted(missing)[:100],
        "unexpected_candidate_sha256": sorted(unexpected)[:100],
        "provenance_mismatch_sha256": sorted(provenance_mismatch)[:100],
        "playback_verified": False,
    }

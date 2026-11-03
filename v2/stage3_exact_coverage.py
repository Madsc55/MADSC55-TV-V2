#!/usr/bin/env python3
"""Fail-closed exact coverage for genuine #60/#72 URL-SHA identities.

Inputs are anonymous hash evidence emitted by the existing source recovery
steps. A count of 4,955 by itself is NOT proof of historical membership.
No plaintext stream URL, decryption key or playback claim is produced.
"""
import re

HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _valid_sha(value):
    return isinstance(value, str) and HEX_SHA256.fullmatch(value) is not None


def verify_exact_coverage(baseline_rows, matched_groups, expected_count=4955):
    """Validate complete, exact baseline membership across independent sources.

    This does not independently decrypt sealed data or verify current playback.
    The source-specific collectors must only output hashes of actual URL strings.
    """
    rows = list(baseline_rows)
    if len(rows) != expected_count or not all(
        isinstance(row, dict) and _valid_sha(row.get("url_sha256"))
        for row in rows
    ):
        raise ValueError("Invalid historical baseline count or SHA256 format")
    baseline = {row["url_sha256"] for row in rows}
    if len(baseline) != expected_count:
        raise ValueError("Duplicate historical SHA256 identities")
    if not isinstance(matched_groups, dict) or not matched_groups:
        raise ValueError("Missing original-source evidence groups")
    union = set()
    for name, hashes in matched_groups.items():
        if not isinstance(name, str) or not name.strip() or hashes is None:
            raise ValueError("Invalid historical evidence source")
        group = set()
        for candidate in hashes:
            if not _valid_sha(candidate):
                raise ValueError("Invalid SHA256 in original-source evidence")
            if candidate not in baseline:
                raise ValueError("Evidence includes nonhistorical SHA256 identity")
            group.add(candidate)
        union.update(group)
    missing = baseline - union
    if missing:
        raise ValueError(f"Original historical SHA256 identities still missing: {len(missing)}")
    return union

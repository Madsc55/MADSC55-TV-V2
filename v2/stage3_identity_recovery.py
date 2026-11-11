"""Conservative, offline identity and recovery decisions for Stage 3.

No playlist writes, network access, or unverified playback promotions.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import urlsplit

TRANSIENT_HTTP = frozenset({408, 425, 429, 500, 502, 503, 504})
PERMANENT_HTTP = frozenset({400, 401, 403, 404, 410, 451})


def url_sha256(url: str) -> str:
    """Hash the exact URL bytes; do not strip tokens or normalize query strings."""
    if not isinstance(url, str):
        raise TypeError("URL must be a string")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("invalid HTTP(S) URL")
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def classify_failure(status: int | None, *, timeout: bool = False, network_error: bool = False) -> str:
    """Unknown and transient failures must not destroy prior successful evidence."""
    if timeout or network_error or status is None or status in TRANSIENT_HTTP:
        return "RETRY"
    if status in PERMANENT_HTTP:
        return "REVIEW"
    if 200 <= status < 300:
        return "CHECK_AV"
    return "REVIEW"


def merge_evidence(previous: dict, incoming: dict) -> dict:
    """Keep immutable historical observations; never promote based on HTTP alone."""
    if previous.get("url") != incoming.get("url"):
        raise ValueError("cannot merge different URL identities")
    url_sha256(previous["url"])
    merged = dict(previous)
    old = previous.get("observations", [])
    new = incoming.get("observations", [])
    if not isinstance(old, list) or not isinstance(new, list):
        raise ValueError("observations must be lists")
    if not all(isinstance(item, dict) for item in old + new):
        raise ValueError("observations must contain objects")
    merged["observations"] = [*old, *new]
    merged["url_sha256"] = url_sha256(previous["url"])
    for field in ("name", "tvg_id", "country", "group", "language", "logo"):
        if not merged.get(field) and incoming.get(field):
            merged[field] = incoming[field]
    ids = []
    for record in (previous, incoming):
        for value in [record.get("source_id"), *(record.get("source_ids") or [])]:
            if isinstance(value, str) and value and value not in ids:
                ids.append(value)
    merged["source_ids"] = ids
    # AV evidence remains an observation, not an inferred property of a URL.
    return merged


def recovery_decision(record: dict, status: int | None, *, timeout: bool = False) -> dict:
    """Return a decision; callers persist the original record separately."""
    sha = url_sha256(record["url"])
    outcome = classify_failure(status, timeout=timeout)
    return {"url_sha256": sha, "action": outcome,
            "preserve_history": True, "remove_from_inventory": False,
            "av_verified": False}

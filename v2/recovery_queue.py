#!/usr/bin/env python3
"""Deterministic offline recovery queue; never treats metadata as playback proof."""
import hashlib

TRANSIENT = {"TIMEOUT", "RATE_LIMITED", "FETCH_FAILED", "HTTP_ERROR", "PROBE_UNAVAILABLE"}
VERIFIED = "AV_VERIFIED"


def build_queue(records, max_attempts=3):
    if type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("max_attempts must be a positive integer")
    queue, held, accepted, seen = [], [], [], set()
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("Recovery record must be an object")
        digest = item.get("url_sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Missing or invalid URL SHA-256")
        if digest in seen:
            raise ValueError("Duplicate recovery URL digest")
        seen.add(digest)
        attempts = item.get("attempts", 0)
        if type(attempts) is not int or attempts < 0:
            raise ValueError("Invalid attempt count")
        status = item.get("status", "UNVERIFIED")
        row = {"url_sha256": digest, "status": status, "attempts": attempts}
        if status == VERIFIED and item.get("video") is True and item.get("audio") is True:
            accepted.append(row)
        elif status in TRANSIENT and attempts < max_attempts:
            queue.append({**row, "next_attempt": attempts + 1})
        else:
            held.append(row)
    return {"retry": queue, "hold": held, "verified": accepted}


def sha_for_url(url):
    if not isinstance(url, str) or not url:
        raise ValueError("URL required")
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

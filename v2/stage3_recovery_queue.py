"""Deterministic Stage 3 recovery queue derived from preserved inventory.

Offline only; callers must supply real observations and persist queues privately.
"""
from __future__ import annotations

from stage3_identity_recovery import recovery_decision, url_sha256


def build_recovery_queue(records: list[dict], *, max_attempts: int = 3) -> list[dict]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    queue = []
    seen = set()
    for record in records:
        sha = url_sha256(record["url"])
        if sha in seen:
            raise ValueError("duplicate URL in inventory")
        seen.add(sha)
        attempts = record.get("recovery_attempts", 0)
        if type(attempts) is not int or attempts < 0:
            raise ValueError("invalid recovery attempt count")
        observations = record.get("observations", [])
        if not isinstance(observations, list) or any(not isinstance(x, dict) for x in observations):
            raise ValueError("invalid observations")
        status = record.get("last_http_status")
        if status is not None and (type(status) is not int or status < 100 or status > 599):
            raise ValueError("invalid HTTP status")
        decision = recovery_decision(record, status,
                                     timeout=record.get("last_timeout") is True)
        if attempts >= max_attempts:
            action = "REVIEW"
        else:
            action = decision["action"]
        if action in ("RETRY", "CHECK_AV", "REVIEW"):
            queue.append({"url_sha256": sha, "action": action,
                          "attempts": attempts, "next_attempt": (attempts + 1 if action != "REVIEW" else None),
                          "preserve_history": True})
    return sorted(queue, key=lambda item: (item["attempts"], item["url_sha256"]))

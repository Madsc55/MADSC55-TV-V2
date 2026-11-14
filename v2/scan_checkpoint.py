"""Encrypted, authenticated progress checkpoints for the read-only real AV scanner.

Only a recent observation of the exact URL may be reused. Reused decoded AV
is identified as *previous-checkpoint evidence*, never decoded in the new run.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import tempfile
import time

from secure_archive import decrypt, encrypt
from stage3_identity_recovery import url_sha256

SCHEMA = "MADSC55-V2-REAL-SCAN-CHECKPOINT-1"
MAX_AGE_SECONDS = 18 * 60 * 60
MAX_ROWS = 200_000


def _valid_result(result):
    if result is None:
        return True
    return (isinstance(result, dict)
            and result.get("decoded_av_verified") is True
            and result.get("decode_status") == "DECODED_AV"
            and isinstance(result.get("verified_quality"), dict)
            and result["verified_quality"].get("av_verified") is True)


def load_progress(path, passphrase, *, worldwide, now=None):
    """Read validated rows from a previous encrypted checkpoint.

    A missing file means a new scan. Corrupt, mismatched or unauthenticated
    checkpoint data fail closed instead of silently asserting old AV proof.
    Rows older than the freshness window are not reused.
    """
    path = Path(path)
    if not path.exists():
        return {}
    if path.is_symlink():
        raise ValueError("Symlinked scan checkpoint refused")
    raw = decrypt(path.read_bytes(), passphrase)
    report = json.loads(raw)
    if (not isinstance(report, dict)
            or report.get("schema") != SCHEMA
            or type(report.get("worldwide")) is not bool
            or report["worldwide"] is not worldwide
            or not isinstance(report.get("rows"), list)
            or len(report["rows"]) > MAX_ROWS):
        raise ValueError("Invalid scan checkpoint format or scope")
    now = time.time() if now is None else now
    accepted = {}
    for item in report["rows"]:
        if not isinstance(item, dict):
            raise ValueError("Invalid checkpoint row")
        url = item.get("url")
        sha = item.get("url_sha256")
        checked_at = item.get("checked_at")
        if (not isinstance(url, str) or url_sha256(url) != sha
                or type(checked_at) not in (int, float)
                or not math.isfinite(checked_at)
                or not isinstance(item.get("diagnostics"), dict)
                or not _valid_result(item.get("result"))):
            raise ValueError("Invalid checkpoint observation")
        if url in accepted:
            raise ValueError("Duplicate checkpoint URL")
        if -60 <= now - checked_at <= MAX_AGE_SECONDS:
            accepted[url] = item
    return accepted


def save_progress(path, passphrase, *, worldwide, rows):
    """Replace only the dedicated progress file, atomically and encrypted.

    The previous valid checkpoint remains on disk if encryption or write fails.
    Never write the plaintext URL/token inventory to a temporary file.
    """
    path = Path(path)
    if path.name != "ibo-scan-progress.enc":
        raise ValueError("Only the dedicated scan checkpoint may be replaced")
    if path.is_symlink():
        raise ValueError("Symlinked scan checkpoint refused")
    if len(rows) > MAX_ROWS:
        raise ValueError("Checkpoint observation count exceeds limit")
    payload = {"schema": SCHEMA, "worldwide": bool(worldwide),
               "rows": list(rows.values())}
    encrypted = encrypt((json.dumps(payload, ensure_ascii=False,
                                    separators=(",", ":")) + "\n").encode(), passphrase)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".v2-scan-progress-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(encrypted)
            output.flush()
            os.fsync(output.fileno())
        # Replace the checkpoint inode, not a protected playlist or baseline.
        os.replace(temporary, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"saved": len(rows), "encrypted": True}


def checkpoint_row(url, result, diagnostics, *, checked_at=None):
    """Retain the exact URL and actual decoded-video+audio evidence privately."""
    compact_result = None
    if result is not None:
        if not _valid_result(result):
            raise ValueError("Only truly decoded AV may be checkpointed as success")
        compact_result = {
            "decoded_av_verified": True,
            "decode_status": "DECODED_AV",
            "verified_quality": result["verified_quality"],
        }
    return {
        "url": url,
        "url_sha256": url_sha256(url),
        "checked_at": time.time() if checked_at is None else checked_at,
        "result": compact_result,
        "diagnostics": dict(diagnostics),
    }

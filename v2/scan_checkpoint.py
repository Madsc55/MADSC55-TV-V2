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
    if path.is_symlink():
        raise ValueError("Symlinked scan checkpoint refused")
    if not path.exists():
        return {}
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
                or not _valid_result(item.get("result"))
                or type(item.get("recovery_attempts", 0)) is not int
                or not 0 <= item.get("recovery_attempts", 0) <= 3):
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


def checkpoint_row(url, result, diagnostics, *, checked_at=None, recovery_attempts=0):
    """Retain the exact URL and actual decoded-video+audio evidence privately."""
    if type(recovery_attempts) is not int or not 0 <= recovery_attempts <= 3:
        raise ValueError("Recovery attempt count must be a nonnegative integer, capped at 3")
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
        "recovery_attempts": recovery_attempts,
    }


def bootstrap_from_pending_inventory(inventory_path, report_path, destination,
                                     passphrase, *, observed_at, now=None):
    """Recover real prior-run observations from a legacy encrypted pending inventory.

    Older real-scan runs saved the authenticated candidate inventory but not a
    per-100-stream checkpoint. This upgrades that evidence without reclassifying
    old FFmpeg decodes as current-run results. An incomplete source fetch remains
    incomplete; this cannot turn a failed scan into an accepted IBO package.
    """
    from datetime import datetime, timezone
    inventory_path, report_path = Path(inventory_path), Path(report_path)
    if (inventory_path.is_symlink() or report_path.is_symlink()
            or inventory_path.name != "ibo-candidate-inventory.jsonl.pending.enc"
            or report_path.name != "ibo-real-scan-report.json"):
        raise ValueError("Unexpected pending evidence path")
    if not isinstance(observed_at, str):
        raise ValueError("Prior run start is required")
    try:
        stamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid prior run start") from exc
    if stamp.tzinfo is None:
        raise ValueError("Prior run start must specify UTC offset")
    started = stamp.astimezone(timezone.utc).timestamp()
    now = time.time() if now is None else now
    if not -60 <= now - started <= MAX_AGE_SECONDS:
        raise ValueError("Previous AV evidence is expired or from the future")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (not isinstance(report, dict)
            or report.get("status") != "INCOMPLETE_SOURCE_FETCH_OR_DROP"
            or report.get("scan_scope") != "WORLDWIDE_ALL_SOURCE_ENTRIES"
            or report.get("archive_restore_test_passed") is not True
            or report.get("mock_data_used") is not False
            or not str(report.get("candidate_inventory", "")).endswith(
                "/ibo-candidate-inventory.jsonl.pending.enc")
            or type(report.get("unique_new_candidates")) is not int
            or type(report.get("http_checked")) is not int
            or type(report.get("av_verified")) is not int):
        raise ValueError("Pending scan report is not authenticated acceptance evidence")
    if report["http_checked"] != report["unique_new_candidates"]:
        raise ValueError("Previous real scan lacks observations for all discovered streams")

    plaintext = decrypt(inventory_path.read_bytes(), passphrase)
    rows = {}
    decoded = 0
    for line in plaintext.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            raise ValueError("Invalid legacy inventory row")
        url = record.get("url")
        if (not isinstance(url, str)
                or url_sha256(url) != record.get("url_sha256")
                or url in rows):
            raise ValueError("Invalid or duplicated legacy URL identity")
        status = record.get("http_hls_status")
        decoded_av = record.get("decoded_av_verified")
        quality = record.get("verified_quality")
        if status == "AV_VERIFIED":
            if (decoded_av is not True
                    or record.get("decode_status") != "DECODED_AV"
                    or not isinstance(quality, dict)
                    or quality.get("av_verified") is not True):
                raise ValueError("Unproven AV cannot be resumed as verified")
            result = {"decoded_av_verified": True,
                      "decode_status": "DECODED_AV",
                      "verified_quality": quality}
            decoded += 1
        elif status == "UNVERIFIED_OR_FAILED" and decoded_av is False:
            result = None
        else:
            raise ValueError("Unexpected legacy candidate evidence state")
        diagnostics = {"last_http_status": record.get("last_http_status"),
                       "last_timeout": record.get("last_timeout") is True}
        prior_attempts = record.get("recovery_attempts", 0)
        rows[url] = checkpoint_row(
            url, result, diagnostics, checked_at=started,
            recovery_attempts=prior_attempts)
    if (len(rows) != report["http_checked"]
            or decoded != report["av_verified"]):
        raise ValueError("Legacy encrypted inventory does not match real scan counts")
    save_progress(destination, passphrase, worldwide=True, rows=rows)
    return {"resumed_rows": len(rows), "prior_decoded_av": decoded,
            "last_scan_was_incomplete": True}

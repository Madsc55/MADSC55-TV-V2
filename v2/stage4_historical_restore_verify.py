#!/usr/bin/env python3
"""Offline-only verification of historical Stage 4 offsite Drive restore evidence.

Checks byte-for-byte equality of the pinned Actions archive and independently
retrieved Drive ciphertext, plus the exact producer and independent restore
receipts. DOES NOT decrypt, rerun a restore, or accept the separate #6 Turkish
authorized vault. No network calls or playlist/archive modifications.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

EXPECTED = {
    "run_id": "43241168321",
    "engine_commit": "5a1766dfcd5e37eca0cfcaf9e10129116c67db2e",
    "producer_zip_sha256": "92766f43a713de6363577b6c179d9669e3d14ae3131e8e0efccd5f6c8007f369",
    "restore_zip_sha256": "b84546022f16e1c1e6583ec132e650f80c09c3ba5ade4e547cba4c086200427c",
    "producer_receipt_sha256": "7d29d1e96f1cdf69bc6310637711a8fa8ec7f03f55cbd3297d6c5f33dbf051f6",
    "accepted_receipt_sha256": "66790f47497edab8e3a813e53ee6a606eaba70d34f3b450a325e1804ce1adf68",
    "archive_sha256": "29f5498c3173b39afe5c4bee824e4423cc8229961fb5f7cbf26e402d449f4241",
    "archive_bytes": 7832688,
    "archive_records": 7819,
    "candidates": 7769,
    "historical_records": 4955,
    "sources_fetched": 46,
    "all_regions_av": 801,
    "tr_az_av": 800,
    "drive_version": "4",
    "drive_revision_sha256": "566dc770f4087c0f3d4d39e413f6e706aa43b668eda018f8ae1d5fe45998b4bb",
}
MAX_ZIP_BYTES = 20 * 1024 * 1024
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate JSON receipt key")
        obj[key] = value
    return obj


def _read(path, max_bytes):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Evidence source must be a non-symlink regular file")
    if not 0 < path.stat().st_size <= max_bytes:
        raise ValueError("Evidence input is empty or oversized")
    raw = path.read_bytes()
    if not 0 < len(raw) <= max_bytes:
        raise ValueError("Evidence input exceeds byte limit")
    return raw


def _members(raw, names):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        entries = z.infolist()
        if sorted(item.filename for item in entries) != sorted(names):
            raise ValueError("Evidence ZIP members changed or duplicated")
        if any(item.is_dir() or item.flag_bits & 1
               or item.file_size > MAX_ARCHIVE_BYTES for item in entries):
            raise ValueError("Unsafe evidence ZIP member")
        return {name: z.read(name) for name in names}


def _receipt(raw, expected_hash):
    if not 0 < len(raw) <= 10000 or digest(raw) != expected_hash:
        raise ValueError("Receipt content SHA-256 mismatch")
    obj = json.loads(raw, object_pairs_hook=_unique_pairs)
    if not isinstance(obj, dict):
        raise ValueError("Receipt must be a JSON object")
    return obj


def verify(producer_zip, restore_zip, drive_archive, *, expected=EXPECTED):
    source_bytes = _read(producer_zip, MAX_ZIP_BYTES)
    receipt_bytes = _read(restore_zip, MAX_ZIP_BYTES)
    drive_bytes = _read(drive_archive, MAX_ARCHIVE_BYTES)
    if digest(source_bytes) != expected["producer_zip_sha256"]:
        raise ValueError("Producer artifact SHA-256 mismatch")
    if digest(receipt_bytes) != expected["restore_zip_sha256"]:
        raise ValueError("Independent restore artifact SHA-256 mismatch")
    source = _members(source_bytes, ("inventory.enc", "receipt.json"))
    restored = _members(receipt_bytes, ("accepted.json",))
    archive_bytes = source["inventory.enc"]
    if (len(archive_bytes) != expected["archive_bytes"]
            or len(drive_bytes) != expected["archive_bytes"]
            or digest(archive_bytes) != expected["archive_sha256"]
            or digest(drive_bytes) != expected["archive_sha256"]
            or archive_bytes != drive_bytes):
        raise ValueError("Producer and independently retrieved Drive ciphertext differ")
    source_receipt = _receipt(source["receipt.json"], expected["producer_receipt_sha256"])
    restore_receipt = _receipt(restored["accepted.json"], expected["accepted_receipt_sha256"])
    if (set(restore_receipt) != set(source_receipt) |
            {"drive", "restored_from", "restored_records"}):
        raise ValueError("Restore receipt keys differ from the source")
    if any(restore_receipt[key] != val for key, val in source_receipt.items()):
        raise ValueError("Restore receipt changed the original producer claims")
    for key in ("run_id", "engine_commit"):
        if source_receipt.get(key) != expected[key]:
            raise ValueError("Incorrect historical source identity")
    for key in ("archive_bytes", "candidates", "historical_records",
                "sources_fetched", "all_regions_av", "tr_az_av"):
        if type(source_receipt.get(key)) is not int or source_receipt[key] != expected[key]:
            raise ValueError("Historical source count does not match evidence")
    if (source_receipt.get("archive") != {
            "schema": 1, "record_count": expected["archive_records"],
            "sha256": expected["archive_sha256"]}
            or type(restore_receipt.get("restored_records")) is not int
            or restore_receipt["restored_records"] != expected["archive_records"]
            or restore_receipt.get("restored_from") != "google-drive-independent-runner"
            or restore_receipt.get("drive") != {
                "version": expected["drive_version"],
                "revision_sha256": expected["drive_revision_sha256"]}):
        raise ValueError("Historical independent Drive restore receipt mismatch")
    return {
        "status": "PINNED_HISTORICAL_STAGE4_DRIVE_RECEIPTS_MATCH",
        "source_actions_run": expected["run_id"],
        "encrypted_archive_sha256": expected["archive_sha256"],
        "encrypted_archive_bytes": expected["archive_bytes"],
        "producer_artifact_sha256": expected["producer_zip_sha256"],
        "restore_artifact_sha256": expected["restore_zip_sha256"],
        "historical_restore_receipt_record_count": expected["archive_records"],
        "historical_restore_receipt_original_history": expected["historical_records"],
        "offline_artifact_provenance_verified": True,
        "ci_job_status_checked_by_this_script": False,
        "new_decryption_performed": False,
        "new_restore_performed": False,
        "turkish_authorized_vault_issue6_accepted": False,
        "playlist_modified": False,
        "new_scan_started": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-zip", type=Path, required=True)
    parser.add_argument("--restore-zip", type=Path, required=True)
    parser.add_argument("--drive-archive", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.producer_zip, args.restore_zip, args.drive_archive),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

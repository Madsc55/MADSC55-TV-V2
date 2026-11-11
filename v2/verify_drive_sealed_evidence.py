#!/usr/bin/env python3
"""Verify V2 owner-private Drive ciphertext copies; optionally decrypt with RSA key.

Never logs stream URLs. No scanning, playlist edits, new archive fabrication, or
false production pass when the original RSA private key is unavailable.
"""
import argparse
import base64
import hashlib
import json
import re
import tempfile
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from stage3_sealed_export import open_rows
from production_full_stage5_archive import verify as verify_production_aes

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "history/offsite-sealed-drive-20261103.json"
BASELINE = HERE / "history/stage3-4955-hash-only.jsonl"

def checksum(file):
    h = hashlib.sha256()
    with Path(file).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def audit_zip(path, descriptor, private_key=None):
    if checksum(path) != descriptor["source_zip_sha256"]:
        raise ValueError("Independent encrypted ZIP checksum mismatch")
    if Path(path).stat().st_size != descriptor["archive_size_bytes"]:
        raise ValueError("Restored ZIP length differs from original")
    recovered = {}
    with ZipFile(path) as archive:
        entries = archive.namelist()
        if len(entries) != len(set(entries)) or len(entries) > 100:
            raise ValueError("Ambiguous ZIP entries")
        if any("/" in name or ".." in name or name.startswith(".") for name in entries):
            raise ValueError("Unsafe ZIP member name")
        for name, expected_rows in descriptor["sealed_record_counts"].items():
            if name not in entries:
                raise ValueError("Missing original sealed evidence member")
            data = json.loads(archive.read(name))
            if data.get("schema") != 1 or data.get("kind") != "RSA_OAEP_SHA256_AES256_GCM_ZLIB":
                raise ValueError("Unknown sealed archive format")
            if data.get("records_encrypted") != expected_rows:
                raise ValueError("Encrypted record count differs")
            if (len(base64.b64decode(data["nonce"], validate=True)) != 12 or
                    len(base64.b64decode(data["wrapped_key"], validate=True)) < 384 or
                    len(base64.b64decode(data["ciphertext"], validate=True)) <= 16):
                raise ValueError("Invalid RSA/AES evidence envelope")
            if private_key:
                with tempfile.TemporaryDirectory() as directory:
                    sealed = Path(directory) / "evidence.sealed"
                    sealed.write_bytes(archive.read(name))
                    sealed.chmod(0o600)
                    rows = open_rows(sealed, private_key)
                if len(rows) != expected_rows:
                    raise ValueError("RSA private restore record count mismatch")
                found = set()
                for row in rows:
                    if not isinstance(row, dict) or not isinstance(row.get("url"), str):
                        raise ValueError("Private restore row lacks real URL")
                    key = hashlib.sha256(row["url"].encode("utf-8")).hexdigest()
                    if key != row.get("url_sha256"):
                        raise ValueError("RSA private restore URL SHA256 mismatch")
                    if key in found:
                        raise ValueError("Duplicate decrypted URL evidence")
                    found.add(key)
                recovered[name] = found
        if descriptor["label"] == "stage3-4955":
            raw = archive.read("stage3-4955-hash-only.jsonl")
            if hashlib.sha256(raw).hexdigest() != json.loads(MANIFEST.read_text())["historic_rows_sha256"]:
                raise ValueError("Original history JSONL bytes changed")
            public = json.loads(archive.read("stage3-combined-real-url-recovery.json"))
            if len(public["matched_hashes"]) != 4955:
                raise ValueError("Historical matching evidence lost entries")
        if descriptor["label"] == "orphan-107":
            report = json.loads(archive.read("three-source-orphan-anonymous.json"))
            if report["orphan_entries"] != 55 or report["unique_orphan_metadata_identities"] != 50:
                raise ValueError("Original orphan metadata mismatch")
    return recovered

def verify(stage3, orphan, private_key=None):
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (m["production_acceptance_complete"] is not False or
            m["encrypted_url_decryption_verified"] is not False or
            m["ciphertext_zip_digest_verified"] is not True):
        raise ValueError("Manifest attempts to overstate production acceptance")
    expected = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]
    identities = {row["url_sha256"] for row in expected}
    if len(expected) != 4955 or len(identities) != 4955:
        raise ValueError("Immutable history missing rows")
    if hashlib.sha256("".join(sorted(identities)).encode()).hexdigest() != m["historic_identity_sha256"]:
        raise ValueError("Immutable history checksum mismatch")
    result1 = audit_zip(stage3, m["encrypted_artifact_checks"][0], private_key)
    result2 = audit_zip(orphan, m["encrypted_artifact_checks"][1], private_key)
    if private_key:
        union = set().union(*result1.values())
        if union != identities:
            raise ValueError("Decrypted stage3 URLs do not cover exactly the 4955 historical identities")
        all_orphan = result2["three-source-all-historical-candidates.sealed"]
        verified = result2["three-source-av-verified.sealed"]
        if len(all_orphan) != 107 or len(verified) != 4 or not verified.issubset(all_orphan):
            raise ValueError("Orphan decryption does not match 107/4 evidence")
        return "RSA_AES_DECRYPTION_4955_IDENTITIES_AND_107_ORPHAN_CANDIDATES_VERIFIED"
    return "DRIVE_INDEPENDENT_CIPHERTEXT_READBACK_VERIFIED_RSA_PRIVATE_RESTORE_NOT_YET_PROVEN"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--stage3", type=Path, required=True)
    p.add_argument("--orphan", type=Path, required=True)
    p.add_argument("--rsa-private-key", type=Path)
    p.add_argument("--production-aes", type=Path)
    p.add_argument("--production-aes-key", type=Path)
    p.add_argument("--production-aes-sha256")
    a = p.parse_args()
    print(verify(a.stage3, a.orphan, a.rsa_private_key))
    production_inputs = (a.production_aes, a.production_aes_key, a.production_aes_sha256)
    if any(x is not None for x in production_inputs):
        if not all(x is not None for x in production_inputs):
            raise ValueError("Production AES acceptance requires archive, original key metadata and pinned SHA256 together")
        result = verify_production_aes(*production_inputs)
        if not result.get("full_aes_gcm_restore") or not result.get("exact_sha256_identities_verified"):
            raise ValueError("Production AES independent restore acceptance failed")
        print("DRIVE_PRODUCTION_AES_4955_PLUS_107_AUTHENTICATED_RESTORE_VERIFIED")

if __name__ == "__main__":
    main()

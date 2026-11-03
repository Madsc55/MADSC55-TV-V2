#!/usr/bin/env python3
"""MADSC55 TV V2: independently recoverable encrypted evidence bundle.

Safely packages the genuine original Stage 3 + orphan Actions artifacts.
Does NOT decrypt the original RSA-sealed streaming URLs or claim playback.
Only the new outer AES-256-GCM archive can be restored using its private key.
Never logs URLs or private key bytes. Never writes the main IBO playlist.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import stat
from zipfile import ZipFile, ZIP_STORED

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"MADSC55-TV-V2-ENCRYPTED-EVIDENCE-BUNDLE-v1\n"
AAD = b"MADSC55-TV-V2-PRODUCTION-SEALED-EVIDENCE-v1"
EXPECTED_HISTORY_COUNT = 4955
EXPECTED_HISTORY_IDENTITY_DIGEST = "e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83"
EXPECTED_ORPHAN_CANDIDATES = 107
EXPECTED_ORPHAN_VERIFIED = 4
EXPECTED_ORPHAN_METADATA = 50
MAX_BYTES = 24_000_000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _validate_artifacts(stage3_bytes, orphan_bytes):
    """Require genuine 4955 baseline coverage, sealed real URL evidence, and orphan report."""
    with ZipFile(io.BytesIO(stage3_bytes)) as z:
        names = z.namelist()
        required = ["stage3-4955-hash-only.jsonl", "stage3-combined-real-url-recovery.json",
                    "stage3-git-history-recovered.sealed", "stage3-original-github-recovered.sealed",
                    "stage3-original-configured-recovered.sealed",
                    "stage3-dearbulut-health-recovered.sealed"]
        if any(n not in names for n in required) or len(names) != len(set(names)):
            raise ValueError("Stage3 genuine original evidence files missing or duplicated")
        raw = z.read(required[0])
        rows = [json.loads(line) for line in raw.splitlines() if line]
        hashes = [r.get("url_sha256") for r in rows]
        if (len(rows) != EXPECTED_HISTORY_COUNT or len(set(hashes)) != EXPECTED_HISTORY_COUNT
                or not all(isinstance(h, str) and len(h) == 64 for h in hashes)
                or sha(''.join(sorted(hashes)).encode()) != EXPECTED_HISTORY_IDENTITY_DIGEST):
            raise ValueError("Immutable 4955 historical identities missing or changed")
        recovered = json.loads(z.read(required[1]))
        if (recovered.get("unique_exact_original_url_matches") != EXPECTED_HISTORY_COUNT
                or recovered.get("still_without_original_url") != 0
                or len(recovered.get("matched_hashes", [])) != EXPECTED_HISTORY_COUNT
                or set(recovered.get("matched_hashes", [])) != set(hashes)):
            raise ValueError("Recovered historical evidence does not match 4955 exact original identities")
        counts = {}
        for n in required[2:]:
            env = json.loads(z.read(n))
            if (env.get("kind") != "RSA_OAEP_SHA256_AES256_GCM_ZLIB"
                    or env.get("schema") != 1
                    or not isinstance(env.get("records_encrypted"), int)):
                raise ValueError("Expected RSA/AES sealed stage3 artifact")
            for fld in ("nonce", "wrapped_key", "ciphertext"):
                if not isinstance(env.get(fld), str) or not base64.b64decode(env[fld], validate=True):
                    raise ValueError("Sealed stage3 evidence not structurally valid")
            counts[n] = env["records_encrypted"]
        if counts["stage3-git-history-recovered.sealed"] != 4902:
            raise ValueError("Real Stage3 Git forensics evidence changed")

    with ZipFile(io.BytesIO(orphan_bytes)) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate orphan archive records")
        required = ["three-source-orphan-anonymous.json",
                    "three-source-all-historical-candidates.sealed",
                    "three-source-av-verified.sealed"]
        if any(n not in names for n in required):
            raise ValueError("Real orphan source evidence missing")
        report = json.loads(z.read(required[0]))
        if (report.get("orphan_entries") != 55 or
                report.get("unique_orphan_metadata_identities") != EXPECTED_ORPHAN_METADATA or
                report.get("all_proven_url_candidates_sealed_for_future_retest") != EXPECTED_ORPHAN_CANDIDATES or
                report.get("unique_candidates_video_audio_verified") != EXPECTED_ORPHAN_VERIFIED):
            raise ValueError("Original 55/50 orphan report or 107/4 candidates changed")
        for name, count in ((required[1], EXPECTED_ORPHAN_CANDIDATES),
                            (required[2], EXPECTED_ORPHAN_VERIFIED)):
            env = json.loads(z.read(name))
            if env.get("kind") != "RSA_OAEP_SHA256_AES256_GCM_ZLIB" or env.get("records_encrypted") != count:
                raise ValueError("Original RSA/AES orphan sealed candidate count changed")
    return {"historical_identity_count": EXPECTED_HISTORY_COUNT,
            "historical_identity_sha256": EXPECTED_HISTORY_IDENTITY_DIGEST,
            "original_url_hash_matches": EXPECTED_HISTORY_COUNT,
            "orphan_metadata_identities": EXPECTED_ORPHAN_METADATA,
            "orphan_source_occurrences": 55,
            "orphan_sealed_candidates": EXPECTED_ORPHAN_CANDIDATES,
            "orphan_av_verified_evidence": EXPECTED_ORPHAN_VERIFIED,
            "rsa_private_url_decryption_verified": False,
            "ibo_device_verified": False}


def create_archive(stage3, orphan, archive, key_file):
    """Create a new authenticated archive and separate 256-bit key (both owner-only)."""
    archive, key_file = Path(archive), Path(key_file)
    if archive.exists() or archive.is_symlink() or key_file.exists() or key_file.is_symlink():
        raise FileExistsError("Refusing to overwrite archive or private recovery key")
    stage3_bytes, orphan_bytes = Path(stage3).read_bytes(), Path(orphan).read_bytes()
    details = _validate_artifacts(stage3_bytes, orphan_bytes)
    manifest = {"schema": 1, "system": "MADSC55-TV-V2", "scope": "genuine historical sealed recovery evidence",
                "stage3_zip_sha256": sha(stage3_bytes), "orphan_zip_sha256": sha(orphan_bytes),
                "stage3_zip_size": len(stage3_bytes), "orphan_zip_size": len(orphan_bytes), **details}
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_STORED) as z:
        z.writestr("manifest.json", json.dumps(manifest, sort_keys=True, separators=(',', ':')))
        z.writestr("stage3-original-evidence.zip", stage3_bytes)
        z.writestr("orphan-original-evidence.zip", orphan_bytes)
    raw = buffer.getvalue()
    key = secrets.token_bytes(32)
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, raw, AAD)
    payload = MAGIC + nonce + ciphertext
    if len(payload) > MAX_BYTES:
        raise ValueError("Archive exceeds bounded size")
    for target, content in ((archive, payload), (key_file, json.dumps({
            "schema": 1, "system": "MADSC55-TV-V2", "format": "AES-256-GCM-RECOVERY-KEY",
            "key_base64": base64.b64encode(key).decode(),
            "archive_sha256": sha(payload), "archive_manifest_sha256": sha(raw),
            "warning": "PRIVATE SECRET. Never commit or publicly share this key."
        }, sort_keys=True).encode())):
        target.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(content); f.flush(); os.fsync(f.fileno())
    if not verify_archive(archive, key_file, expected_sha=sha(payload))['evidence_restored']:
        raise RuntimeError("Fresh encrypted archive failed immediate AES-GCM restore")
    return {"sha256": sha(payload), "bytes": len(payload), **details}


def verify_archive(archive, key_file, expected_sha=None):
    """Restore, fully authenticate AES bundle, validate unchanged source artifacts."""
    path, key_path = Path(archive), Path(key_file)
    for item in (path, key_path):
        if item.is_symlink() or not item.is_file() or not stat.S_ISREG(item.stat().st_mode):
            raise ValueError("Restore archive or private key must be regular non-symlink file")
    if key_path.stat().st_mode & 0o077:
        raise PermissionError("Private recovery key must be owner-only")
    payload = path.read_bytes()
    if len(payload) > MAX_BYTES or not payload.startswith(MAGIC):
        raise ValueError("Invalid V2 encrypted bundle")
    actual_sha = sha(payload)
    if expected_sha and expected_sha != actual_sha:
        raise ValueError("Independently pinned SHA256 differs from restored archive")
    key_info = json.loads(key_path.read_text())
    if key_info.get("format") != "AES-256-GCM-RECOVERY-KEY" or key_info.get("archive_sha256") != actual_sha:
        raise ValueError("Recovery key escrow does not match original archive")
    key = base64.b64decode(key_info["key_base64"], validate=True)
    if len(key) != 32:
        raise ValueError("Invalid AES-256 key")
    header = len(MAGIC)
    try:
        plaintext = AESGCM(key).decrypt(payload[header:header + 12], payload[header + 12:], AAD)
    except Exception as exc:
        raise ValueError("AES-GCM authenticated recovery failed") from exc
    if sha(plaintext) != key_info.get("archive_manifest_sha256"):
        raise ValueError("Restored plaintext bundle differs from encrypted source")
    with ZipFile(io.BytesIO(plaintext)) as z:
        names = set(z.namelist())
        if names != {"manifest.json", "stage3-original-evidence.zip", "orphan-original-evidence.zip"}:
            raise ValueError("Restored encrypted bundle missing required evidence")
        manifest = json.loads(z.read("manifest.json"))
        stage3 = z.read("stage3-original-evidence.zip")
        orphan = z.read("orphan-original-evidence.zip")
        if (sha(stage3) != manifest.get("stage3_zip_sha256") or
                sha(orphan) != manifest.get("orphan_zip_sha256") or
                len(stage3) != manifest.get("stage3_zip_size") or
                len(orphan) != manifest.get("orphan_zip_size")):
            raise ValueError("Restored evidence differs from source artifact checksums")
        checks = _validate_artifacts(stage3, orphan)
        if any(manifest.get(k) != v for k,v in checks.items()):
            raise ValueError("Restored inventory report does not match original evidence")
    return {"evidence_restored": True, "archive_sha256": actual_sha,
            "encrypted_aes256_gcm": True, **checks}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command", required=True)
    new=sub.add_parser("create")
    for x in ("stage3", "orphan", "archive", "key-file"):
        new.add_argument('--'+x,required=True)
    read=sub.add_parser("verify")
    for x in ("archive", "key-file", "expected-sha"):
        read.add_argument('--'+x,required=True)
    args=p.parse_args()
    if args.command=="create":
        out=create_archive(args.stage3,args.orphan,args.archive,args.key_file)
    else:
        out=verify_archive(args.archive,args.key_file,args.expected_sha)
    print(json.dumps(out,sort_keys=True))

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Restore the original production archive using a short-lived Drive token."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from production_full_stage5_archive import verify


ATTESTATION = Path(__file__).resolve().parent / "history/stage5-production-acceptance-20261103.json"
AES_SECRET = "V2_PRODUCTION_AES_KEY_METADATA_B64"


def drive_get(file_id, token, params, timeout):
    query = urlencode({"supportsAllDrives": "true", **params})
    request = Request(f"https://www.googleapis.com/drive/v3/files/{file_id}?{query}")
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    try:
        return urlopen(request, timeout=timeout)
    except HTTPError as exc:
        exc.close()
        raise RuntimeError(f"Google Drive API returned HTTP {exc.code}") from None
    except URLError:
        raise RuntimeError("Could not reach the Google Drive API") from None


def drive_metadata(file_id, token, expected_size):
    fields = {"fields": "id,mimeType,size,version,trashed"}
    with drive_get(file_id, token, fields, timeout=60) as response:
        info = json.load(response)
    if (info.get("id") != file_id or info.get("trashed") is not False
            or info.get("mimeType") != "application/octet-stream"
            or str(info.get("size")) != str(expected_size)
            or not re.fullmatch(r"[1-9][0-9]*", str(info.get("version")))):
        raise RuntimeError("Google Drive archive identity, size or revision could not be verified")
    return info


def download_archive(file_id, token, destination, expected_size, expected_sha256):
    digest = hashlib.sha256()
    size = 0
    with drive_get(file_id, token, {"alt": "media"}, timeout=120) as response:
        with destination.open("xb") as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > expected_size:
                    raise RuntimeError("Google Drive download exceeded the pinned archive size")
                digest.update(chunk)
                output.write(chunk)
    if size != expected_size or digest.hexdigest() != expected_sha256:
        raise RuntimeError("Google Drive archive size or SHA-256 differs from the original")


def restore_drive():
    token = os.environ.get("V2_DRIVE_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("GitHub OIDC did not provide a Google Drive access token")
    attestation = json.loads(ATTESTATION.read_text(encoding="utf-8"))
    file_id = attestation["independent_second_backup_file_id"]
    expected_size = attestation["archive_bytes"]
    expected_sha256 = attestation["archive_sha256"]
    if (not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", file_id)
            or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
            or not 0 < expected_size <= 1024**3):
        raise ValueError("Invalid pinned Google Drive archive metadata")

    initial = drive_metadata(file_id, token, expected_size)
    with tempfile.TemporaryDirectory(prefix="v2-drive-restore-") as directory:
        archive = Path(directory) / "archive.enc"
        download_archive(file_id, token, archive, expected_size, expected_sha256)
        if drive_metadata(file_id, token, expected_size) != initial:
            raise RuntimeError("Google Drive archive changed during retrieval")
        print("PASS: Google Drive archive ID, version, size and SHA-256 verified", flush=True)

        encoded_key = os.environ.get(AES_SECRET)
        if not encoded_key:
            raise RuntimeError(f"Missing original AES archive metadata secret {AES_SECRET}")
        try:
            key_metadata = base64.b64decode(encoded_key, validate=True)
        except ValueError:
            raise RuntimeError(f"Invalid base64 encoding for {AES_SECRET}") from None
        with tempfile.NamedTemporaryFile(dir=directory) as key_file:
            key_file.write(key_metadata)
            key_file.flush()
            result = verify(archive, key_file.name, expected_sha256)
    print(f"PASS: original AES-256-GCM restored {result['historical_original_urls']} historical "
          f"and {result['orphan_original_urls']} orphan records with source provenance")


if __name__ == "__main__":
    restore_drive()

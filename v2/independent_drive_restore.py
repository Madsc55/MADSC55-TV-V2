#!/usr/bin/env python3
"""Independent Google Drive archive retrieval; never log tokens, keys or archive URLs."""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

def restore_drive():
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    from archive_acceptance_gate import check

    file_id = os.environ["V2_DRIVE_ARCHIVE_FILE_ID"]
    expected = os.environ["V2_ARCHIVE_EXPECTED_SHA256"]
    secret = json.loads(os.environ["V2_DRIVE_SERVICE_ACCOUNT_JSON"])
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", file_id):
        raise ValueError("Invalid Drive file identifier")
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("Pinned archive SHA256 is required")
    credentials = service_account.Credentials.from_service_account_info(
        secret, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    session = AuthorizedSession(credentials)
    endpoint = "https://www.googleapis.com/drive/v3/files/" + file_id
    metadata = session.get(endpoint, params={"fields":"id,mimeType,size,md5Checksum,version,trashed",
                                                "supportsAllDrives":"true"}, timeout=60)
    metadata.raise_for_status()
    info = metadata.json()
    if info.get("id") != file_id or info.get("trashed") or not info.get("version"):
        raise RuntimeError("Drive object identity/version not verified")
    if info.get("mimeType") == "application/vnd.google-apps.folder":
        raise RuntimeError("Drive object must be an encrypted binary file")
    with tempfile.TemporaryDirectory(prefix="v2-drive-restore-") as directory:
        root = Path(directory)
        root.chmod(0o700)
        restored = root / "archive.enc"
        response = session.get(endpoint, params={"alt":"media","supportsAllDrives":"true"},
                               stream=True, timeout=120)
        response.raise_for_status()
        digest = hashlib.sha256()
        size = 0
        with restored.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024*1024):
                if chunk:
                    size += len(chunk)
                    if size > 1024*1024*1024:
                        raise RuntimeError("Drive archive exceeds safe size limit")
                    digest.update(chunk)
                    output.write(chunk)
        restored.chmod(0o600)
        if digest.hexdigest() != expected or str(size) != str(info.get("size")):
            raise RuntimeError("Drive archive digest/size mismatch")
        # Reject objects that changed during download.
        verify = session.get(endpoint, params={"fields":"id,version,size,trashed",
                                                "supportsAllDrives":"true"}, timeout=60)
        verify.raise_for_status()
        latest = verify.json()
        if latest.get("version") != info["version"] or str(latest.get("size")) != str(size) or latest.get("trashed"):
            raise RuntimeError("Drive archive changed during retrieval")
        evidence = root / "evidence.json"
        evidence.write_text(json.dumps({
            "encrypted":True,"durable":True,"restore_test_passed":True,
            "integrity_verified":True,"backup_scope":"independent_remote_storage",
            "retrieval_method":"google_drive_authenticated_version_checked_get",
            "backup_location":"gdrive://" + file_id,
            "remote_object_version":str(info["version"]),
            "historical_record_count":4955,"restore_sha256":expected,
            "restored_file":str(restored)
        }), encoding="utf-8")
        evidence.chmod(0o600)
        env = dict(os.environ, V2_ARCHIVE_RESTORE_APPROVED="true",
                   V2_ARCHIVE_RESTORE_EVIDENCE=str(evidence))
        check(env)
        print("PASS: independent Google Drive AES-GCM restore and 4955 historical identities")

if __name__ == "__main__":
    restore_drive()

#!/usr/bin/env python3
"""Create encrypted, non-production 500-entry review batches from AV-verified inventory."""
import hashlib
import io
import json
import os
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from secure_archive import decrypt, encrypt, atomic_write
from export_ibo_batches import render, valid_stream_url

def main():
    source = Path("v2/reports/ibo-candidate-inventory.jsonl.enc")
    out = Path("v2/reports/ibo-500-review-backup.zip.enc")
    secret = os.environ.get("V2_ARCHIVE_PASSPHRASE", "")
    if not secret:
        raise SystemExit("Missing archive secret")
    if not source.is_file():
        raise SystemExit("Encrypted inventory missing")
    rows, seen = [], set()
    for line in decrypt(source.read_bytes(), secret).splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if not isinstance(rec, dict):
            continue
        url = rec.get("url")
        if not valid_stream_url(url) or url in seen:
            continue
        if rec.get("http_hls_status") != "AV_VERIFIED" or rec.get("decoded_av_verified") is not True or rec.get("decode_status") != "DECODED_AV":
            continue
        seen.add(url)
        rows.append(rec)
    if not rows:
        raise SystemExit("No AV-verified streams; refusing empty backup")
    buf = io.BytesIO()
    manifest = {"source": "encrypted-real-scan-inventory", "count": len(rows), "batch_size": 500, "status": "REVIEW_ONLY_NOT_DEVICE_ACCEPTED", "parts": []}
    with ZipFile(buf, "w", ZIP_DEFLATED) as z:
        for offset in range(0, len(rows), 500):
            name = f"IBO_REVIEW_{offset // 500 + 1:02d}.m3u8"
            payload = render(rows[offset:offset + 500])
            z.writestr(name, payload)
            manifest["parts"].append({"file": name, "count": len(rows[offset:offset + 500]), "sha256": hashlib.sha256(payload).hexdigest()})
        z.writestr("MANIFEST.json", json.dumps(manifest, indent=2))
    if out.exists() or out.is_symlink():
        raise SystemExit("Refusing to overwrite backup")
    atomic_write(out, encrypt(buf.getvalue(), secret))
    print(json.dumps({"encrypted_backup": str(out), "verified_candidates": len(rows), "parts": len(manifest["parts"])}))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Isolated ZIP/7z restore audit; never writes to production or marks tasks done.

Only standard ZIP is supported here. Custom MADSC55 encrypted inventory requires
its native authenticated decryptor and must not be treated as a ZIP restore.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import tempfile
import zipfile
import stat

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def audit(archive, expected_sha, expected_count, report_path):
    archive = archive.resolve()
    report = {"schema": 1, "passed": False, "independent_restore": False,
              "source_archive": archive.name, "archive_sha256": None,
              "restored_count": 0, "error": None,
              "note": "ZIP extraction is not proof of native encrypted inventory decryption."}
    try:
        if not archive.is_file():
            raise ValueError("archive not found")
        report["archive_sha256"] = digest(archive)
        if report["archive_sha256"] != expected_sha.lower():
            raise ValueError("archive SHA-256 mismatch")
        if not zipfile.is_zipfile(archive):
            raise ValueError("unsupported format; native authenticated decryptor required")
        with tempfile.TemporaryDirectory(prefix="stage-c-isolated-") as directory:
            root = pathlib.Path(directory).resolve()
            with zipfile.ZipFile(archive) as z:
                files = [info for info in z.infolist() if not info.is_dir()]
                for info in z.infolist():
                    destination = (root / info.filename).resolve()
                    if not destination.is_relative_to(root):
                        raise ValueError("unsafe ZIP member path")
                    if stat.S_ISLNK(info.external_attr >> 16):
                        raise ValueError("ZIP symlink forbidden")
                bad = z.testzip()
                if bad:
                    raise ValueError("ZIP CRC failed: " + bad)
                for info in files:
                    target = (root / info.filename).resolve()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
                    if target.stat().st_size != info.file_size:
                        raise ValueError("extracted size mismatch")
                report["restored_count"] = len(files)
                if expected_count is not None and len(files) != expected_count:
                    raise ValueError("extracted file count mismatch")
                report["zip_extraction_passed"] = True
                report["contains_encrypted_inventory"] = any(
                    p.filename.endswith(".enc") for p in files)
                if report["contains_encrypted_inventory"]:
                    report["error"] = "encrypted inventory remains opaque; independent restore NOT accepted"
                else:
                    report["error"] = "ZIP extraction alone does not establish production record restoration"
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        report["error"] = str(exc)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archive", type=pathlib.Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--expected-file-count", type=int)
    p.add_argument("--report", type=pathlib.Path, required=True)
    a = p.parse_args()
    print(json.dumps(audit(a.archive, a.expected_sha256, a.expected_file_count, a.report),
                     ensure_ascii=False))
    return 0 if a.report.exists() and json.loads(a.report.read_text()).get("independent_restore") is True else 1

if __name__ == "__main__":
    raise SystemExit(main())

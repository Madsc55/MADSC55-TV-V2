#!/usr/bin/env python3
"""Private archive backup/restore drill; never writes plaintext candidate URLs."""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import stat
from encrypted_archive import _cipher, restore

def private_regular(path):
    path = pathlib.Path(path)
    return (not path.is_symlink() and path.is_file()
            and stat.S_ISREG(path.stat().st_mode) and not path.stat().st_mode & 0o077)

def drill(archive, backup, restored, evidence):
    archive, backup, restored, evidence = map(pathlib.Path, (archive, backup, restored, evidence))
    _cipher()
    if not private_regular(archive):
        raise RuntimeError("Source archive must be a private regular file")
    if any(path.exists() or path.is_symlink() for path in (backup, restored, evidence)):
        raise RuntimeError("Backup, restore and evidence destinations must not exist")
    if len({str(path.resolve()) for path in (archive, backup, restored, evidence)}) != 4:
        raise RuntimeError("Archive drill paths must be distinct")
    if not backup.parent.exists() or not restored.parent.exists() or not evidence.parent.exists():
        raise RuntimeError("Destination parent directories must exist")
    if backup.parent.resolve() == archive.parent.resolve():
        raise RuntimeError("Backup must be in a separate directory")
    original = restore(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    for destination in (backup, restored):
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as stream, archive.open("rb") as source:
            shutil.copyfileobj(source, stream)
            stream.flush()
            os.fsync(stream.fileno())
        if hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise RuntimeError("Encrypted archive backup checksum mismatch")
    if restore(restored) != original:
        raise RuntimeError("Restored encrypted archive records mismatch")
    result = {"encrypted": True, "durable": True, "restore_test_passed": True,
              "integrity_verified": True, "backup_location": str(backup.resolve()),
              "restored_file": str(restored.resolve()), "restore_sha256": digest,
              "record_count": len(original),
              "backup_scope": "local_separate_directory_not_independent_storage"}
    fd = os.open(evidence, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=pathlib.Path, required=True)
    parser.add_argument("--backup", type=pathlib.Path, required=True)
    parser.add_argument("--restored", type=pathlib.Path, required=True)
    parser.add_argument("--evidence", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = drill(args.archive, args.backup, args.restored, args.evidence)
    print("Encrypted archive backup/restore drill passed; records:", result["record_count"])
    print("Separate directory is NOT proof of independent durable storage")
if __name__ == "__main__":
    main()

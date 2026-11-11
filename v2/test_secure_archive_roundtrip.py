#!/usr/bin/env python3
"""Offline archive safety regression: no network, no playlist modification."""
import hashlib
import os
import tempfile
from pathlib import Path
from secure_archive import backup, restore, decrypt, encrypt

def main():
    secret = "offline-fixture-passphrase-only"
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        original = root / "source.jsonl"
        payload = b'{"url":"https://example.org/offline-fixture.m3u8"}\n'
        original.write_bytes(payload)
        encrypted = root / "private.enc"
        report = backup(original, encrypted, secret)
        assert report["restore_test_passed"]
        assert report["restored_sha256"] == hashlib.sha256(payload).hexdigest()
        assert encrypted.read_bytes() != payload
        assert decrypt(encrypted.read_bytes(), secret) == payload
        recovered = root / "restored.jsonl"
        assert restore(encrypted, recovered, secret) == hashlib.sha256(payload).hexdigest()
        assert recovered.read_bytes() == payload
        damaged = bytearray(encrypted.read_bytes())
        damaged[-1] ^= 1
        bad = root / "bad.enc"
        bad.write_bytes(damaged)
        destination = root / "must-not-exist.jsonl"
        try:
            restore(bad, destination, secret)
        except Exception:
            pass
        else:
            raise AssertionError("Corrupt archive was accepted")
        assert not destination.exists()
        try:
            decrypt(encrypted.read_bytes(), "incorrect-passphrase-long-enough")
        except Exception:
            pass
        else:
            raise AssertionError("Incorrect passphrase was accepted")
    print("PASS: encrypted backup, disk restore, tamper and wrong-key rejection")

if __name__ == "__main__":
    main()

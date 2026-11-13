#!/usr/bin/env python3
"""Offline archive safety regression: no network, no playlist modification."""
import hashlib
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import secure_archive
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
        # Reject malformed API input types before cryptographic processing.
        for value in ("text", bytearray(b"data"), None):
            for operation in (encrypt, decrypt):
                try:
                    operation(value, secret)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Non-byte encryption input accepted")
        # A passphrase consisting only of whitespace must not encrypt data.
        for weak_secret in (" " * 16, "\t" * 20, "\n" * 20):
            try:
                encrypt(payload, weak_secret)
            except ValueError:
                pass
            else:
                raise AssertionError("Whitespace-only archive passphrase accepted")
        # Direct API calls must not overwrite their own input.
        for operation in (backup, restore):
            try:
                operation(encrypted, encrypted, secret)
            except ValueError:
                pass
            else:
                raise AssertionError("Same-path archive operation accepted")
        assert decrypt(encrypted.read_bytes(), secret) == payload
        # Reject oversized encrypted input before loading it into memory.
        with patch.object(secure_archive, "MAX_INPUT", 1):
            try:
                decrypt(encrypted.read_bytes(), secret)
            except ValueError:
                pass
            else:
                raise AssertionError("Oversized encrypted blob accepted")
            try:
                restore(encrypted, root / "oversized-restored.jsonl", secret)
            except ValueError:
                pass
            else:
                raise AssertionError("Oversized archive restore accepted")
        assert not (root / "oversized-restored.jsonl").exists()
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

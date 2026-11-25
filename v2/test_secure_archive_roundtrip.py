#!/usr/bin/env python3
"""Offline archive safety regression: no network, no playlist modification."""
import hashlib
import os
import secrets
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
import secure_archive
from cryptography.fernet import Fernet
from turk_authorized_vault import Vault
from secure_archive import backup, restore, decrypt, encrypt

def test_independent_ephemeral_restore():
    # Separate producer and recovery directories; never touch repository data.
    secret = secrets.token_urlsafe(32)
    payload = b'{"fixture":"independent AES-256-GCM restore"}\n'
    expected = hashlib.sha256(payload).hexdigest()
    with tempfile.TemporaryDirectory(prefix="v2-recovery-") as recovery:
        recovery = Path(recovery)
        with tempfile.TemporaryDirectory(prefix="v2-producer-") as producer:
            producer = Path(producer)
            source = producer / "fixture.json"
            source.write_bytes(payload)
            encrypted = producer / "fixture.enc"
            receipt = backup(source, encrypted, secret)
            copy = recovery / "retrieved.enc"
            shutil.copyfile(encrypted, copy)
            copy.chmod(0o600)
            assert hashlib.sha256(copy.read_bytes()).hexdigest() == receipt["archive_sha256"]
        assert not producer.exists()
        recovered = recovery / "restored.json"
        assert restore(copy, recovered, secret) == expected
        assert hashlib.sha256(recovered.read_bytes()).hexdigest() == expected
        assert recovered.read_bytes() == payload
        assert recovered.stat().st_mode & 0o777 == 0o600
        damaged = recovery / "damaged.enc"
        blob = bytearray(copy.read_bytes())
        blob[-1] ^= 1
        damaged.write_bytes(blob)
        from cryptography.exceptions import InvalidTag
        for bad_source, bad_key in ((damaged, secret), (copy, secrets.token_urlsafe(32))):
            target = recovery / "rejected.json"
            try:
                restore(bad_source, target, bad_key)
            except InvalidTag:
                pass
            else:
                raise AssertionError("Invalid archive accepted")
            assert not target.exists()
    print("PASS: independent ephemeral AES-256-GCM restore and SHA-256 parity")


def main():
    test_independent_ephemeral_restore()
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
        # Existing destinations must never be replaced by backup or restore.
        for operation, source in ((backup, original), (restore, encrypted)):
            protected = root / ("protected-backup.enc" if operation is backup else "protected-restore.jsonl")
            protected.write_bytes(b"DO_NOT_OVERWRITE")
            try:
                operation(source, protected, secret)
            except FileExistsError:
                pass
            else:
                raise AssertionError("Existing archive destination was overwritten")
            assert protected.read_bytes() == b"DO_NOT_OVERWRITE"
        # Symlink destinations must also be refused without changing their targets.
        symlink_target = root / "protected-target.bin"
        symlink_target.write_bytes(b"SYMLINK_TARGET_UNCHANGED")
        for operation, source in ((backup, original), (restore, encrypted)):
            link = root / ("backup-link.enc" if operation is backup else "restore-link.jsonl")
            link.symlink_to(symlink_target)
            try:
                operation(source, link, secret)
            except FileExistsError:
                pass
            else:
                raise AssertionError("Symlink destination was overwritten")
            assert link.is_symlink()
            assert symlink_target.read_bytes() == b"SYMLINK_TARGET_UNCHANGED"
        # The low-level atomic writer must also fail closed for files and symlinks.
        direct_target = root / "direct-existing.bin"
        direct_target.write_bytes(b"KEEP")
        try:
            secure_archive.atomic_write(direct_target, b"REPLACE")
        except FileExistsError:
            pass
        else:
            raise AssertionError("atomic_write replaced an existing file")
        assert direct_target.read_bytes() == b"KEEP"
        symlink_target = root / "symlink-target.bin"
        symlink_target.write_bytes(b"TARGET-KEEP")
        symlink_path = root / "existing-link.bin"
        symlink_path.symlink_to(symlink_target)
        try:
            secure_archive.atomic_write(symlink_path, b"SYMLINK-REPLACE")
        except FileExistsError:
            pass
        else:
            raise AssertionError("atomic_write replaced an existing symlink")
        assert symlink_path.is_symlink()
        assert symlink_target.read_bytes() == b"TARGET-KEEP"
        # Even if a source is swapped after path validation, never follow the link.
        for operation, data, suffix in ((backup, payload, "jsonl"),
                                        (restore, encrypted.read_bytes(), "enc")):
            source = root / ("swap-source." + suffix)
            source.write_bytes(data)
            target = root / ("swap-target." + suffix)
            target.write_bytes(data)
            output = root / ("swap-output-" + suffix)
            original_validate = secure_archive._validate_paths
            def swap_after_validation(src, dst):
                original_validate(src, dst)
                src.unlink()
                src.symlink_to(target)
            with patch.object(secure_archive, "_validate_paths", side_effect=swap_after_validation):
                try:
                    operation(source, output, secret)
                except OSError:
                    pass
                else:
                    raise AssertionError("Archive followed a source swapped to symlink")
            assert not output.exists()
            assert target.read_bytes() == data
        # Bound the actual read even if the pre-read stat underreports the file.
        with patch.object(secure_archive, "MAX_INPUT", 1):
            try:
                secure_archive._read_regular_bounded(original, 1)
            except ValueError:
                pass
            else:
                raise AssertionError("Oversized source read accepted")
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
    # End-to-end integration of the existing secure archive with the Turkish-only vault.
    # This exercises the production backup/restore API, without real streams or network.
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        key = Fernet.generate_key()
        vault = Vault(root / "authorized-tr.enc", key)
        vault.add("TR-001", "https://example.org/tr.m3u8?token=private",
                  "licensed offline fixture", True, True)
        original = vault.read()
        outer = root / "private-backup.enc"
        backup_report = backup(vault.path, outer, secret)
        assert backup_report["restore_test_passed"]
        recovered_ciphertext = root / "restored-vault.enc"
        assert restore(outer, recovered_ciphertext, secret) == hashlib.sha256(vault.path.read_bytes()).hexdigest()
        restored_vault = Vault(recovered_ciphertext, key)
        assert restored_vault.read() == original
        assert "private" not in str(restored_vault.public_report())
        try:
            restored_vault.add("FOREIGN", "https://example.org/foreign.m3u8",
                               "offline fixture", True, False)
        except ValueError:
            pass
        else:
            raise AssertionError("Foreign stream accepted after secure archive restore")
        assert restored_vault.read() == original
    print("PASS: encrypted backup, disk restore, tamper and wrong-key rejection")

if __name__ == "__main__":
    main()

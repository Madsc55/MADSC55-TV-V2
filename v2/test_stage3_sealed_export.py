#!/usr/bin/env python3
"""Grouped confidential recovery transport tests (synthetic URLs only)."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from stage3_sealed_export import open_rows, seal_rows


class SealedRecoveryTests(unittest.TestCase):
    def test_full_encrypted_transport_and_tamper_rejection(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        url = "https://fixture.example.org/test.m3u8?token=SECRET_TEST_ONLY"
        rows = [{"url": url, "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                 "source": "fixture"}]
        with tempfile.TemporaryDirectory() as directory:
            pub = Path(directory) / "pub.pem"
            priv = Path(directory) / "priv.pem"
            sealed = Path(directory) / "private.sealed"
            pub.write_bytes(key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            priv.write_bytes(key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()))
            self.assertEqual(seal_rows(rows, pub, sealed), 1)
            self.assertNotIn(url, sealed.read_text(encoding="utf-8"))
            self.assertEqual(open_rows(sealed, priv), rows)
            with self.assertRaises(ValueError):
                seal_rows(rows, pub, sealed)
            tampered = [dict(rows[0], url_sha256="0" * 64)]
            with self.assertRaisesRegex(ValueError, "SHA256"):
                seal_rows(tampered, pub, Path(directory) / "bad.sealed")

    def test_empty_sealed_evidence_is_valid_and_confidential(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        with tempfile.TemporaryDirectory() as directory:
            pub, priv, sealed = (Path(directory) / p for p in
                                 ("p.pem", "s.pem", "empty.sealed"))
            pub.write_bytes(key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
            priv.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
            self.assertEqual(seal_rows([], pub, sealed), 0)
            self.assertEqual(open_rows(sealed, priv), [])


if __name__ == "__main__":
    unittest.main()

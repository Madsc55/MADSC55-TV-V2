import unittest
from ibo_final_acceptance import audit_archive,audit_encrypted_archive,audit_external_restore,final_gate
from secure_archive import encrypt
class AcceptanceTests(unittest.TestCase):
    def test_archive_roundtrip(self):
        self.assertEqual(audit_archive(b"ciphertext",b"ciphertext")["status"],"ROUNDTRIP_BYTES_MATCH")
        with self.assertRaises(ValueError): audit_archive(b"a",b"b")
    def test_rejects_non_byte_archive_inputs(self):
        for original, restored in (("same", "same"), (bytearray(b"same"), b"same"),
                                   (b"same", memoryview(b"same")), (None, b"same")):
            with self.subTest(original=type(original).__name__, restored=type(restored).__name__), self.assertRaises(ValueError):
                audit_archive(original, restored)

    def test_authenticated_archive(self):
        raw=b'private test inventory'
        cipher=encrypt(raw,'offline-test-passphrase-2026')
        result=audit_encrypted_archive(raw,cipher,'offline-test-passphrase-2026')
        self.assertTrue(result['encrypted'])
        self.assertFalse(result['external_restore_verified'])
        with self.assertRaises(Exception):
            audit_encrypted_archive(raw,cipher,'wrong-test-passphrase-2026')
        with self.assertRaises(ValueError):
            audit_encrypted_archive(raw,raw,'offline-test-passphrase-2026')
    def test_independent_encrypted_restore_evidence(self):
        raw=b"production-like offline archive fixture"
        cipher=encrypt(raw, "offline-test-passphrase-2026")
        report=audit_external_restore(raw, cipher, raw, "offline-test-passphrase-2026")
        self.assertTrue(report["encrypted"])
        self.assertTrue(report["external_restore_verified"])
        self.assertEqual(report["sha256"], __import__("hashlib").sha256(raw).hexdigest())
        with self.assertRaises(ValueError):
            audit_external_restore(raw, cipher, b"different restored bytes", "offline-test-passphrase-2026")
        with self.assertRaises(ValueError):
            audit_external_restore(raw, raw, raw, "offline-test-passphrase-2026")

    def test_rejects_non_byte_encrypted_archive_inputs(self):
        for original, ciphertext in (("raw", b"encrypted"), (b"raw", "encrypted"),
                                     (bytearray(b"raw"), b"encrypted"), (b"raw", None)):
            with self.subTest(original=type(original).__name__, ciphertext=type(ciphertext).__name__), self.assertRaises(ValueError):
                audit_encrypted_archive(original, ciphertext, "offline-test-passphrase-2026")

    def test_invalid_final_reports_fail_closed(self):
        valid={"target":1000,"records":1000,"sha256":"a"*64,"status":"EVIDENCE_GATED"}
        archive={"status":"ROUNDTRIP_BYTES_MATCH","sha256":"a"*64,"bytes":128,"external_restore_verified":True}
        for report in (None, [], "EVIDENCE_GATED",
                       dict(valid, sha256="abc"),
                       dict(valid, sha256="z"*64),
                       dict(valid, target=True),
                       dict(valid, records=True)):
            with self.subTest(report=report), self.assertRaises(ValueError):
                final_gate(report, archive, True, True)
        with self.assertRaises(ValueError):
            final_gate(valid, None, True, True)

        for bad_archive in ({"status":"ROUNDTRIP_BYTES_MATCH"},
                            dict(archive, sha256="invalid"),
                            dict(archive, bytes=0),
                            dict(archive, bytes=True),
                            dict(archive, bytes=-1)):
            with self.subTest(archive=bad_archive), self.assertRaises(ValueError):
                final_gate(valid, bad_archive, True, True)
    def test_rejects_archive_from_different_package(self):
        package={"target":1000,"records":1000,"sha256":"a"*64,"status":"EVIDENCE_GATED"}
        archive={"status":"ROUNDTRIP_BYTES_MATCH","sha256":"b"*64,"bytes":128,"external_restore_verified":True}
        with self.assertRaisesRegex(ValueError, "do not match"):
            final_gate(package, archive, True, True)

    def test_rejects_non_boolean_acceptance_flags(self):
        p={"target":1000,"records":1000,"sha256":"a"*64,"status":"EVIDENCE_GATED"}
        a={"status":"ROUNDTRIP_BYTES_MATCH","sha256":"a"*64,"bytes":128,"external_restore_verified":True}
        for restore, av in (("false", True), (True, "false"), (1, True), (True, 0), (None, True)):
            with self.subTest(restore=restore, av=av), self.assertRaises(ValueError):
                final_gate(p, a, restore, av)

    def test_rejects_plaintext_archive_for_production_review(self):
        p={"target":1000,"records":1000,"sha256":"a"*64,"status":"EVIDENCE_GATED"}
        a={"status":"ROUNDTRIP_BYTES_MATCH","sha256":"a"*64,"bytes":128,"external_restore_verified":True}
        for encrypted in (None, False, "true", 1):
            with self.subTest(encrypted=encrypted), self.assertRaises(ValueError):
                final_gate(p, dict(a, encrypted=encrypted), True, True)

    def test_rejects_unverified_independent_restore(self):
        p={"target":1000,"records":1000,"sha256":"a"*64,"status":"EVIDENCE_GATED"}
        a={"status":"ROUNDTRIP_BYTES_MATCH","sha256":"a"*64,"bytes":128,"encrypted":True}
        for flag in (None, False, "true", 1):
            with self.subTest(flag=flag), self.assertRaisesRegex(ValueError, "external restore"):
                final_gate(p, dict(a, external_restore_verified=flag), True, True)
        self.assertFalse(final_gate(p, dict(a, external_restore_verified=True), True, True)["production_accepted"])

    def test_no_false_production_acceptance(self):
        p={"target":1000,"records":1000,"sha256":"a"*64,"status":"EVIDENCE_GATED"}
        a={"status":"ROUNDTRIP_BYTES_MATCH","sha256":"a"*64,"bytes":128,"external_restore_verified":True}
        self.assertFalse(final_gate(p,a)["production_accepted"])
        with self.assertRaisesRegex(ValueError, "encrypted archive"):
            final_gate(p,a,True,True)
        self.assertFalse(final_gate(p,dict(a, encrypted=True),True,True)["production_accepted"])
if __name__=="__main__": unittest.main()

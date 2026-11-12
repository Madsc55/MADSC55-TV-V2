import unittest
from ibo_final_acceptance import audit_archive,audit_encrypted_archive,final_gate
from secure_archive import encrypt
class AcceptanceTests(unittest.TestCase):
    def test_archive_roundtrip(self):
        self.assertEqual(audit_archive(b"ciphertext",b"ciphertext")["status"],"ROUNDTRIP_BYTES_MATCH")
        with self.assertRaises(ValueError): audit_archive(b"a",b"b")
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
    def test_no_false_production_acceptance(self):
        p={"target":1000,"records":1000,"sha256":"abc","status":"EVIDENCE_GATED"}
        a={"status":"ROUNDTRIP_BYTES_MATCH"}
        self.assertFalse(final_gate(p,a)["production_accepted"])
        self.assertFalse(final_gate(p,a,True,True)["production_accepted"])
if __name__=="__main__": unittest.main()

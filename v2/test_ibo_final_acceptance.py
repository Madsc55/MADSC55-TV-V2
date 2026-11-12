import unittest
from ibo_final_acceptance import audit_archive,final_gate
class AcceptanceTests(unittest.TestCase):
    def test_archive_roundtrip(self):
        self.assertEqual(audit_archive(b"ciphertext",b"ciphertext")["status"],"ROUNDTRIP_BYTES_MATCH")
        with self.assertRaises(ValueError): audit_archive(b"a",b"b")
    def test_no_false_production_acceptance(self):
        p={"target":1000,"records":1000,"sha256":"abc","status":"EVIDENCE_GATED"}
        a={"status":"ROUNDTRIP_BYTES_MATCH"}
        self.assertFalse(final_gate(p,a)["production_accepted"])
        self.assertFalse(final_gate(p,a,True,True)["production_accepted"])
if __name__=="__main__": unittest.main()

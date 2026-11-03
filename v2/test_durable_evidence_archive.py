#!/usr/bin/env python3
"""Stage-5 grouped offline cryptographic regressions. Fixture envelopes are NOT live streams."""
import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZIP_STORED, ZipFile

from durable_evidence_archive import create_archive, verify_archive, _validate_artifacts

BASELINE = Path(__file__).resolve().parent / "history" / "stage3-4955-hash-only.jsonl"

class DurableEvidenceArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BASELINE.is_file():
            raise unittest.SkipTest("V2 immutable historical identity fixture not mounted")
        cls.rows = [json.loads(line) for line in BASELINE.read_text().splitlines() if line]

    def fixture(self, path, orphan=False, bad=False):
        def sealed(count):
            return json.dumps({"schema":1,"kind":"RSA_OAEP_SHA256_AES256_GCM_ZLIB",
                "records_encrypted":count,"nonce":base64.b64encode(b'N'*12).decode(),
                "wrapped_key":base64.b64encode(b'K'*384).decode(),
                "ciphertext":base64.b64encode(b'C'*24).decode()})
        with ZipFile(path, "w", compression=ZIP_STORED) as z:
            if not orphan:
                rows = self.rows[:(10 if bad else None)]
                z.writestr("stage3-4955-hash-only.jsonl", "\n".join(json.dumps(x) for x in rows)+"\n")
                z.writestr("stage3-combined-real-url-recovery.json", json.dumps({
                    "unique_exact_original_url_matches":len(rows), "still_without_original_url":0,
                    "matched_hashes":[x["url_sha256"] for x in rows]}))
                for n,count in (("stage3-git-history-recovered.sealed",4902),
                    ("stage3-original-github-recovered.sealed",2844),
                    ("stage3-original-configured-recovered.sealed",2075),
                    ("stage3-dearbulut-health-recovered.sealed",1861)):
                    z.writestr(n,sealed(count))
            else:
                z.writestr("three-source-orphan-anonymous.json",json.dumps({
                    "orphan_entries":55, "unique_orphan_metadata_identities":50,
                    "all_proven_url_candidates_sealed_for_future_retest":107,
                    "unique_candidates_video_audio_verified":4}))
                z.writestr("three-source-all-historical-candidates.sealed",sealed(107))
                z.writestr("three-source-av-verified.sealed",sealed(4))

    def test_encrypted_backup_roundtrip_and_lossless_identity_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); first=r/'stage3.zip'; second=r/'orphan.zip'; archive=r/'archive.enc'; key=r/'private.json'
            self.fixture(first);self.fixture(second,orphan=True)
            result = create_archive(first,second,archive,key)
            self.assertEqual(result["historical_identity_count"],4955)
            self.assertTrue(verify_archive(archive,key,expected_sha=result["sha256"])["evidence_restored"])
            self.assertNotIn(b"url_sha256",archive.read_bytes())
            self.assertEqual(key.stat().st_mode & 0o077,0)
            self.assertEqual(archive.stat().st_mode & 0o077,0)

    def test_wrong_key_sha_tampering_or_truncation_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); first=r/'stage3.zip'; second=r/'orphan.zip'; archive=r/'archive.enc'; key=r/'private.json'
            self.fixture(first);self.fixture(second,orphan=True)
            result=create_archive(first,second,archive,key)
            with self.assertRaisesRegex(ValueError,"SHA256"):
                verify_archive(archive,key,"a"*64)
            original=archive.read_bytes(); archive.write_bytes(original[:-4]);
            with self.assertRaisesRegex(ValueError,"recovery|match|authentication|SHA256"):
                verify_archive(archive,key)
            archive.write_bytes(original[:-1]+bytes([original[-1]^1]));
            with self.assertRaises(ValueError): verify_archive(archive,key)
            archive.write_bytes(original)
            raw=json.loads(key.read_text()); raw['key_base64']=base64.b64encode(b'X'*32).decode()
            key.write_text(json.dumps(raw))
            with self.assertRaisesRegex(ValueError,"AES-GCM"):
                verify_archive(archive,key)

    def test_rejects_partial_historical_inventory_or_untrusted_rsa_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d); first=r/'stage3.zip'; second=r/'orphan.zip'; self.fixture(first,bad=True); self.fixture(second,orphan=True)
            with self.assertRaisesRegex(ValueError,"4955"):
                _validate_artifacts(first.read_bytes(),second.read_bytes())
            self.fixture(first)
            with ZipFile(second,'w') as z: z.writestr('unsafe', 'placeholder')
            with self.assertRaisesRegex(ValueError,"orphan source"):
                _validate_artifacts(first.read_bytes(),second.read_bytes())

if __name__ == "__main__": unittest.main(verbosity=2)
#!/usr/bin/env python3
"""Grouped Stage5 production archive regression — offline, no private keys in repo."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zlib
from zipfile import ZipFile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from production_real_url_archive import HISTORY_IDENTITY_SHA,private_key_file,open_sealed,SEALED_AAD
from production_full_stage5_archive import orphan_rows_from_reseal,verify

ROOT=Path(__file__).resolve().parent
ATTESTATION=ROOT/'history/stage5-production-acceptance-20261103.json'

class ProductionStage5Tests(unittest.TestCase):
    def test_pinned_actual_historical_baseline_and_true_narrow_scope(self):
        state=json.loads(ATTESTATION.read_text())
        self.assertEqual(state['historical_original_real_url_records'],4955)
        self.assertEqual(state['orphan_historically_proven_real_url_records'],107)
        self.assertEqual(state['historical_original_identity_sha256'],HISTORY_IDENTITY_SHA)
        self.assertTrue(state['private_aes_decryption_from_independent_persistent_storage_completed'])
        self.assertTrue(state['private_rsa_decryption_completed_for_real_4955_and_107'])
        self.assertFalse(state['overall_live_stream_production_accepted'])
        self.assertFalse(state['IBO_player_device_playback_verified'])
        rows=[json.loads(l) for l in (ROOT/'history/stage3-4955-hash-only.jsonl').read_text().splitlines() if l]
        hashes={r['url_sha256'] for r in rows}
        self.assertEqual(len(rows),len(hashes))
        self.assertEqual(len(rows),4955)
        self.assertEqual(hashlib.sha256(''.join(sorted(hashes)).encode()).hexdigest(),HISTORY_IDENTITY_SHA)

    def test_no_plaintext_url_or_private_key_in_git_attestation(self):
        data=ATTESTATION.read_text()
        self.assertNotIn('-----BEGIN PRIVATE KEY-----',data)
        self.assertNotIn('private_secret_base64',data)
        self.assertNotIn('key_base64',data)
        self.assertNotIn('https://',data)
        self.assertNotIn('http://',data)
        self.assertEqual(len(json.loads(data)['archive_sha256']),64)

    def test_real_RSA3072_decrypt_module_with_synthetic_unit_fixture(self):
        key=rsa.generate_private_key(public_exponent=65537,key_size=3072)
        url='https://fixture.invalid/original-channel.m3u8'
        rows=[{'url':url,'url_sha256':hashlib.sha256(url.encode()).hexdigest()}]
        aes=AESGCM.generate_key(bit_length=256)
        nonce=b'N'*12
        plaintext=zlib.compress(json.dumps({'schema':1,'records':rows}).encode())
        ciphertext=AESGCM(aes).encrypt(nonce,plaintext,SEALED_AAD)
        wrapped=key.public_key().encrypt(aes,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
        sealed={'schema':1,'kind':'RSA_OAEP_SHA256_AES256_GCM_ZLIB','records_encrypted':1,
                'nonce':base64.b64encode(nonce).decode(),'wrapped_key':base64.b64encode(wrapped).decode(),
                'ciphertext':base64.b64encode(ciphertext).decode()}
        self.assertEqual(open_sealed(json.dumps(sealed).encode(),key),rows)
        tampered=dict(sealed,ciphertext=base64.b64encode(ciphertext[:-1]+b'Z').decode())
        with self.assertRaises(Exception):open_sealed(json.dumps(tampered).encode(),key)

    def test_owner_only_private_key_guard_and_missing_archive_guard(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'private.key';p.write_text('fixture private data');p.chmod(0o644)
            with self.assertRaises(PermissionError):private_key_file(p)
            p.chmod(0o600);self.assertEqual(private_key_file(p),p)
            with self.assertRaises(ValueError):verify(Path(d)/'missing.enc',p,'f'*64)

if __name__ == '__main__':unittest.main(verbosity=2)
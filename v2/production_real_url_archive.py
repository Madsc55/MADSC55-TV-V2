#!/usr/bin/env python3
"""V2 Stage5: authenticated and restorable REAL 4955-historical-URL archive.

Exact URLs come only from RSA-3072/AES-256-GCM source-provenance envelopes.
Decrypted URLs are kept in RAM and never logged or written as plaintext files.
This is historical archiving, NOT a claim of current audio/video or IBO playback.
"""
import base64
import hashlib
import io
import json
import os
import secrets
import stat
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_STORED
import zlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC=b"MADSC55-TV-V2-REAL-HISTORY-URL-ARCHIVE-v1\n"
AAD=b"MADSC55-TV-V2-REAL-4955-HISTORICAL-URL-AESGCM-v1"
SEALED_AAD=b"MADSC55-TV-V2-STAGE3-RECOVERED-URL-TRANSIT-v1"
HISTORY_IDENTITY_SHA="e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83"
MAX_ENCRYPTED_SIZE=40_000_000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def private_key_file(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_mode & 0o077:
        raise PermissionError("Recovery key must be private regular non-symlink file")
    return p


def open_sealed(data, private):
    env=json.loads(data)
    if env.get('kind')!='RSA_OAEP_SHA256_AES256_GCM_ZLIB' or env.get('schema')!=1:
        raise ValueError('Unsupported historical URL envelope')
    aes=private.decrypt(base64.b64decode(env['wrapped_key'],validate=True),
      padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    raw=AESGCM(aes).decrypt(base64.b64decode(env['nonce'],validate=True),
      base64.b64decode(env['ciphertext'],validate=True),SEALED_AAD)
    rows=json.loads(zlib.decompress(raw))['records']
    if len(rows)!=env.get('records_encrypted'):
        raise ValueError('Sealed row count differs')
    return rows


def match_original_history(stage3_bytes, resealed_bytes, rsa_private_path):
    private_path=private_key_file(rsa_private_path)
    rsa_key=serialization.load_pem_private_key(private_path.read_bytes(),password=None)
    if not isinstance(rsa_key,rsa.RSAPrivateKey) or rsa_key.key_size < 3072:
        raise ValueError('RSA-3072 private key required')
    with ZipFile(io.BytesIO(stage3_bytes)) as original:
        history=[json.loads(l) for l in original.read('stage3-4955-hash-only.jsonl').splitlines() if l]
        recovered_report=json.loads(original.read('stage3-combined-real-url-recovery.json'))
    baseline={r['url_sha256']:r for r in history}
    if len(history)!=4955 or len(baseline)!=4955 or digest(''.join(sorted(baseline)).encode())!=HISTORY_IDENTITY_SHA:
        raise ValueError('Immutable original #60 baseline changed')
    if set(recovered_report['matched_hashes'])!=set(baseline):
        raise ValueError('Original historical provenance coverage changed')
    by_hash={}
    evidence={}
    with ZipFile(io.BytesIO(resealed_bytes)) as source:
        sealed_names=[x for x in source.namelist() if x.endswith('.sealed')]
        if len(sealed_names)!=4:
            raise ValueError('Exactly four independent original recovery sources required')
        for file in sealed_names:
            rows=open_sealed(source.read(file),rsa_key)
            if not rows:
                raise ValueError('Empty real historical URL source group')
            seen=set()
            for row in rows:
                url=row.get('url'); sha=row.get('url_sha256')
                if not isinstance(url,str) or digest(url.encode('utf-8'))!=sha:
                    raise ValueError('Original URL identity SHA-256 mismatch')
                if sha not in baseline or sha in seen:
                    raise ValueError('Invented or duplicated exact original source URL')
                seen.add(sha)
                if sha in by_hash and by_hash[sha]!=url:
                    raise ValueError('Conflicting plaintext URLs for historical SHA identity')
                by_hash[sha]=url
                evidence.setdefault(sha,[]).append(file)
        union=json.loads(source.read('stage5-historical-union.json'))
        if union.get('recovered_RSA_sealed_original_hashes')!=4955:
            raise ValueError('Historical RSA reseal coverage was not complete')
    if len(by_hash)!=4955 or set(by_hash)!=set(baseline):
        raise ValueError('Real original URLs missing from all four source groups')
    return [{**baseline[sha], 'url':by_hash[sha], 'evidence_sources':sorted(evidence[sha])}
             for sha in sorted(baseline)]


def make(stage3,orphan,resealed,rsa_private,out_file,aes_key_file):
    out_file,aes_key_file=Path(out_file),Path(aes_key_file)
    if any(p.exists() or p.is_symlink() for p in (out_file,aes_key_file)):
        raise FileExistsError('Never overwrite previous encrypted archive or private key')
    stage3_bytes,orphan_bytes,resealed_bytes=[Path(p).read_bytes() for p in (stage3,orphan,resealed)]
    rows=match_original_history(stage3_bytes,resealed_bytes,rsa_private)
    with ZipFile(io.BytesIO(orphan_bytes)) as other:
        orphan_manifest=json.loads(other.read('three-source-orphan-anonymous.json'))
    if orphan_manifest.get('unique_orphan_metadata_identities')!=50 or orphan_manifest.get('all_proven_url_candidates_sealed_for_future_retest')!=107:
        raise ValueError('Orphan history cannot be dropped from production archive')
    real_jsonl=''.join(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for row in rows).encode('utf-8')
    manifest={'schema':1,'project':'MADSC55-TV-V2','historical_original_real_url_count':4955,
              'immutable_historical_sha256':HISTORY_IDENTITY_SHA,'all_4955_source_URLs_private_RSA_decrypted':True,
              'real_url_rows_sha256':digest(real_jsonl),
              'source_stage3_zip_sha256':digest(stage3_bytes),'source_orphan_zip_sha256':digest(orphan_bytes),
              'source_new_RSA_zip_sha256':digest(resealed_bytes),
              'orphan_sealed_url_candidates':107,'orphan_unique_metadata_ids':50,
              'orphan_original_RSA_private_key_present':False,
              'current_video_audio_retested':False,'ibo_device_playback_verified':False,
              'plaintext_URL_files_persisted':False,'main_playlist_modified':False}
    rawstream=io.BytesIO()
    with ZipFile(rawstream,'w',compression=ZIP_STORED) as archive:
        archive.writestr('manifest.json',json.dumps(manifest,sort_keys=True,separators=(',',':')))
        archive.writestr('real-historical-4955-urls.jsonl',real_jsonl)
        archive.writestr('original-stage3-source-proof.zip',stage3_bytes)
        archive.writestr('original-orphan-source-proof.zip',orphan_bytes)
        archive.writestr('original-new-rsa-seals.zip',resealed_bytes)
    raw=rawstream.getvalue()
    key=secrets.token_bytes(32);nonce=secrets.token_bytes(12)
    cipher=MAGIC+nonce+AESGCM(key).encrypt(nonce,raw,AAD)
    if len(cipher)>MAX_ENCRYPTED_SIZE:
        raise ValueError('Encrypted evidence archive too large')
    sha=digest(cipher)
    key_doc=json.dumps({'schema':1,'algorithm':'AES-256-GCM','secret_b64':base64.b64encode(key).decode(),
                        'archive_sha256':sha,'archive_plaintext_bundle_sha256':digest(raw),
                        'warning':'PRIVATE KEY. Keep apart from public GitHub files.'}).encode()
    for p,data in ((out_file,cipher),(aes_key_file,key_doc)):
        p.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(fd,'wb') as out:
            out.write(data);out.flush();os.fsync(out.fileno())
    restored=verify(out_file,aes_key_file,sha)
    assert restored['historical_original_real_url_count']==4955
    return {'archive_sha256':sha,'archive_bytes':len(cipher),'historical_real_urls':4955,
            'orphan_sealed_candidates':107,'rsa_private_recovered_original_urls':True,
            'encrypted_independent_restore_immediately_verified':True}


def verify(archive_file,aes_key_file,expected_sha):
    key_path=private_key_file(aes_key_file)
    file=Path(archive_file)
    if file.is_symlink() or not file.is_file():
        raise ValueError('Restored encrypted bundle must be regular file')
    encrypted=file.read_bytes()
    if len(encrypted)>MAX_ENCRYPTED_SIZE or not encrypted.startswith(MAGIC) or digest(encrypted)!=expected_sha:
        raise ValueError('Independently pinned real URL archive SHA256 mismatch')
    key_doc=json.loads(key_path.read_text(encoding='utf-8'))
    if key_doc.get('archive_sha256')!=expected_sha:
        raise ValueError('Private AES key belongs to a different immutable archive')
    key=base64.b64decode(key_doc['secret_b64'],validate=True)
    if len(key)!=32:
        raise ValueError('Wrong AES key length')
    header=len(MAGIC)
    try:
        raw=AESGCM(key).decrypt(encrypted[header:header+12],encrypted[header+12:],AAD)
    except Exception as exc:
        raise ValueError('AES-256-GCM authenticated real-URL restore failed') from exc
    if digest(raw)!=key_doc.get('archive_plaintext_bundle_sha256'):
        raise ValueError('Decrypted archive content differs from authenticated source')
    with ZipFile(io.BytesIO(raw)) as zipfile:
        expected={'manifest.json','real-historical-4955-urls.jsonl','original-stage3-source-proof.zip','original-orphan-source-proof.zip','original-new-rsa-seals.zip'}
        if set(zipfile.namelist())!=expected:
            raise ValueError('Encrypted archive missing required source-evidence groups')
        manifest=json.loads(zipfile.read('manifest.json'))
        url_data=zipfile.read('real-historical-4955-urls.jsonl')
        if digest(url_data)!=manifest.get('real_url_rows_sha256'):
            raise ValueError('Actual recovered URL evidence was modified')
        rows=[json.loads(l) for l in url_data.splitlines() if l]
        hashes={}
        for r in rows:
            url,identity=r.get('url'),r.get('url_sha256')
            if not isinstance(url,str) or digest(url.encode())!=identity or identity in hashes:
                raise ValueError('Real recovered historical URL hash invalid or duplicated')
            hashes[identity]=r
        if len(rows)!=4955 or len(hashes)!=4955 or digest(''.join(sorted(hashes)).encode())!=HISTORY_IDENTITY_SHA:
            raise ValueError('Lost original 4955 real historical URL identities')
        with ZipFile(io.BytesIO(zipfile.read('original-stage3-source-proof.zip'))) as orig:
            original=[json.loads(l) for l in orig.read('stage3-4955-hash-only.jsonl').splitlines() if l]
        if set(r['url_sha256'] for r in original)!=set(hashes):
            raise ValueError('Restored URL data lost original historical identity')
        if any(any(hashes[r['url_sha256']].get(k)!=v for k,v in r.items()) for r in original):
            raise ValueError('Immutable provenance metadata changed')
        for member,field in [('original-stage3-source-proof.zip','source_stage3_zip_sha256'),('original-orphan-source-proof.zip','source_orphan_zip_sha256'),('original-new-rsa-seals.zip','source_new_RSA_zip_sha256')]:
            if digest(zipfile.read(member))!=manifest[field]:
                raise ValueError('Source encrypted evidence bytes changed')
        if manifest['all_4955_source_URLs_private_RSA_decrypted'] is not True or manifest['ibo_device_playback_verified'] is not False:
            raise ValueError('Archive manifest contains unsupported claims')
    return {'historical_original_real_url_count':4955,'real_source_urls_sha256_verified':True,
            'source_immutable_provenance_verified':True,'aes256gcm_decrypted_from_persistent_archive':True,
            'orphan_sealed_candidates':107,'ibo_device_verified':False}
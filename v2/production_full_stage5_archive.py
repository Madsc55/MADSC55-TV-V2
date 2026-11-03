#!/usr/bin/env python3
"""MADSC55 TV V2 — full authenticated historical-URL and orphan archive acceptance.

Only actual URL records decrypted from GitHub RSA/AES historical source evidence
are stored in the outer AES-256-GCM private archive. No plaintext URL files.
Archive acceptance proves retention/restoration, NOT today's stream playback.
"""
import base64
import io
import json
import os
from pathlib import Path
import secrets
from zipfile import ZipFile,ZIP_STORED
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from production_real_url_archive import (match_original_history,open_sealed,digest,
                                            private_key_file,HISTORY_IDENTITY_SHA)
MAGIC=b"MADSC55-TV-V2-REAL-4955-PLUS-107-ARCHIVE-v1\n"
AAD=b"MADSC55-TV-V2-4955-PLUS-107-ORIGINAL-URL-AESGCM-v1"

def orphan_rows_from_reseal(path,private_key):
    private=serialization.load_pem_private_key(private_key_file(private_key).read_bytes(),password=None)
    with ZipFile(path) as z:
        report=json.loads(z.read('three-source-orphan-anonymous.json'))
        if report.get('orphan_entries')!=55 or report.get('unique_orphan_metadata_identities')!=50:
            raise ValueError('Original 55/50 orphan metadata not preserved')
        all_rows=open_sealed(z.read('three-source-all-historical-candidates.sealed'),private)
        av_rows=open_sealed(z.read('three-source-av-verified.sealed'),private)
        if len(all_rows)!=report.get('all_proven_url_candidates_sealed_for_future_retest') or len(all_rows)!=107:
            raise ValueError('All 107 real orphan candidates not present')
        if len(av_rows)!=report.get('sealed_successful_av_stream_count'):
            raise ValueError('Orphan AV evidence contradicted by decrypted rows')
    indexed={}
    for row in all_rows:
        url=row.get('url'); sha=row.get('url_sha256')
        if not isinstance(url,str) or digest(url.encode())!=sha or sha in indexed:
            raise ValueError('Orphan candidate URL missing, invented, or duplicated')
        indexed[sha]=row
    av_set=set()
    for row in av_rows:
        sha=row.get('url_sha256');url=row.get('url')
        if digest(url.encode())!=sha or sha not in indexed or indexed[sha]['url']!=url:
            raise ValueError('Orphan AV evidence is not a subset of original proven URLs')
        av_set.add(sha)
    if len(av_set)!=len(av_rows):
        raise ValueError('Repeated AV candidate evidence')
    return [indexed[sha] for sha in sorted(indexed)],len(av_set)


def create(stage3_zip,orphan_zip,historical_rsa_zip,orphan_rsa_zip,rsa_private,output_archive,output_key):
    paths=[Path(p) for p in (stage3_zip,orphan_zip,historical_rsa_zip,orphan_rsa_zip)]
    target,keyfile=Path(output_archive),Path(output_key)
    if target.exists() or target.is_symlink() or keyfile.exists() or keyfile.is_symlink():
        raise FileExistsError('Refusing to overwrite V2 original archive or key')
    raw_sources=[p.read_bytes() for p in paths]
    history=match_original_history(raw_sources[0],raw_sources[2],rsa_private)
    orphans,verified_count=orphan_rows_from_reseal(paths[3],rsa_private)
    history_jsonl=''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in history).encode()
    orphan_jsonl=''.join(json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n' for x in orphans).encode()
    manifest={'schema':1,'system':'MADSC55-TV-V2','historical_original_urls_decrypted':4955,
              'historical_identity_sha256':HISTORY_IDENTITY_SHA,'orphan_exact_historical_candidate_urls_decrypted':107,
              'orphan_original_source_metadata_identities':50,'orphan_original_source_occurrences':55,
              'orphan_probe_av_evidence_count':verified_count,
              'history_jsonl_sha256':digest(history_jsonl),'orphan_jsonl_sha256':digest(orphan_jsonl),
              'stage3_source_zip_sha256':digest(raw_sources[0]),'orphan_source_zip_sha256':digest(raw_sources[1]),
              'stage5_historical_rsa_zip_sha256':digest(raw_sources[2]),'stage5_orphan_rsa_zip_sha256':digest(raw_sources[3]),
              'privacy':'NO_UNENCRYPTED_STREAM_URL_FILE','all_real_source_rows_restored':True,
              'current_video_audio_newly_probed':False,'ibo_player_device_playback_verified':False,'main_playlist_modified':False}
    buffer=io.BytesIO()
    with ZipFile(buffer,'w',compression=ZIP_STORED) as z:
        z.writestr('manifest.json',json.dumps(manifest,sort_keys=True,separators=(',',':')))
        z.writestr('real-historical-4955-urls.jsonl',history_jsonl)
        z.writestr('real-orphan-107-urls.jsonl',orphan_jsonl)
        for name,source in zip(('stage3-source.zip','orphan-source.zip','stage5-historical-rsa.zip','stage5-orphan-rsa.zip'),raw_sources):
            z.writestr(name,source)
    data=buffer.getvalue(); secret=secrets.token_bytes(32);nonce=secrets.token_bytes(12)
    cipher=MAGIC+nonce+AESGCM(secret).encrypt(nonce,data,AAD)
    file_sha=digest(cipher)
    key_json=json.dumps({'schema':1,'system':'MADSC55-TV-V2','archive_sha256':file_sha,
                         'plaintext_zip_sha256':digest(data),'algorithm':'AES-256-GCM',
                         'private_secret_base64':base64.b64encode(secret).decode(),
                         'warning':'PRIVATE! NEVER COMMIT THIS KEY TO GITHUB.'},sort_keys=True).encode()
    for p,bytes_ in ((target,cipher),(keyfile,key_json)):
        p.parent.mkdir(parents=True,exist_ok=True)
        fd=os.open(p,os.O_WRONLY|os.O_EXCL|os.O_CREAT|getattr(os,'O_NOFOLLOW',0),0o600)
        with os.fdopen(fd,'wb') as f:f.write(bytes_);f.flush();os.fsync(f.fileno())
    restored=verify(target,keyfile,file_sha)
    assert restored['historical_original_urls']==4955 and restored['orphan_original_urls']==107
    return {'archive_sha256':file_sha,'archive_size':len(cipher),'historical_original_urls':4955,
            'orphan_original_urls':107,'historical_provenance_restored':True,
            'orphan_video_audio_evidence':verified_count,'complete_aes_gcm_restore_passed':True,
            'ibo_player_device_verified':False}


def verify(encrypted_archive,private_key,expected_checksum):
    key_path=private_key_file(private_key)
    archive_path=Path(encrypted_archive)
    if archive_path.is_symlink() or not archive_path.is_file():
        raise ValueError('Encrypted private archive file missing or is a symlink')
    payload=archive_path.read_bytes()
    if not payload.startswith(MAGIC) or digest(payload)!=expected_checksum:
        raise ValueError('Restored archive differs from independent original SHA256')
    info=json.loads(key_path.read_text())
    if info.get('algorithm')!='AES-256-GCM' or info.get('archive_sha256')!=expected_checksum:
        raise ValueError('Wrong private AES recovery key metadata')
    secret=base64.b64decode(info['private_secret_base64'],validate=True)
    if len(secret)!=32:raise ValueError('Invalid AES-256 recovery key')
    off=len(MAGIC)
    try:raw=AESGCM(secret).decrypt(payload[off:off+12],payload[off+12:],AAD)
    except Exception as exc:raise ValueError('AES-256-GCM authenticated decryption failed') from exc
    if digest(raw)!=info.get('plaintext_zip_sha256'):
        raise ValueError('Full encrypted snapshot restore digest mismatch')
    with ZipFile(io.BytesIO(raw)) as z:
        expected={'manifest.json','real-historical-4955-urls.jsonl','real-orphan-107-urls.jsonl','stage3-source.zip','orphan-source.zip','stage5-historical-rsa.zip','stage5-orphan-rsa.zip'}
        if set(z.namelist())!=expected:raise ValueError('Source archives or real URL evidence missing')
        report=json.loads(z.read('manifest.json'))
        histories=z.read('real-historical-4955-urls.jsonl'); orphans=z.read('real-orphan-107-urls.jsonl')
        if digest(histories)!=report['history_jsonl_sha256'] or digest(orphans)!=report['orphan_jsonl_sha256']:
            raise ValueError('Authenticated real URL records changed')
        hrows=[json.loads(x) for x in histories.splitlines() if x]
        orows=[json.loads(x) for x in orphans.splitlines() if x]
        for rows,count in ((hrows,4955),(orows,107)):
            ids=set()
            if len(rows)!=count:raise ValueError('Missing real historical or orphan source URL')
            for item in rows:
                url=item.get('url');sha=item.get('url_sha256')
                if not isinstance(url,str) or sha!=digest(url.encode()) or sha in ids:
                    raise ValueError('Invalid or duplicated real source URL identity')
                ids.add(sha)
        hs={row['url_sha256'] for row in hrows}
        if digest(''.join(sorted(hs)).encode())!=HISTORY_IDENTITY_SHA:
            raise ValueError('Real historical 4955 URL SHA identity baseline drift')
        with ZipFile(io.BytesIO(z.read('stage3-source.zip'))) as src:
            real=[json.loads(x) for x in src.read('stage3-4955-hash-only.jsonl').splitlines() if x]
        if len(real)!=4955 or {row['url_sha256'] for row in real}!=hs:
            raise ValueError('Original historical #60 provenance not restored')
        hmap={r['url_sha256']:r for r in hrows}
        if any(any(hmap[r['url_sha256']].get(k)!=v for k,v in r.items()) for r in real):
            raise ValueError('Original metadata changed while restoring real URLs')
        with ZipFile(io.BytesIO(z.read('orphan-source.zip'))) as src:
            old=json.loads(src.read('three-source-orphan-anonymous.json'))
        if old['orphan_entries']!=55 or old['unique_orphan_metadata_identities']!=50:
            raise ValueError('Original orphan metadata not restored')
        with ZipFile(io.BytesIO(z.read('stage5-orphan-rsa.zip'))) as recent:
            new=json.loads(recent.read('three-source-orphan-anonymous.json'))
        old_hashes={c['url_sha256'] for item in old['records'] for c in item['candidates']}
        new_hashes={c['url_sha256'] for item in new['records'] for c in item['candidates']}
        if len(old_hashes)!=107 or old_hashes!=new_hashes or old_hashes!={r['url_sha256'] for r in orows}:
            raise ValueError('Original 107 proven orphan URL identities drifted during reseal')
        checks={'stage3-source.zip':'stage3_source_zip_sha256','orphan-source.zip':'orphan_source_zip_sha256','stage5-historical-rsa.zip':'stage5_historical_rsa_zip_sha256','stage5-orphan-rsa.zip':'stage5_orphan_rsa_zip_sha256'}
        for name,k in checks.items():
            if digest(z.read(name))!=report[k]:raise ValueError('Nested RSA or source ZIP modified')
        if report.get('current_video_audio_newly_probed') is not False or report.get('ibo_player_device_playback_verified') is not False:
            raise ValueError('Unsupported real playback claim in archive')
    return {'historical_original_urls':4955,'orphan_original_urls':107,'exact_sha256_identities_verified':True,
            'source_provenance_preserved':True,'full_aes_gcm_restore':True,
            'current_video_audio_probe_not_performed':True,'ibo_device_verified':False}
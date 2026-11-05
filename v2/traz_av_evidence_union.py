#!/usr/bin/env python3
"""Merge pinned, anonymous FFmpeg evidence without reprobing or IBO writes.

The API snapshot and an exact-M3U recovery pass are separate evidence scopes.
Channel identity + URL SHA integrity is mandatory. This does not establish
spoken language, Swedish access, stable playback or an IBO device result.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'v2/reports/ci'
HEX = re.compile(r'[0-9a-f]{64}\Z')

def _check(doc, kind, policy):
    if (not isinstance(doc, dict) or doc.get('schema') != 1 or
        doc.get('kind') != kind or doc.get('policy') != policy or
        doc.get('protected_playlist_modified') is not False or
        doc.get('ibo_device_verified') is not False):
        raise ValueError('Invalid or unsafe immutable evidence source')
    return doc

def _hash(value):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ValueError('Missing or invalid URL SHA-256')
    return value

def _read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8_000_000:
        raise ValueError('Missing or unsafe anonymous report')
    content = path.read_bytes()
    if b'http://' in content or b'https://' in content:
        raise ValueError('Public evidence must not contain plaintext URLs')
    return json.loads(content), sha256(content).hexdigest()

def merge(prior, newer, gap):
    prior = _check(prior, 'TR_AZ_IPTV_API_REAL_FFMPEG_AV_ACCEPTANCE',
                   'ANONYMOUS_HASH_ONLY_RSA_ENCRYPTED_URLS')
    newer = _check(newer, 'V2_TR_AZ_MISSING_M3U_REAL_AV_READONLY',
                   'PUBLIC_SHA_ONLY_RSA_AES_SEALED_STREAM_URLS')
    gap = _check(gap, 'V2_TR_AZ_EXACT_MISSING_M3U_AND_EPG_GAP_TRIAGE',
                 'READ_ONLY_PUBLIC_HASH_ONLY_NO_AUTO_IBO_PROMOTION')
    if (prior.get('unprobed') != 0 or prior.get('probed') != prior.get('unique_url_candidates')
        or not isinstance(prior.get('streams'), list) or
        len(prior['streams']) != prior['probed'] or len(prior['streams']) > 1000):
        raise ValueError('Prior AV sample coverage incomplete')
    if (not isinstance(newer.get('results'), list) or
        len(newer['results']) != newer.get('candidate_hashes') or
        len(newer['results']) > 5000 or
        newer.get('ffmpeg_probed') != newer.get('matched_current_source_hashes') or
        newer.get('matched_current_source_hashes', -1) > len(newer['results']) or
        newer.get('old_historical_orphan_50_auto_recovered') is not False):
        raise ValueError('New exact-source AV sample coverage inconsistent')
    expected = {}
    for group in gap.get('candidate_identities', []):
        cid = group.get('channel_id')
        candidates = group.get('candidate_m3u_url_hashes')
        if (not isinstance(cid, str) or not cid or not isinstance(candidates, list) or
            group.get('candidate_count') != len(candidates) or
            group.get('playback_verified') is not False):
            raise ValueError('Invalid pre-existing exact M3U identity')
        for item in candidates:
            h = _hash(item.get('url_sha256'))
            if item.get('av_verified') is not False or h in expected:
                raise ValueError('False or overlapping discovery lead')
            expected[h] = cid
    if (len(expected) != gap.get('exact_missing_stream_candidate_hashes') or
        len(expected) != newer.get('candidate_hashes')):
        raise ValueError('Exact M3U target artifact and AV run mismatch')
    found = {}
    old_ids = set()
    counts = Counter()
    for item in prior['streams']:
        h = _hash(item.get('url_sha256'))
        ids = item.get('channel_ids')
        if (h in found or 'url' in item or not isinstance(ids, list) or not ids or
            len(ids) != len(set(ids)) or not all(isinstance(i, str) and i for i in ids) or
            item.get('decoded') not in (True, False)):
            raise ValueError('Duplicate or invalid previous AV identity')
        counts[item.get('status')] += 1
        if item['decoded']:
            if (item.get('status') != 'VIDEO_AUDIO_DECODED' or
                item.get('video') is not True or item.get('audio') is not True):
                raise ValueError('Fabricated previous AV success')
            found[h] = frozenset(ids)
            old_ids.update(ids)
    if (dict(counts) != prior.get('status_counts') or
        len(found) != prior.get('video_audio_decoded')):
        raise ValueError('Previous FFmpeg tally mismatch')
    new_ids = set()
    statuses = Counter()
    matched = 0
    new_decodes = 0
    for item in newer['results']:
        h = _hash(item.get('url_sha256'))
        cid = item.get('exact_channel_id')
        if ('url' in item or h not in expected or expected[h] != cid or
            item.get('ibo_device_verified') is not False or
            not isinstance(item.get('status'), str) or
            item.get('decoded') not in (True, False)):
            raise ValueError('Unpinned or invalid exact-M3U recovery result')
        del expected[h]
        statuses[item['status']] += 1
        if item['status'] != 'NOT_FOUND_IN_CURRENT_SOURCE':
            matched += 1
        if item['decoded']:
            if (item['status'] != 'VIDEO_AUDIO_DECODED' or
                item.get('video') is not True or item.get('audio') is not True):
                raise ValueError('Fabricated new AV success')
            new_decodes += 1
            new_ids.add(cid)
            if h in found and found[h] != frozenset([cid]):
                raise ValueError('Same proven URL assigned to different broadcaster')
            found[h] = frozenset([cid])
    if (expected or matched != newer['matched_current_source_hashes'] or
        len(newer['results']) - matched != newer.get('unmatched_or_unavailable_hashes') or
        dict(statuses) != newer.get('av_status_counts') or
        new_decodes != newer.get('real_video_audio_decoded_hashes') or
        len(new_ids) != newer.get('real_video_audio_channel_ids') or
        sorted(new_ids) != newer.get('channel_ids_with_new_av')):
        raise ValueError('Targeted AV tally or identity mismatch')
    union_ids = set().union(*found.values()) if found else set()
    streamless = gap.get('missing_api_stream_identities')
    epg_missing = gap.get('missing_api_epg_references')
    with_leads = gap.get('exact_missing_stream_identities_with_other_m3u_leads')
    no_leads = gap.get('still_without_exact_source_metadata')
    if (not all(isinstance(i, int) and i >= 0 for i in
                (streamless, epg_missing, with_leads, no_leads)) or
        with_leads + no_leads != streamless or
        not new_ids.issubset({r.get('channel_id') for r in gap['candidate_identities']})):
        raise ValueError('Source candidate counts do not reconcile')
    xmltv = gap.get('epg_xmltv')
    if not isinstance(xmltv, dict) or xmltv.get('missing_api_guide_identities') != epg_missing:
        raise ValueError('Missing XMLTV gap review')
    xml_matched = xmltv.get('exact_xmltv_channel_id_candidates')
    xml_remaining = xmltv.get('remaining_without_xmltv_channel_id_candidate')
    if (not isinstance(xml_matched, int) or not isinstance(xml_remaining, int) or
        xml_matched + xml_remaining != epg_missing):
        raise ValueError('XMLTV metadata mismatch')
    return {
        'schema': 1, 'kind': 'V2_TR_AZ_CROSS_RUN_REAL_AV_EVIDENCE_UNION',
        'policy': 'READ_ONLY_SHA_ONLY_NO_REPROBING_OR_IBO_EXPORT',
        'previous_video_audio_stream_hashes': prior['video_audio_decoded'],
        'previous_video_audio_channel_ids': len(old_ids),
        'new_exact_source_video_audio_stream_hashes': new_decodes,
        'new_exact_source_video_audio_channel_ids': len(new_ids),
        'overlapping_av_channel_ids': sorted(old_ids & new_ids),
        'total_distinct_video_audio_stream_hashes': len(found),
        'total_distinct_video_audio_channel_ids': len(union_ids),
        'newly_av_proven_channel_ids': sorted(new_ids-old_ids),
        'original_api_streamless_identities': streamless,
        'other_m3u_exact_source_lead_identities': with_leads,
        'other_m3u_no_lead_identities': no_leads,
        'source_lead_identities_still_without_new_av': with_leads-len(new_ids),
        'missing_api_epg_references': epg_missing,
        'additional_xmltv_id_candidates_not_schedule_proof': xml_matched,
        'still_without_exact_xmltv_id_candidate': xml_remaining,
        'new_source_hashes_unmatched_in_current_sources': newer['unmatched_or_unavailable_hashes'],
        'old_historical_orphan_50_auto_recovered': False,
        'long_term_stability_verified': False, 'spoken_language_verified': False,
        'sweden_access_verified': False, 'ibo_device_verified': False,
        'protected_playlist_modified': False,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prior', type=Path, default=BASE/'traz-api-av-acceptance.json')
    ap.add_argument('--new', type=Path, default=BASE/'traz-missing-target-real-av.json')
    ap.add_argument('--gap', type=Path, default=BASE/'traz-missing-stream-epg-crosswalk.json')
    ap.add_argument('--out', type=Path, default=BASE/'traz-av-evidence-union.json')
    a = ap.parse_args()
    inputs = [_read(p) for p in (a.prior, a.new, a.gap)]
    report = merge(*(i[0] for i in inputs))
    report['source_report_sha256'] = {k: inputs[i][1] for i,k in
       enumerate(('initial_real_av','targeted_real_av','exact_source_xmltv_gap'))}
    if a.out.is_symlink() or a.out.suffix != '.json' or a.out.name.startswith('private'):
        raise ValueError('Unsafe anonymous output path')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('TR_AZ_AV_EVIDENCE_UNION',json.dumps({
        'av_streams':report['total_distinct_video_audio_stream_hashes'],
        'av_channel_ids':report['total_distinct_video_audio_channel_ids'],
        'added_av_ids':report['newly_av_proven_channel_ids'],
        'xmltv_id_candidates':report['additional_xmltv_id_candidates_not_schedule_proof']},sort_keys=True))

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Offline hash-only #60 history cross-reference against existing local M3U files.

Never guesses stream addresses, probes networks, exports a playlist, or writes
plaintext URLs. Existing files are read-only; public reports contain hashes
and coverage counts only. Private matched URL evidence is memory-only unless
an explicit encrypted output archive with key is requested.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from discover import entries
from historical_url_recovery import validate_url
from historical_inventory_guard import reconcile, preserve_to_new_archive

SHA = re.compile(r'^[0-9a-f]{64}$')
MAX_M3U_BYTES = 32_000_000


def validate_index(records, expected=4955):
    records = list(records)
    if expected is not None and len(records) != expected:
        raise ValueError('Real history baseline count mismatch')
    hashes = set()
    for row in records:
        if not isinstance(row, dict) or 'url' in row:
            raise ValueError('History must be hash-only records')
        key = row.get('url_sha256')
        if not isinstance(key, str) or not SHA.fullmatch(key) or key in hashes:
            raise ValueError('Invalid or duplicate history identity')
        hashes.add(key)
    return hashes


def match_local_sources(records, sources, expected=4955):
    """Return URL-free public audit and private in-memory matches (never logged)."""
    hashes = validate_index(records, expected)
    found, per_source = {}, []
    used_sources = set()
    for source_id, text in sources:
        if not isinstance(source_id, str) or not source_id or source_id in used_sources:
            raise ValueError('Invalid or duplicate local source label')
        if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_M3U_BYTES:
            raise ValueError('Malformed or oversize M3U content')
        used_sources.add(source_id)
        if not text.lstrip('\ufeff \r\n\t').startswith('#EXTM3U'):
            raise ValueError('Not an M3U playlist')
        source_hits = set()
        for item in entries(text):
            url = item.get('url')
            if not validate_url(url):
                continue
            key = hashlib.sha256(url.encode('utf-8')).hexdigest()
            if key not in hashes:
                continue
            source_hits.add(key)
            if key not in found:
                found[key] = {'url': url, 'url_sha256': key, 'source_ids': [source_id],
                              'name': item.get('name', ''), 'tvg_id': item.get('tvg_id', ''),
                              'logo': item.get('logo', ''), 'group': item.get('group', '')}
            elif source_id not in found[key]['source_ids']:
                found[key]['source_ids'].append(source_id)
        per_source.append({'source_id': source_id, 'matched_historical_hashes': len(source_hits)})
    result = {'schema': 1, 'policy': 'OFFLINE_HASH_MATCH_NOT_PLAYBACK_NO_AUTOPUBLISH',
              'historical_hash_identities': len(hashes),
              'matched_real_url_identities': len(found),
              'unmatched_hash_identities': len(hashes) - len(found),
              'duplicate_matched_identities': 0,
              'matched_hashes': sorted(found),
              'source_audit': per_source,
              'streams_tested': 0, 'device_verified': False,
              'channel_playlist_modified': False,
              'plaintext_url_emitted': False}
    return result, list(found.values())


def read_local_m3u(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_M3U_BYTES:
        raise ValueError('Expected a regular, bounded-size, non-symlink local M3U')
    return path.read_text(encoding='utf-8-sig')


def main():
    parser = argparse.ArgumentParser(description='Offline original M3U hash matches (no network)')
    parser.add_argument('--history-index', type=Path, required=True)
    parser.add_argument('--playlist', type=Path, action='append', required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--expected', type=int, default=4955)
    parser.add_argument('--out-archive', type=Path, help='Private AES-GCM archive; requires V2_ARCHIVE_KEY_HEX')
    args = parser.parse_args()
    if args.expected < 1 or args.report.exists() or args.report.is_symlink():
        parser.error('Unsafe report target or baseline')
    inputs = [args.history_index, *args.playlist]
    outputs = [args.report] + ([args.out_archive] if args.out_archive else [])
    if len({str(x.resolve()) for x in [*inputs, *outputs]}) != len(inputs) + len(outputs):
        parser.error('Input/output collision or repeated input')
    if args.history_index.is_symlink():
        parser.error('Historical input cannot be a symlink')
    rows = [json.loads(line) for line in args.history_index.read_text(encoding='utf-8').splitlines() if line.strip()]
    summary, private_matches = match_local_sources(
        rows, [('local-playlist-%d' % (i + 1), read_local_m3u(path))
               for i, path in enumerate(args.playlist)], args.expected)
    if args.out_archive:
        protected, indexed, proof = reconcile(rows, private_matches, args.expected)
        if proof['historical_hash_only_identities'] != args.expected:
            raise ValueError('Historical identities were lost during reconciliation')
        summary['encrypted_archive_verified'] = preserve_to_new_archive(args.out_archive, protected, indexed)
    else:
        summary['encrypted_archive_verified'] = False
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: val for key, val in summary.items() if key != 'matched_hashes'}, sort_keys=True))


if __name__ == '__main__':
    main()

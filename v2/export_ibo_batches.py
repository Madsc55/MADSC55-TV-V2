#!/usr/bin/env python3
"""Generate real 1000/2000-item IBO M3U files from an encrypted verified inventory."""
import argparse
import json
import os
from pathlib import Path
from secure_archive import decrypt, atomic_write

def render(records):
    lines = ['#EXTM3U']
    for record in records:
        name = str(record.get('name') or 'UNKNOWN').replace('\n', ' ').replace('\r', ' ').replace(',', ' ')
        group = str(record.get('group') or 'TR-AZ ADAY').replace('"', '').replace('\n', ' ')
        logo = str(record.get('logo') or '')
        logo_attr = f' tvg-logo="{logo}"' if logo.startswith(('https://', 'http://')) and '"' not in logo else ''
        lines.extend([f'#EXTINF:-1{logo_attr} group-title="{group}",{name}', record['url']])
    return ('\n'.join(lines) + '\n').encode('utf-8')

def export(archive, passphrase, destination, sizes=(1000, 2000), existing=()):
    raw = decrypt(Path(archive).read_bytes(), passphrase)
    records, seen = [], set(existing)
    for line in raw.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        url = record.get('url')
        if not isinstance(url, str) or not url.startswith(('http://', 'https://')) or url in seen:
            continue
        if record.get('http_hls_status') != 'AV_VERIFIED':
            continue
        seen.add(url)
        records.append(record)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    # Never leave older, larger exports that could be mistaken for this run.
    for stale in destination.glob('IBO_AV_VERIFIED_*_PART*.m3u8'):
        stale.unlink()
    result = {'av_verified_unique': len(records), 'packages': []}
    for size in sizes:
        for part, offset in enumerate(range(0, len(records), size), 1):
            batch = records[offset:offset + size]
            path = destination / f'IBO_AV_VERIFIED_{size}_PART{part}.m3u8'
            atomic_write(path, render(batch))
            result['packages'].append({'path': str(path), 'count': len(batch), 'batch_size': size})
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('encrypted_inventory', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--live', type=Path, required=True)
    args = parser.parse_args()
    if not args.live.is_file():
        parser.error('Protected main playlist is required for exclusion')
    existing = {line.strip() for line in args.live.read_text(encoding='utf-8-sig').splitlines()
                if line.strip().startswith(('http://', 'https://'))}
    if not existing:
        parser.error('Protected playlist has no URLs')
    secret = os.environ.get('V2_ARCHIVE_PASSPHRASE', '')
    result = export(args.encrypted_inventory, secret, args.destination, existing=existing)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['packages']:
        raise SystemExit('No verified candidates; no packages generated')

if __name__ == '__main__':
    main()

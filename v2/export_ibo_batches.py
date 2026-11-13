#!/usr/bin/env python3
"""Generate real 1000/2000-item IBO M3U files from an encrypted verified inventory."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from secure_archive import decrypt, atomic_write

def valid_stream_url(value):
    """Reject malformed URLs before any untrusted inventory is rendered as M3U."""
    if not isinstance(value, str) or not value or any(
            ord(char) < 32 or ord(char) == 127 or char.isspace()
            for char in value):
        return False
    try:
        parsed = urlsplit(value)
        _ = parsed.port
        return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
                and parsed.username is None and parsed.password is None)
    except ValueError:
        return False


def clean_attribute(value):
    """Keep untrusted source metadata on its original EXTINF line."""
    return "".join(" " if (ord(char) < 32 or 127 <= ord(char) <= 159
                           or char in ("\\u2028", "\\u2029")) else char
                   for char in str(value or "")).replace('"', "")


def render(records):
    lines = ['#EXTM3U']
    for record in records:
        url = record['url']
        if not valid_stream_url(url):
            raise ValueError("Invalid source URL in IBO package")
        name = clean_attribute(record.get('name') or 'UNKNOWN').replace(',', ' ')
        group = clean_attribute(record.get('group') or 'TR-AZ ADAY')
        logo = record.get('logo') or ''
        logo_attr = f' tvg-logo="{logo}"' if valid_stream_url(logo) and '"' not in logo else ''
        lines.extend([f'#EXTINF:-1{logo_attr} group-title="{group}",{name}', url])
    return ('\n'.join(lines) + '\n').encode('utf-8')

def export(archive, passphrase, destination, sizes=(1000, 2000), existing=()):
    raw = decrypt(Path(archive).read_bytes(), passphrase)
    records, seen = [], set(existing)
    for line in raw.splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if not isinstance(record, dict):
            continue
        url = record.get('url')
        if not valid_stream_url(url) or url in seen:
            continue
        if record.get('http_hls_status') != 'AV_VERIFIED':
            continue
        seen.add(url)
        records.append(record)
    destination = Path(destination)
    if destination.is_symlink():
        raise ValueError('Package output directory must not be a symlink')
    # Plan every output before writing any: never delete or replace older
    # packages, even if a different historical batch size is requested.
    planned = []
    for size in sizes:
        if type(size) is not int or size <= 0:
            raise ValueError('Invalid IBO batch size')
        for part, offset in enumerate(range(0, len(records), size), 1):
            batch = records[offset:offset + size]
            path = destination / f'IBO_AV_VERIFIED_{size}_PART{part}.m3u8'
            planned.append((path, batch, size))
    paths = [path for path, _, _ in planned]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate output package paths')
    if any(path.exists() or path.is_symlink() for path in paths):
        raise FileExistsError('Existing IBO package must not be replaced or deleted')
    destination.mkdir(parents=True, exist_ok=True)
    result = {'av_verified_unique': len(records), 'packages': []}
    for path, batch, size in planned:
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

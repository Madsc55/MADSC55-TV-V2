#!/usr/bin/env python3
"""Fill missing YEDEKLER logos from matching public M3U metadata; never invent logos."""
import pathlib
import re
import urllib.request
from real_ibo_scan import SOURCES, LIVE, fetch, parse_m3u
import json

def norm(name):
    name = re.sub(r'\s*\([^)]*(?:p|P|HD|FHD|UHD)[^)]*\)', '', name)
    return re.sub(r'[^\w]+', '', name.casefold())

def main():
    rows = LIVE.read_text(encoding='utf-8-sig').splitlines(keepends=True)
    source_doc = json.loads(SOURCES.read_text(encoding='utf-8'))
    by_url, by_name = {}, {}
    for source in source_doc['sources']:
        try:
            for item in parse_m3u(fetch(source['url'], timeout=12)):
                logo = item.get('logo', '')
                if not logo.startswith(('https://','http://')) or '"' in logo:
                    continue
                by_url.setdefault(item['url'], logo)
                key = norm(item['name'])
                if key:
                    by_name.setdefault(key, set()).add(logo)
        except (OSError, ValueError, UnicodeError) as exc:
            print(f"Skipped {source['id']}: {type(exc).__name__}")
    changed = 0
    for i, row in enumerate(rows):
        if not row.startswith('#EXTINF:') or 'YEDEKLER (' not in row or 'tvg-logo=' in row:
            continue
        name = row.rstrip('\r\n').rsplit(',', 1)[-1]
        url = rows[i + 1].strip() if i + 1 < len(rows) else ''
        logo = by_url.get(url)
        if not logo:
            options = by_name.get(norm(name), set())
            if len(options) == 1:
                logo = next(iter(options))
        if logo:
            rows[i] = row.replace('#EXTINF:-1', f'#EXTINF:-1 tvg-logo="{logo}"', 1)
            changed += 1
    if changed:
        LIVE.write_text(''.join(rows), encoding='utf-8', newline='')
    print(f'Logo metadata added: {changed}; existing entries preserved')

if __name__ == '__main__':
    main()

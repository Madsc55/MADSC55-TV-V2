#!/usr/bin/env python3
"""Real-network IPTV candidate scanner; exports 2000-item device test batches.
Not a replacement for v2/discover.py; can run beside the existing V2 engine.
No mock data, no invented URLs. HTTP/HLS checks are not playback proof.
"""
import argparse
import concurrent.futures
import hashlib
import http.client
import json
import pathlib
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'v2/config/sources.json'
LIVE = ROOT / 'MADSC55_TV_IBO_CALISANLAR_TEST.m3u8'
OUT = ROOT / 'v2/reports/IBO_YENI_ADAYLAR_PART1.m3u8'
REPORT = ROOT / 'v2/reports/ibo-real-scan-report.json'
UA = 'MADSC55-TV-V2-RealScanner/1.0'
MAX_SOURCE = 25_000_000


def fetch(url, timeout=18, limit=MAX_SOURCE):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError('Source exceeded size limit')
        return data


def parse_m3u(data):
    text = data.decode('utf-8-sig', 'replace')
    if not text.lstrip().startswith('#EXTM3U'):
        raise ValueError('Not an M3U playlist')
    pending = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith('#EXTINF:'):
            name = line.rsplit(',', 1)[-1].strip() or 'Unknown'
            group = re.search(r'group-title="([^"]*)"', line)
            tvg = re.search(r'tvg-id="([^"]*)"', line)
            logo = re.search(r'tvg-logo="([^"]*)"', line)
            pending = {'name': name, 'group': group.group(1) if group else '',
                       'tvg_id': tvg.group(1) if tvg else '',
                       'logo': logo.group(1) if logo else ''}
        elif line and not line.startswith('#'):
            if pending and urllib.parse.urlsplit(line).scheme in ('http', 'https'):
                yield {**pending, 'url': line}
            pending = None


def tr_az(entry, scope):
    # Country-level source labels do not prove the individual stream language.
    value = ' '.join(entry[k] for k in ('name', 'group', 'tvg_id')).casefold()
    excluded = ("trt arabi", "trt world", "young turks", "trt (greece)", "trt (venezuela)")
    if any(x in value for x in excluded):
        return False
    # TR/AZ scoped lists provide discovery candidates, not language proof.
    if scope in ('TR', 'AZ'):
        return True
    return bool(re.search(r'türk|turk|trt (?:1|2|3|cocuk|çocuk|spor|muzik|müzik|eba)|azer|azər|azərbaycan|azerbaijan|(?:^|[ ._-])(?:tr|az)(?:$|[ ._-])', value))


def check_hls(entry, timeout):
    url = entry['url']
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname:
        return None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Range': 'bytes=0-4095'})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            status = res.status
            content_type = res.headers.get('Content-Type', '').lower()
            sample = res.read(4096)
        hls = (b'#EXTM3U' in sample and (b'#EXT-X-' in sample or
               'mpegurl' in content_type))
        if status in (200, 206) and hls:
            return entry
    except (OSError, TimeoutError, urllib.error.URLError, ValueError,
            http.client.IncompleteRead, http.client.HTTPException):
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sources', type=pathlib.Path, default=SOURCES)
    ap.add_argument('--output', type=pathlib.Path, default=OUT)
    ap.add_argument('--report', type=pathlib.Path, default=REPORT)
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--timeout', type=float, default=12)
    ap.add_argument('--limit', type=int, default=2000)
    ap.add_argument('--live', type=pathlib.Path, default=LIVE)
    ap.add_argument('--append-live', action='store_true', help='Append verified new channels to YEDEKLER only')
    args = ap.parse_args()
    if not 1 <= args.workers <= 32 or not 1 <= args.limit <= 10000:
        ap.error('workers must be 1..32 and limit 1..10000')
    if not args.live.is_file():
        ap.error('Protected main playlist not found; refusing unfiltered export')
    live_text = args.live.read_text(encoding='utf-8-sig', errors='replace')
    existing = {line.strip() for line in live_text.splitlines()
                if line.strip().startswith(('https://', 'http://'))}
    if not existing:
        ap.error('Protected main playlist contains no stream URLs; refusing unfiltered export')
    doc = json.loads(args.sources.read_text(encoding='utf-8'))
    sources = doc['sources'] if isinstance(doc, dict) else doc
    # Do not export incomplete results as a successful production list.
    candidates = {}
    failed = []
    source_counts = {}
    for source in sources:
        sid, url = source['id'], source['url']
        if urllib.parse.urlsplit(url).scheme != 'https':
            failed.append({'id': sid, 'error': 'NonHTTPS source'}); continue
        try:
            records = list(parse_m3u(fetch(url, args.timeout)))
            source_counts[sid] = len(records)
            for entry in records:
                if tr_az(entry, source.get('scope', 'candidate')):
                    if entry['url'] not in existing:
                        candidates.setdefault(entry['url'], entry)
        except (OSError, ValueError, UnicodeError, socket.timeout) as exc:
            failed.append({'id': sid, 'error': type(exc).__name__})
    checked = 0
    good = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda x: check_hls(x, args.timeout), candidates.values()):
            checked += 1
            if result is not None:
                good.append(result)
    # Source outages are reported; a working subset can still be tested.
    # Never modify the protected main playlist.
    report = {'source_count': len(sources), 'fetched_sources': len(source_counts),
              'failed_sources': failed, 'existing_main_urls': len(existing), 'unique_new_candidates': len(candidates),
              'http_checked': checked, 'http_hls_ok': len(good), 'exported_part1': min(len(good), args.limit),
              'part_count': (len(good) + args.limit - 1) // args.limit,
              'playback_verified_on_device': False, 'mock_data_used': False,
              'status': 'READY_FOR_DEVICE_TEST' if good else 'NO_VERIFIED_CANDIDATES'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if not good:
        # A completed scan with zero eligible streams is a valid no-change result.
        # Keep the report and original playlist intact; do not invent channels.
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    lines = ['#EXTM3U']
    for item in good[:args.limit]:
        name = item['name'].replace('\n', ' ').replace('\r', ' ').replace(',', ' ').upper()
        group = item['group'].replace('"', '').replace('\n', ' ')
        logo = item.get('logo', '')
        logo_attr = f' tvg-logo="{logo}"' if logo.startswith(('https://', 'http://')) and '"' not in logo else ''
        lines.extend([f'#EXTINF:-1{logo_attr} group-title="{group}",{name}', item['url']])
    temp = args.output.with_suffix(args.output.suffix + '.tmp')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    temp.replace(args.output)
    if args.append_live:
        # Preserve every existing byte: append only new verified stream records.
        original = args.live.read_bytes()
        current_urls = {line.strip() for line in
                        original.decode('utf-8-sig', 'replace').splitlines()
                        if line.strip().startswith(('https://', 'http://'))}
        additions = []
        for item in good[:args.limit]:
            if item['url'] in current_urls:
                continue
            current_urls.add(item['url'])
            safe_name = (re.sub(r'[\r\n,]', ' ', item['name']).strip() or 'YENİ KANAL').upper()
            logo = item.get('logo', '')
            logo_attr = f' tvg-logo="{logo}"' if logo.startswith(('https://', 'http://')) and '"' not in logo else ''
            additions.extend([
                f'#EXTINF:-1{logo_attr} group-title="🗂️ YEDEKLER (2)",{safe_name}',
                item['url'],
            ])
        if additions:
            separator = b'' if original.endswith(b'\n') else b'\n'
            # Atomic write; preexisting content and categories remain byte-identical.
            tmp = args.live.with_suffix(args.live.suffix + '.tmp')
            # Normalize every YEDEKLER header to the new exact category total.
            old_group = re.search(rb'group-title="\xf0\x9f\x97\x82\xef\xb8\x8f YEDEKLER \(\d+\)"', original)
            if not old_group:
                raise ValueError('YEDEKLER category not found')
            new_count = len(re.findall(rb'group-title="\xf0\x9f\x97\x82\xef\xb8\x8f YEDEKLER \(\d+\)"', original)) + len(additions) // 2
            group_new = f'group-title="🗂️ YEDEKLER ({new_count})"'.encode('utf-8')
            combined = original + separator + ('\n'.join(additions) + '\n').encode('utf-8')
            combined = re.sub(rb'group-title="\xf0\x9f\x97\x82\xef\xb8\x8f YEDEKLER \(\d+\)"', lambda _: group_new, combined)
            # Only YEDEKLER is alphabetized; all other groups retain their order.
            decoded = combined.decode('utf-8')
            rows = decoded.splitlines()
            if not rows or rows[0] != '#EXTM3U':
                raise ValueError('Invalid playlist header')
            pairs = [(rows[i], rows[i + 1]) for i in range(1, len(rows) - 1, 2)]
            other = [p for p in pairs if 'group-title="🗂️ YEDEKLER (' not in p[0]]
            backups = [p for p in pairs if 'group-title="🗂️ YEDEKLER (' in p[0]]
            backups.sort(key=lambda p: p[0].rsplit(',', 1)[-1].casefold())
            combined = ('#EXTM3U\\n' + ''.join(h + '\\n' + u + '\\n' for h, u in other + backups)).encode('utf-8')
            tmp.write_bytes(combined)
            tmp.replace(args.live)
        report['added_to_yedekler'] = len(additions) // 2
        report['status'] = 'APPENDED_TO_YEDEKLER' if additions else 'NO_NEW_URLS'
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n',
                               encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

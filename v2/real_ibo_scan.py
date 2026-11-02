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
import time
import urllib.error
import urllib.parse
import urllib.request
from stream_probe import probe
from secure_archive import backup as encrypt_inventory, decrypt as decrypt_inventory
import os

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'v2/config/sources.json'
DYNAMIC_SOURCES = ROOT / 'v2/reports/github-source-discovery.json'
LIVE = ROOT / 'MADSC55_TV_IBO_CALISANLAR_TEST.m3u8'
OUT = ROOT / 'v2/reports/IBO_YENI_ADAYLAR_PART1.m3u8'
REPORT = ROOT / 'v2/reports/ibo-real-scan-report.json'
INVENTORY = ROOT / 'v2/reports/ibo-candidate-inventory.jsonl'
UA = 'MADSC55-TV-V2-RealScanner/1.0'
MAX_SOURCE = 25_000_000
TURKISH_BACKUP_PRIORITY = ("BBC FİRST TURKİYE", "CARTOON NETWORK (TURKİYE)", "KANAL 7", "KANAL 7 AVRUPA", "KANAL 7 AVRUPA HD TR", "KANAL AVRUPA TR", "SHOW TV", "TRT 3 (720P)", "TRT COCUK (1440P)", "TRT EBA ILKOKUL (720P)", "TRT EBA LİSE (720P)", "TRT SPOR YİLDİZ (1440P) [GEO-BLOCKED]", "TRT TURK TR")



def fetch(url, timeout=18, limit=MAX_SOURCE):
    """Retry transient source failures without silently accepting partial downloads."""
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError('Source exceeded size limit')
                return data
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in (408, 429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(1 + attempt * 2)


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
            outcome = probe(url, timeout=timeout)
            if outcome['status'] == 'AV_VERIFIED':
                return entry
    except (OSError, TimeoutError, urllib.error.URLError, ValueError,
            http.client.IncompleteRead, http.client.HTTPException):
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sources', type=pathlib.Path, default=SOURCES)
    ap.add_argument('--dynamic-sources', type=pathlib.Path, default=None,
                    help='Optional GitHub discovery report; only parsed HTTPS M3U sources are included')
    ap.add_argument('--output', type=pathlib.Path, default=OUT)
    ap.add_argument('--report', type=pathlib.Path, default=REPORT)
    ap.add_argument('--inventory', type=pathlib.Path, default=INVENTORY,
                    help='Durable full candidate inventory, including HTTP/HLS failures')
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--timeout', type=float, default=12)
    ap.add_argument('--limit', type=int, default=2000)
    ap.add_argument('--live', type=pathlib.Path, default=LIVE)
    args = ap.parse_args()
    if len(os.environ.get('V2_ARCHIVE_PASSPHRASE', '')) < 16:
        ap.error('V2_ARCHIVE_PASSPHRASE must contain at least 16 characters')
    if not 1 <= args.workers <= 32 or not 1 <= args.limit <= 10000:
        ap.error('workers must be 1..32 and limit 1..10000')
    if not args.live.is_file():
        ap.error('Protected V2 main playlist not found; refusing unfiltered export')
    live_text = args.live.read_text(encoding='utf-8-sig', errors='replace')
    main_urls = {line.strip() for line in live_text.splitlines()
                if line.strip().startswith(('https://', 'http://'))}
    if not main_urls:
        ap.error('Protected main playlist contains no stream URLs; refusing unfiltered export')
    # Previously rejected foreign YEDEKLER entries are retained in a separate
    # archive, but must never be rediscovered as new Turkish IBO test candidates.
    foreign_archive = ROOT / 'v2/arsiv/yabanci_yedekler_2026-11-02_3964.m3u8'
    if not foreign_archive.is_file():
        ap.error('Protected foreign archive missing; refusing unfiltered export')
    foreign_entries = list(parse_m3u(foreign_archive.read_bytes()))
    foreign_urls = {entry['url'] for entry in foreign_entries}
    if len(foreign_entries) != 3964:
        ap.error('Foreign archive integrity failed; expected 3964 preserved entries')
    existing = main_urls | foreign_urls
    # A backup is not a fresh discovery simply because it moved to an archive.
    # Preserve this exclusion when comparing the current main playlist.

    doc = json.loads(args.sources.read_text(encoding='utf-8'))
    sources = list(doc['sources'] if isinstance(doc, dict) else doc)
    dynamic_count = 0
    if args.dynamic_sources is not None:
        dynamic = json.loads(args.dynamic_sources.read_text(encoding='utf-8'))
        if not isinstance(dynamic.get('sources'), list):
            ap.error('Dynamic discovery report has no sources list')
        seen_source_urls = {item['url'] for item in sources}
        for item in dynamic['sources']:
            url = item.get('url', '')
            parsed = urllib.parse.urlsplit(url)
            if (item.get('status') != 'SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED'
                    or parsed.scheme != 'https' or not parsed.hostname or parsed.username
                    or parsed.password or url in seen_source_urls):
                continue
            sources.append({'id': 'github-auto-' + hashlib.sha256(url.encode()).hexdigest()[:20],
                            'url': url, 'scope': 'candidate'})
            seen_source_urls.add(url)
            dynamic_count += 1
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
                        found = candidates.get(entry['url'])
                        if found is None:
                            candidates[entry['url']] = {**entry, 'source_ids': [sid]}
                        elif sid not in found['source_ids']:
                            found['source_ids'].append(sid)
        except (OSError, ValueError, UnicodeError, socket.timeout) as exc:
            failed.append({'id': sid, 'error': type(exc).__name__})
    # Compare source yields with the last complete scan before replacing its baseline.
    source_drops = []
    if args.report.exists():
        try:
            prior_report = json.loads(args.report.read_text(encoding='utf-8'))
            if not prior_report.get('failed_sources') and not prior_report.get('source_drops'):
                for sid, prior in prior_report.get('source_counts', {}).items():
                    current = source_counts.get(sid)
                    if isinstance(prior, int) and prior >= 20 and current is not None and current < prior * 0.5:
                        source_drops.append({'id': sid, 'previous': prior, 'current': current})
        except (OSError, ValueError, TypeError):
            pass
    incomplete = bool(failed or source_drops)
    # Carry forward historical candidates from the last encrypted inventory.
    # Missing streams are retained for rechecking, never silently dropped.
    previous_encrypted = args.inventory.with_suffix(args.inventory.suffix + '.enc')
    recovered_from_archive = 0
    historical_records = {}
    if previous_encrypted.exists():
        previous_data = decrypt_inventory(previous_encrypted.read_bytes(),
                                          os.environ['V2_ARCHIVE_PASSPHRASE'])
        for line in previous_data.splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            url = record.get('url')
            if not isinstance(url, str) or url in existing:
                continue
            parsed = urllib.parse.urlsplit(url)
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                    or parsed.username or parsed.password):
                continue
            historical_records[url] = record
            if url in candidates:
                current = candidates[url]
                for sid in record.get('source_ids', []):
                    if sid not in current['source_ids']:
                        current['source_ids'].append(sid)
                for key in ('name', 'group', 'tvg_id', 'logo'):
                    if not current.get(key) and record.get(key):
                        current[key] = record[key]
                continue
            candidates[url] = {key: record.get(key, '') for key in ('name', 'group', 'tvg_id', 'logo')}
            candidates[url]['url'] = url
            candidates[url]['source_ids'] = record.get('source_ids', ['historical-archive'])
            recovered_from_archive += 1
    checked = 0
    good = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda x: check_hls(x, args.timeout), candidates.values()):
            checked += 1
            if result is not None:
                good.append(result)
    # Retain every discovered new URL, including candidates that failed HTTP/HLS.
    # Network checks are not device playback proof; never silently lose a candidate.
    good_urls = {item['url'] for item in good}
    args.inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory_tmp = args.inventory.with_suffix(args.inventory.suffix + '.tmp')
    # Restrict the temporary plaintext inventory before writing any URL tokens.
    fd = os.open(inventory_tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as inventory_file:
        for candidate in candidates.values():
            previous = historical_records.get(candidate['url'], {})
            old_observations = previous.get('observations', [])
            if not isinstance(old_observations, list):
                old_observations = []
            if not old_observations and previous.get('http_hls_status'):
                old_observations = [{'status': previous['http_hls_status'], 'origin': 'previous-inventory'}]
            new_status = 'AV_VERIFIED' if candidate['url'] in good_urls else 'UNVERIFIED_OR_FAILED'
            record = {**previous, **candidate,
                      'http_hls_status': new_status,
                      'ibo_device_tested': previous.get('ibo_device_tested', False),
                      'observations': old_observations + [{'status': new_status, 'origin': 'current-scan'}]}
            inventory_file.write(json.dumps(record, ensure_ascii=False) + '\n')
    # A failed source fetch must not overwrite the last complete encrypted baseline.
    encrypted_inventory = args.inventory.with_suffix(
        args.inventory.suffix + ('.pending.enc' if incomplete else '.enc'))
    try:
        archive_result = encrypt_inventory(inventory_tmp, encrypted_inventory,
                                           os.environ['V2_ARCHIVE_PASSPHRASE'])
    finally:
        inventory_tmp.unlink(missing_ok=True)
    # Never retain plaintext URL/token inventory in the GitHub working tree.
    # Source outages are reported; a working subset can still be tested.
    # Never modify the protected main playlist.
    report = {'source_count': len(sources), 'dynamic_source_count': dynamic_count, 'fetched_sources': len(source_counts),
              'failed_sources': failed, 'source_counts': source_counts, 'source_drops': source_drops, 'existing_main_urls': len(main_urls), 'excluded_foreign_archive_urls': len(foreign_urls), 'unique_new_candidates': len(candidates), 'recovered_from_previous_encrypted_inventory': recovered_from_archive,
              'http_checked': checked, 'http_hls_ok': len(good), 'av_verified': len(good),
              'candidate_inventory': str(encrypted_inventory), 'archive_restore_test_passed': archive_result['restore_test_passed'],
              'unverified_or_failed_candidates': len(candidates) - len(good),
              'multi_source_candidates': sum(len(item['source_ids']) > 1 for item in candidates.values()),
              'exported_part1': min(len(good), args.limit),
              'part_count': (len(good) + args.limit - 1) // args.limit,
              'playback_verified_on_device': False, 'mock_data_used': False,
              'status': 'READY_FOR_DEVICE_TEST' if good else 'NO_VERIFIED_CANDIDATES'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    # Never leave a prior successful batch in place after a failed/empty scan.
    # Remove stale generated exports before reporting this run's status.
    for previous in args.output.parent.glob(args.output.stem + '_PART*' + args.output.suffix):
        previous.unlink(missing_ok=True)
    args.output.unlink(missing_ok=True)
    if incomplete:
        report['status'] = 'INCOMPLETE_SOURCE_FETCH_OR_DROP'
        report['written_parts'] = []
        report['part_count'] = 0
        report['exported_part1'] = 0
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        raise SystemExit('Incomplete source fetch or source count collapse: refusing misleading IBO packages')
    if not good:
        # A completed scan with zero eligible streams is a valid no-change result.
        # Keep the report and original playlist intact; do not invent channels.
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    # Write every verified stream, not only the first batch. Never claim
    # additional parts exist unless they were actually written.
    written_parts = []
    for part_index, offset in enumerate(range(0, len(good), args.limit), 1):
        lines = ['#EXTM3U']
        for item in good[offset:offset + args.limit]:
            name = item['name'].replace('\n', ' ').replace('\r', ' ').replace(',', ' ').upper()
            group = item['group'].replace('"', '').replace('\n', ' ')
            logo = item.get('logo', '')
            logo_attr = f' tvg-logo="{logo}"' if logo.startswith(('https://', 'http://')) and '"' not in logo else ''
            lines.extend([f'#EXTINF:-1{logo_attr} group-title="{group}",{name}', item['url']])
        destination = (args.output if part_index == 1 else
                       args.output.with_name(args.output.stem + f'_PART{part_index}' + args.output.suffix))
        temp = destination.with_suffix(destination.suffix + '.tmp')
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        temp.replace(destination)
        written_parts.append(str(destination))
    report['written_parts'] = written_parts
    report['part_count'] = len(written_parts)
    report['exported_part1'] = min(len(good), args.limit)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

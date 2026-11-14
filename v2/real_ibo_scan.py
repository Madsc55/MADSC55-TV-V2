#!/usr/bin/env python3
"""Real-network IPTV candidate scanner; exports user-approved device test batches.
Not a replacement for v2/discover.py; can run beside the existing V2 engine.
No mock data, no invented URLs. HTTP/HLS checks are not playback proof.
"""
import argparse
import concurrent.futures
from collections import Counter
from datetime import datetime, timedelta, timezone
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
import xml.etree.ElementTree as ET
from stream_probe import probe, verify_decoded_av
from discovery_34 import identity
from stage3_identity_recovery import url_sha256
from stage3_metadata_acceptance import quality_from_probe, category, normalized_identity, epg_match
from stage3_recovery_queue import build_recovery_queue
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
                declared = response.headers.get('Content-Length')
                if declared is not None and declared.isdecimal():
                    expected = int(declared)
                    if len(data) < expected:
                        raise http.client.IncompleteRead(data, expected - len(data))
                    if len(data) > expected:
                        raise ValueError('Source length exceeds declared Content-Length')
                return data
        except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in (408, 425, 429, 500, 502, 503, 504):
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


def eligible_entry(entry, scope, worldwide=False):
    """Apply source scope unless explicit worldwide discovery is selected."""
    return bool(worldwide) or tr_az(entry, scope)


def public_http_stream_url(url):
    """Allow only parseable public HTTP(S) streams; never trust feed-supplied hosts."""
    if not isinstance(url, str) or "\\" in url:
        return False
    try:
        identity("m3u", url)
        parsed = urllib.parse.urlsplit(url)
        return parsed.scheme in ("http", "https") and not parsed.fragment
    except (ValueError, TypeError, AttributeError):
        return False


def public_https_m3u_feed(url):
    """Only publicly addressable HTTPS endpoints may become source feeds."""
    return public_http_stream_url(url) and urllib.parse.urlsplit(url).scheme == "https"


def normalize_integrated_m3u_sources(report, existing_sources):
    """Admit only candidate-only HTTPS M3U feed URLs from the unified discovery report."""
    if not isinstance(report, dict) or not isinstance(report.get("candidates"), list):
        raise ValueError("Integrated discovery report requires a candidates list")
    seen = {item.get("url") for item in existing_sources if isinstance(item, dict)}
    accepted, rejected = [], []
    for index, item in enumerate(report["candidates"]):
        if not isinstance(item, dict):
            rejected.append({"index": index, "error": "InvalidRecord"})
            continue
        if item.get("source") != "m3u":
            continue
        url = item.get("url")
        if (not isinstance(url, str) or item.get("verified_av") is not False):
            rejected.append({"index": index, "error": "InvalidCandidate"})
            continue
        if not public_https_m3u_feed(url) or url in seen:
            rejected.append({"index": index, "error": "RejectedSource"})
            continue
        sid = "integrated-m3u-" + hashlib.sha256(url.encode()).hexdigest()[:20]
        accepted.append({"id": sid, "url": url, "scope": "candidate"})
        seen.add(url)
    return accepted, rejected


def normalize_resolved_streams(report, existing_urls):
    """Admit only encrypted, live-metadata-confirmed direct HLS candidates."""
    if not isinstance(report, dict) or not isinstance(report.get("candidates"), list):
        raise ValueError("Resolved stream report requires a candidates list")
    seen = set(existing_urls)
    accepted, rejected = [], []
    for index, item in enumerate(report["candidates"]):
        if not isinstance(item, dict):
            rejected.append({"index": index, "error": "InvalidRecord"})
            continue
        source = item.get("source")
        source_id = item.get("source_id")
        url = item.get("url")
        if (source not in ("official", "youtube")
                or not isinstance(source_id, str)
                or not source_id.startswith(source + ":")
                or item.get("status") != "RESOLVED_DIRECT_HLS_NOT_AV_VERIFIED"
                or item.get("live_metadata_verified") is not True
                or item.get("verified_av") is not False):
            rejected.append({"index": index, "error": "InvalidEvidenceState"})
            continue
        try:
            identity("m3u", url)
        except (ValueError, TypeError, AttributeError):
            rejected.append({"index": index, "error": "InvalidDirectURL"})
            continue
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or url in seen:
            rejected.append({"index": index, "error": "RejectedDirectURL"})
            continue
        seen.add(url)
        accepted.append({
            "url": url,
            "name": str(item.get("name") or source_id)[:200],
            "region": str(item.get("region") or "WORLD")[:20],
            "country": str(item.get("country") or "")[:8],
            "group": str(item.get("group") or "")[:120],
            "tvg_id": str(item.get("tvg_id") or "")[:200],
            "logo": str(item.get("logo") or "")[:1000],
            "source_ids": [source_id],
        })
    return accepted, rejected


def check_hls(entry, timeout, diagnostics=None):
    """Return AV-verified stream or capture observed HTTP failure for recovery."""
    url = entry.get('url') if isinstance(entry, dict) else None
    if not public_http_stream_url(url):
        return None
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Range': 'bytes=0-4095'})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            status = res.status
            if diagnostics is not None:
                diagnostics['last_http_status'] = status
            content_type = res.headers.get('Content-Type', '').lower()
            sample = res.read(4096)
        hls = (b'#EXTM3U' in sample and (b'#EXT-X-' in sample or
               'mpegurl' in content_type))
        if status in (200, 206) and hls:
            outcome = probe(url, timeout=timeout)
            if (outcome.get('status') != 'AV_STREAMS_PRESENT'
                    or outcome.get('video') is not True
                    or outcome.get('audio') is not True):
                return None
            decoded = verify_decoded_av(url, timeout=timeout)
            if decoded.get('decoded_av_verified') is not True:
                if diagnostics is not None:
                    diagnostics['decode_status'] = decoded.get('decode_status', 'DECODE_NOT_VERIFIED')
                return None
            verified_outcome = {**outcome, 'status': 'AV_VERIFIED'}
            quality = quality_from_probe(verified_outcome)
            if quality['av_verified']:
                return {**entry, 'verified_quality': quality,
                        'decoded_av_verified': True,
                        'decode_status': decoded.get('decode_status', 'DECODED_AV')}
    except urllib.error.HTTPError as exc:
        if diagnostics is not None:
            diagnostics['last_http_status'] = exc.code
    except (OSError, TimeoutError, urllib.error.URLError, ValueError,
            http.client.IncompleteRead, http.client.HTTPException):
        if diagnostics is not None:
            diagnostics['last_timeout'] = True
    return None


def next_recovery_attempts(prior_attempts, *, reused, av_verified):
    """Count only newly executed network checks, never checkpoint replays.

    Reopening a sealed scan must not exhaust the three-attempt queue without
    actually retrying the stream. Actual AV success resets the counter.
    """
    if type(prior_attempts) is not int or prior_attempts < 0 or prior_attempts > 3:
        raise ValueError('Invalid historical recovery attempts')
    if type(reused) is not bool or type(av_verified) is not bool:
        raise ValueError('Invalid recovery evidence flags')
    return 0 if av_verified else min(prior_attempts + (0 if reused else 1), 3)


def observation_origin(*, reused):
    return 'resumed-checkpoint' if reused else 'current-scan'


def validated_xmltv_programme_ids(payload, *, now=None):
    """Accept EPG IDs only with one declaration and a real current programme.

    A <channel> declaration alone is not EPG schedule proof. The programme
    needs a title and a valid time interval in our 4-day candidate horizon.
    XMLTV remains an identity hint, not publisher ownership or AV evidence.
    """
    from epg_integrity import parse_xmltv_time
    if not isinstance(payload, bytes) or len(payload) > 100_000_000:
        raise ValueError("Invalid or oversized XMLTV input")
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("XMLTV DTD/entity declarations refused")
    root = ET.fromstring(payload)
    if root.tag != "tv":
        raise ValueError("XMLTV root must be tv")
    declared = Counter(node.get("id") for node in root.findall("channel")
                       if isinstance(node.get("id"), str) and node.get("id").strip())
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("A timezone-aware clock is required")
    valid = set()
    for programme in root.findall("programme"):
        cid = programme.get("channel")
        if not cid or declared[cid] != 1:
            continue
        title = programme.findtext("title") or ""
        if not title.strip():
            continue
        try:
            start = parse_xmltv_time(programme.get("start", ""))
            stop = parse_xmltv_time(programme.get("stop", ""))
        except (ValueError, TypeError, AttributeError):
            continue
        if stop > start and now - timedelta(hours=12) <= start <= now + timedelta(days=4):
            valid.add(cid)
    return valid


def recovery_http_status(status):
    """Normalize nonstandard network status codes at the strict recovery boundary.

    Keep the original HTTP observation in the encrypted inventory. A missing,
    malformed or out-of-range status remains UNKNOWN for recovery decisions,
    and never serves as evidence of successful AV playback.
    """
    return status if type(status) is int and 100 <= status <= 599 else None


def preserve_failed_recovery_evidence(plaintext_inventory, inventory_path, report_path,
                                      passphrase, *, error_type, checked,
                                      decoded_av_count, candidate_count):
    """Seal real scan observations before propagating a recovery-queue failure.

    Do not replace the last complete encrypted baseline. The pending archive
    contains private URLs; the public failure report contains only aggregates.
    """
    from secure_archive import backup
    pending = inventory_path.with_suffix(inventory_path.suffix + '.pending.enc')
    archive = backup(plaintext_inventory, pending, passphrase)
    failure_report = {
        'status': 'RECOVERY_QUEUE_FAILED',
        'failed_stage': 'build_recovery_queue',
        'error_type': error_type,
        'http_checked': checked,
        'decoded_av_verified_this_run': decoded_av_count,
        'unique_new_candidates': candidate_count,
        'candidate_inventory': str(pending),
        'archive_restore_test_passed': archive['restore_test_passed'],
        'playback_verified_on_device': False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(failure_report, sort_keys=True, indent=2) + '\n',
                           encoding='utf-8')
    return failure_report


def current_decode_confirmed(current_av, status, *, reused=False):
    """Only fresh successful frame decoding can certify an AV inventory row."""
    return (not reused and status == 'AV_VERIFIED' and isinstance(current_av, dict)
            and current_av.get('decoded_av_verified') is True
            and current_av.get('decode_status') == 'DECODED_AV')

def historical_source_ids(record):
    """Keep both legacy and current source identifiers without duplicates."""
    ids = record.get('source_ids', [])
    if not isinstance(ids, list):
        raise ValueError('Invalid historical source_ids')
    legacy = record.get('source_id')
    values = ids + ([legacy] if isinstance(legacy, str) and legacy else [])
    return list(dict.fromkeys(x for x in values if isinstance(x, str) and x)) or ['historical-archive']


def normalize_dynamic_sources(dynamic, existing_sources):
    """Validate optional discovery report rows before admitting HTTPS M3U feeds."""
    if not isinstance(dynamic, dict) or not isinstance(dynamic.get('sources'), list):
        raise ValueError('Dynamic discovery report must be an object with a sources list')
    seen = {item.get('url') for item in existing_sources if isinstance(item, dict)}
    accepted, rejected = [], []
    for index, item in enumerate(dynamic['sources']):
        if not isinstance(item, dict):
            rejected.append({'index': index, 'error': 'InvalidRecord'})
            continue
        url = item.get('url')
        if not isinstance(url, str):
            rejected.append({'index': index, 'error': 'InvalidURLType'})
            continue
        if (item.get('status') != 'SOURCE_PARSED_STREAMS_NOT_PLAYBACK_VERIFIED'
                or not public_https_m3u_feed(url) or url in seen):
            rejected.append({'index': index, 'error': 'RejectedSource'})
            continue
        sid = 'github-auto-' + hashlib.sha256(url.encode()).hexdigest()[:20]
        accepted.append({'id': sid, 'url': url, 'scope': 'candidate'})
        seen.add(url)
    return accepted, rejected


def classify_source_failures(failed, source_drops, configured_ids, *,
                             tolerate_discovery_errors=False):
    """Separate mandatory configured source outages from untrusted discoveries.

    Optional discovered feed outages are never silently accepted: their IDs
    stay in the public report as incomplete discovery. The full-discovery
    acceptance gate must remain open, even when configured-source AV testing
    can proceed safely.
    """
    if not isinstance(configured_ids, set):
        raise ValueError("Configured source identities must be a set")
    mandatory_failed, optional_failed = [], []
    mandatory_drops, optional_drops = [], []
    for record in failed:
        (optional_failed if tolerate_discovery_errors
         and record["id"] not in configured_ids else mandatory_failed).append(record)
    for record in source_drops:
        (optional_drops if tolerate_discovery_errors
         and record["id"] not in configured_ids else mandatory_drops).append(record)
    return mandatory_failed, optional_failed, mandatory_drops, optional_drops


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage2-offline-input', type=pathlib.Path, default=None,
                    help='Integrate existing observations without channel discovery or playback')
    ap.add_argument('--stage2-offline-output', type=pathlib.Path, default=None,
                    help='Optional offline JSON report output; no stream URLs')
    ap.add_argument('--sources', type=pathlib.Path, default=SOURCES)
    ap.add_argument('--dynamic-sources', type=pathlib.Path, default=None,
                    help='Optional GitHub/Gist discovery report; only parsed HTTPS M3U sources are included')
    ap.add_argument('--integrated-candidates', type=pathlib.Path, default=None,
                    help='Optional unified discovery report; only candidate-only M3U feed URLs are admitted')
    ap.add_argument('--resolved-streams', type=pathlib.Path, default=None,
                    help='Optional authenticated encrypted direct HLS candidates from official/YouTube resolvers')
    ap.add_argument('--resume-checkpoint', type=pathlib.Path, default=None,
                    help='Optional encrypted prior progress from a failed real AV scan')
    ap.add_argument('--checkpoint-every', type=int, default=100,
                    help='Seal encrypted progress after this many candidate observations')
    ap.add_argument('--fail-fast-source-errors', action='store_true',
                    help='Stop before hours of AV probing if any mandatory M3U source failed')
    ap.add_argument('--tolerate-optional-discovery-failures', action='store_true',
                    help='Quarantine inaccessible discovered feeds; report incomplete discovery without treating them as mandatory configured sources')
    ap.add_argument('--output', type=pathlib.Path, default=OUT)
    ap.add_argument('--report', type=pathlib.Path, default=REPORT)
    ap.add_argument('--inventory', type=pathlib.Path, default=INVENTORY,
                    help='Durable full candidate inventory, including HTTP/HLS failures')
    ap.add_argument('--epg', type=pathlib.Path, default=None,
                    help='Optional trusted local XMLTV file for exact tvg-id matching')
    ap.add_argument('--workers', type=int, default=12)
    ap.add_argument('--timeout', type=float, default=12)
    ap.add_argument('--limit', type=int, default=500)
    ap.add_argument('--worldwide', action='store_true', help='Include all public source entries instead of TR/AZ metadata filtering')
    ap.add_argument('--live', type=pathlib.Path, default=LIVE)
    args = ap.parse_args()
    if args.stage2_offline_input is not None:
        from stage2_integration import integrate
        payload = json.loads(args.stage2_offline_input.read_text(encoding='utf-8'))
        if not isinstance(payload, dict) or not isinstance(payload.get('records'), list):
            ap.error('Stage 2 offline input requires a records list')
        xmltv = args.epg.read_text(encoding='utf-8') if args.epg else None
        result = integrate(payload['records'], scopes=payload.get('scopes'),
                           xmltv_text=xmltv)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + chr(10)
        if args.stage2_offline_output:
            destination = args.stage2_offline_output.resolve()
            reports_dir = (ROOT / 'v2/reports').resolve()
            if destination.suffix.lower() != '.json' or reports_dir not in destination.parents:
                ap.error('Offline report must be a .json file inside v2/reports')
            if destination == args.stage2_offline_input.resolve():
                ap.error('Offline report must not overwrite its input')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(rendered, encoding='utf-8')
        else:
            print(rendered, end='')
        return
    # Live mode retains all existing protected-playlist and archive safety gates.
    from secure_archive import backup as encrypt_inventory, decrypt as decrypt_inventory
    if len(os.environ.get('V2_ARCHIVE_PASSPHRASE', '')) < 16:
        ap.error('V2_ARCHIVE_PASSPHRASE must contain at least 16 characters')
    if not 1 <= args.workers <= 32 or not 1 <= args.limit <= 10000 or not 1 <= args.checkpoint_every <= 1000:
        ap.error('workers must be 1..32, limit 1..10000, checkpoint-every 1..1000')
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
    configured_source_ids = {item['id'] for item in sources}
    dynamic_count = 0
    integrated_m3u_count = 0
    rejected_integrated_m3u = []
    if args.integrated_candidates is not None:
        integrated_report = json.loads(args.integrated_candidates.read_text(encoding='utf-8'))
        integrated_sources, rejected_integrated_m3u = normalize_integrated_m3u_sources(integrated_report, sources)
        sources.extend(integrated_sources)
        integrated_m3u_count = len(integrated_sources)
    rejected_dynamic_sources = []
    if args.dynamic_sources is not None:
        dynamic = json.loads(args.dynamic_sources.read_text(encoding='utf-8'))
        try:
            accepted_dynamic, rejected_dynamic_sources = normalize_dynamic_sources(dynamic, sources)
        except ValueError as exc:
            ap.error(str(exc))
        sources.extend(accepted_dynamic)
        dynamic_count = len(accepted_dynamic)
    # Do not export incomplete results as a successful production list.
    candidates = {}
    failed = []
    source_counts = {}
    for source in sources:
        sid, url = source['id'], source['url']
        if not public_https_m3u_feed(url):
            failed.append({'id': sid, 'error': 'InvalidPublicHTTPSSource'}); continue
        try:
            records = list(parse_m3u(fetch(url, args.timeout)))
            source_counts[sid] = len(records)
            for entry in records:
                if (eligible_entry(entry, source.get('scope', 'candidate'), args.worldwide)
                        and public_http_stream_url(entry['url'])):
                    if entry['url'] not in existing:
                        found = candidates.get(entry['url'])
                        if found is None:
                            candidates[entry['url']] = {**entry, 'source_ids': [sid]}
                        elif sid not in found['source_ids']:
                            found['source_ids'].append(sid)
        except (OSError, ValueError, UnicodeError, socket.timeout) as exc:
            # Preserve actionable, non-sensitive failure classification in the
            # uploaded report. Never include exception text: it may contain
            # authenticated URLs or credentials from a discovered feed.
            failure = {'id': sid, 'error': type(exc).__name__}
            if isinstance(exc, urllib.error.HTTPError):
                failure['http_status'] = exc.code
            elif isinstance(exc, ValueError):
                if str(exc) == 'Not an M3U playlist':
                    failure['reason'] = 'INVALID_M3U_FORMAT'
                elif str(exc) == 'Source exceeded size limit':
                    failure['reason'] = 'SOURCE_SIZE_LIMIT'
                elif str(exc) == 'Source length exceeds declared Content-Length':
                    failure['reason'] = 'CONTENT_LENGTH_MISMATCH'
            failed.append(failure)
    resolved_direct_count = 0
    rejected_resolved_direct = []
    if args.resolved_streams is not None:
        encrypted_direct = args.resolved_streams.read_bytes()
        direct_report = json.loads(decrypt_inventory(
            encrypted_direct, os.environ["V2_ARCHIVE_PASSPHRASE"]))
        direct_candidates, rejected_resolved_direct = normalize_resolved_streams(
            direct_report, existing)
        for item in direct_candidates:
            url = item["url"]
            current = candidates.get(url)
            if current is None:
                candidates[url] = item
            else:
                for source_id in item["source_ids"]:
                    if source_id not in current["source_ids"]:
                        current["source_ids"].append(source_id)
        resolved_direct_count = len(direct_candidates)
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
    (mandatory_failed_sources, optional_failed_sources,
     mandatory_source_drops, optional_source_drops) = classify_source_failures(
        failed, source_drops, configured_source_ids,
        tolerate_discovery_errors=args.tolerate_optional_discovery_failures)
    # Configured-source completeness is a hard gate. Dynamically discovered
    # feeds are untrusted candidates that can disappear between API discovery
    # and fetch. Their failures are recorded separately and cannot certify
    # complete discovery or publisher provenance.
    incomplete = bool(mandatory_failed_sources or mandatory_source_drops)
    discovery_partial = bool(optional_failed_sources or optional_source_drops)
    if incomplete and args.fail_fast_source_errors:
        # Full acceptance is impossible without all mandatory sources.
        # Report the source problem now rather than spending hours on AV probes
        # that cannot be exported. A separately downloaded prior checkpoint is
        # still included in the always-uploaded evidence artifact.
        args.report.parent.mkdir(parents=True, exist_ok=True)
        early_report = {
            'status': 'INCOMPLETE_SOURCE_FETCH_EARLY',
            'scan_scope': 'WORLDWIDE_ALL_SOURCE_ENTRIES' if args.worldwide else 'TR_AZ_METADATA_CANDIDATES',
            'source_count': len(sources), 'source_counts': source_counts,
            'fetched_sources': len(source_counts), 'failed_sources': failed,
            'mandatory_failed_sources': mandatory_failed_sources,
            'optional_failed_discovered_sources': optional_failed_sources,
            'source_drops': source_drops, 'mandatory_source_drops': mandatory_source_drops,
            'optional_discovery_source_drops': optional_source_drops,
            'discovery_partial': discovery_partial,
            'unique_new_candidates': len(candidates),
            'http_checked': 0, 'av_verified': 0,
            'playback_verified_on_device': False, 'mock_data_used': False,
            'no_new_av_probes_because_source_incomplete': True,
        }
        args.report.write_text(json.dumps(early_report, indent=2, ensure_ascii=False) + '\n',
                               encoding='utf-8')
        raise SystemExit('Incomplete mandatory source fetch: stopped before expensive AV probing')
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
                historical_sources = historical_source_ids(record)
                for sid in historical_sources:
                    if sid not in current['source_ids']:
                        current['source_ids'].append(sid)
                for key in ('name', 'group', 'tvg_id', 'logo'):
                    if not current.get(key) and record.get(key):
                        current[key] = record[key]
                continue
            candidates[url] = {key: record.get(key, '') for key in ('name', 'group', 'tvg_id', 'logo')}
            candidates[url]['url'] = url
            candidates[url]['source_ids'] = historical_source_ids(record)
            recovered_from_archive += 1
    # Resume is bound to the exact stream URL, authentic AES ciphertext and a
    # short evidence lifetime. Previous AV proof remains tagged as previous-run
    # evidence; it is never labeled as a new FFmpeg decode in this invocation.
    from scan_checkpoint import checkpoint_row, load_progress, save_progress
    checkpoint_path = args.inventory.parent / 'ibo-scan-progress.enc'
    prior_progress = (load_progress(
        args.resume_checkpoint, os.environ['V2_ARCHIVE_PASSPHRASE'],
        worldwide=args.worldwide) if args.resume_checkpoint is not None else {})
    progress_rows = {}
    resumed_urls = set()
    resumed_verified_urls = set()
    checked = 0
    good = []
    diagnostics_by_url = {}
    def inspect_candidate(candidate):
        url = candidate['url']
        prior = prior_progress.get(url)
        if prior is not None:
            previous = prior['result']
            result = ({**candidate, **previous} if previous is not None else None)
            return url, result, prior['diagnostics'], True, prior['checked_at']
        diagnostics = {}
        result = check_hls(candidate, args.timeout, diagnostics)
        return url, result, diagnostics, False, time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for url, result, diagnostics, reused, checked_at in pool.map(
                inspect_candidate, candidates.values()):
            checked += 1
            diagnostics_by_url[url] = diagnostics
            if result is not None:
                good.append(result)
            if reused:
                resumed_urls.add(url)
                if result is not None:
                    resumed_verified_urls.add(url)
            previous_attempts = prior_progress.get(url, {}).get(
                'recovery_attempts', historical_records.get(url, {}).get('recovery_attempts', 0))
            next_attempts = next_recovery_attempts(
                previous_attempts, reused=reused, av_verified=result is not None)
            progress_rows[url] = checkpoint_row(
                url, result, diagnostics, checked_at=checked_at,
                recovery_attempts=next_attempts)
            if checked % args.checkpoint_every == 0:
                save_progress(checkpoint_path, os.environ['V2_ARCHIVE_PASSPHRASE'],
                              worldwide=args.worldwide, rows=progress_rows)
    # Seal the last partial batch before XMLTV, recovery queue, or export.
    save_progress(checkpoint_path, os.environ['V2_ARCHIVE_PASSPHRASE'],
                  worldwide=args.worldwide, rows=progress_rows)
    epg_ids = set()
    epg_checked = args.epg is not None
    if args.epg is not None:
        # A mere XMLTV channel declaration is NOT evidence of EPG availability.
        # Verify a unique channel declaration, valid timed programme and title.
        if args.epg.is_symlink() or not args.epg.is_file():
            ap.error('Refusing missing or symlinked XMLTV candidate')
        if args.epg.stat().st_size > 100_000_000:
            ap.error('XMLTV input exceeds 100 MB limit')
        epg_ids = validated_xmltv_programme_ids(args.epg.read_bytes())
    # Retain every discovered new URL, including candidates that failed HTTP/HLS.
    # Network checks are not device playback proof; never silently lose a candidate.
    good_urls = {item['url'] for item in good}
    good_by_url = {item['url']: item for item in good}
    args.inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory_tmp = args.inventory.with_suffix(args.inventory.suffix + '.tmp')
    # Refuse to follow a symlink when creating the plaintext temporary file.
    # A stale temporary file is removed only if it is an ordinary file.
    if inventory_tmp.is_symlink():
        raise ValueError('Refusing symlinked plaintext inventory path')
    # Restrict the temporary plaintext inventory before writing any URL tokens.
    try:
        fd = os.open(inventory_tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        recovery_records = []
        nonstandard_http_status_count = 0
        with os.fdopen(fd, 'w', encoding='utf-8') as inventory_file:
            for candidate in candidates.values():
                previous = historical_records.get(candidate['url'], {})
                old_observations = previous.get('observations', [])
                if not isinstance(old_observations, list):
                    old_observations = []
                if not old_observations and previous.get('http_hls_status'):
                    old_observations = [{'status': previous['http_hls_status'], 'origin': 'previous-inventory'}]
                new_status = 'AV_VERIFIED' if candidate['url'] in good_urls else 'UNVERIFIED_OR_FAILED'
                current_av = good_by_url.get(candidate['url'], {})
                verified = current_av.get('verified_quality', {})
                decoded_this_run = current_decode_confirmed(
                    current_av, new_status, reused=candidate['url'] in resumed_urls)
                # The checkpoint already reflects the actual probe (or no probe
                # when reused). Do not increment recovery attempts a second time.
                recovery_attempts = progress_rows[candidate['url']]['recovery_attempts']
                record = {**previous, **candidate,
                          'recovery_attempts': recovery_attempts,
                          'last_http_status': diagnostics_by_url.get(candidate['url'], {}).get('last_http_status'),
                          'last_timeout': diagnostics_by_url.get(candidate['url'], {}).get('last_timeout', False),
                          'url_sha256': url_sha256(candidate['url']),
                          'category': category(candidate) if category(candidate) != 'UNCATEGORIZED' else previous.get('category', 'UNCATEGORIZED'),
                          'identity': normalized_identity({**previous, **candidate}),
                          'epg_exact_match': (bool(candidate.get('tvg_id') and candidate['tvg_id'].strip() in epg_ids and epg_match(candidate, {'channel': candidate['tvg_id'].strip()})) if epg_checked else previous.get('epg_exact_match')),
                          'epg_checked': epg_checked or previous.get('epg_checked', False),
                          'verified_quality': verified if verified.get('av_verified') else previous.get('verified_quality', {'av_verified': False, 'quality': 'UNVERIFIED'}),
                          'http_hls_status': new_status,
                          'decoded_av_verified': decoded_this_run,
                          'decode_status': ('DECODED_AV' if decoded_this_run else
                                            'DECODED_AV_PRIOR_CHECKPOINT' if candidate['url'] in resumed_verified_urls else
                                            'NOT_DECODED_THIS_RUN'),
                          'ibo_device_tested': previous.get('ibo_device_tested', False),
                          'observations': old_observations + [{
                              'status': new_status, 'origin': observation_origin(
                                  reused=candidate['url'] in resumed_urls)}]}
                inventory_file.write(json.dumps(record, ensure_ascii=False) + '\n')
                if candidate['url'] not in good_urls:
                    raw_http_status = diagnostics_by_url.get(candidate['url'], {}).get('last_http_status')
                    queue_http_status = recovery_http_status(raw_http_status)
                    if raw_http_status is not None and queue_http_status is None:
                        nonstandard_http_status_count += 1
                    recovery_records.append({'url': candidate['url'],
                                             'last_http_status': queue_http_status,
                                             'last_timeout': diagnostics_by_url.get(candidate['url'], {}).get('last_timeout', False),
                                             'recovery_attempts': recovery_attempts,
                                             'observations': record['observations']})
        # Queue contains SHA identities only; no stream URL or token in public report.
        try:
            recovery_queue = build_recovery_queue(recovery_records)
        except (ValueError, TypeError, KeyError) as exc:
            # A long real AV scan must never lose its observations just because
            # downstream queue validation failed. Preserve only an encrypted
            # PENDING artifact; keep the last complete baseline untouched.
            preserve_failed_recovery_evidence(
                inventory_tmp, args.inventory, args.report,
                os.environ['V2_ARCHIVE_PASSPHRASE'],
                error_type=type(exc).__name__, checked=checked,
                decoded_av_count=len(good), candidate_count=len(candidates))
            raise
        # A failed source fetch must not overwrite the last complete encrypted baseline.
        encrypted_inventory = args.inventory.with_suffix(
            args.inventory.suffix + ('.pending.enc' if (incomplete or discovery_partial) else '.enc'))
        archive_result = encrypt_inventory(inventory_tmp, encrypted_inventory,
                                           os.environ['V2_ARCHIVE_PASSPHRASE'])
    finally:
        inventory_tmp.unlink(missing_ok=True)
    # Never retain plaintext URL/token inventory in the GitHub working tree.
    # Source outages are reported; a working subset can still be tested.
    # Never modify the protected main playlist.
    report = {'scan_scope': 'WORLDWIDE_ALL_SOURCE_ENTRIES' if args.worldwide else 'TR_AZ_METADATA_CANDIDATES', 'source_count': len(sources), 'dynamic_source_count': dynamic_count, 'rejected_dynamic_sources': rejected_dynamic_sources, 'integrated_m3u_source_count': integrated_m3u_count, 'rejected_integrated_m3u_sources': rejected_integrated_m3u,
              'resolved_direct_candidate_count': resolved_direct_count, 'rejected_resolved_direct_candidates': rejected_resolved_direct, 'fetched_sources': len(source_counts),
              'failed_sources': failed, 'source_counts': source_counts, 'source_drops': source_drops,
              'mandatory_failed_sources': mandatory_failed_sources,
              'optional_failed_discovered_sources': optional_failed_sources,
              'mandatory_source_drops': mandatory_source_drops,
              'optional_discovery_source_drops': optional_source_drops,
              'discovery_partial': discovery_partial,
              'configured_sources_complete': not incomplete,
              'full_discovery_acceptance': not (incomplete or discovery_partial),
              'epg_checked': epg_checked,
              'epg_valid_programme_channel_ids': len(epg_ids),
              'existing_main_urls': len(main_urls), 'excluded_foreign_archive_urls': len(foreign_urls), 'unique_new_candidates': len(candidates), 'recovered_from_previous_encrypted_inventory': recovered_from_archive,
              'http_checked': checked, 'http_checked_this_run': checked - len(resumed_urls),
              'resumed_checkpoint_observations': len(resumed_urls),
              'resumed_decoded_av_evidence': len(resumed_verified_urls),
              'av_verified_this_run': len(good) - len(resumed_verified_urls),
              'http_hls_ok': len(good), 'av_verified': len(good),
              'recovery_queue': recovery_queue,
              'recovery_retry_count': sum(item['action'] == 'RETRY' for item in recovery_queue),
              'recovery_av_check_count': sum(item['action'] == 'CHECK_AV' for item in recovery_queue),
              'recovery_manual_review_count': sum(item['action'] == 'REVIEW' for item in recovery_queue),
              'recovery_nonstandard_http_status_count': nonstandard_http_status_count,
              'candidate_inventory': str(encrypted_inventory), 'archive_restore_test_passed': archive_result['restore_test_passed'],
              'unverified_or_failed_candidates': len(candidates) - len(good),
              'multi_source_candidates': sum(len(item['source_ids']) > 1 for item in candidates.values()),
              'exported_part1': min(len(good), args.limit),
              'part_count': (len(good) + args.limit - 1) // args.limit,
              'playback_verified_on_device': False, 'mock_data_used': False,
              'status': ('PARTIAL_DISCOVERY_READY_FOR_DEVICE_TEST' if good else 'PARTIAL_DISCOVERY_NO_VERIFIED_CANDIDATES') if discovery_partial
                        else ('READY_FOR_DEVICE_TEST' if good else 'NO_VERIFIED_CANDIDATES')}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if discovery_partial and not incomplete:
        # Keep all real observations encrypted, but do not promote partial
        # discovery into a complete baseline or M3U package. The next run
        # can resume from the sealed per-URL checkpoint.
        report['status'] = 'PARTIAL_DISCOVERY_EVIDENCE_ONLY'
        report['written_parts'] = []
        report['part_count'] = 0
        report['exported_part1'] = 0
        args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'],
                          'configured_sources_complete': True,
                          'optional_failed_discovered_sources': optional_failed_sources,
                          'http_checked': checked,
                          'av_verified': len(good),
                          'full_discovery_acceptance': False},
                         ensure_ascii=False))
        return
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
    # Only a complete scan may replace previously published test exports.
    # Do not destroy the last successful batch when a source is unavailable.
    for previous in args.output.parent.glob(args.output.stem + '_PART*' + args.output.suffix):
        previous.unlink(missing_ok=True)
    args.output.unlink(missing_ok=True)
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

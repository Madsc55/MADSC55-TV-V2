#!/usr/bin/env python3
"""Conservative HTTP maintenance of the ONE canonical playlist; fail closed."""
import argparse
import concurrent.futures
import hashlib
from http.client import HTTPException
import ipaddress
import json
import os
from pathlib import Path
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

PLAYLIST = Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
QUARANTINE = Path("archive/historical_http_404_503_quarantine.json")
REPORT = Path("v2/reports/main-playlist-live-health-latest.json")
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
OPENER = build_opener(NoRedirect)

def public_url(url):
    try:
        p = urlsplit(url)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
            return False
        if p.port not in (None, 80, 443, 8080, 8443):
            return False
        addrs = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM)
        return bool(addrs) and all(ipaddress.ip_address(a[4][0]).is_global for a in addrs)
    except (ValueError, OSError):
        return False

def check(url):
    # DNS is checked before each request. Do not follow redirects to internal hosts.
    if not public_url(url):
        return "blocked"
    outcomes = []
    for attempt in range(2):
        try:
            req = Request(url, headers={"User-Agent": "MADSC55-TV-Health/1.0", "Range": "bytes=0-2047"})
            with OPENER.open(req, timeout=3) as response:
                status = response.status
                response.read(2048)
        except HTTPError as e:
            status = e.code
        except (URLError, TimeoutError, OSError, ValueError, HTTPException):
            return "unknown"
        if status == 429:
            return "rate_limited"
        if status in (301, 302, 303, 307, 308):
            return "unknown"
        outcomes.append(status)
        if attempt == 0:
            time.sleep(3)
    if outcomes == [404, 404]:
        return "confirmed_404"
    if all(200 <= code < 300 for code in outcomes):
        return "live"
    return "unknown"

def parse(raw):
    lines = raw.splitlines(keepends=True)
    if not lines or lines[0].strip() != "#EXTM3U":
        raise ValueError("missing EXTM3U")
    records = []
    prefix = [lines[0]]
    i = 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF:"):
            if i + 1 >= len(lines) or not lines[i+1].strip() or lines[i+1].startswith("#"):
                raise ValueError("EXTINF missing URL")
            url = lines[i+1].strip()
            if not urlsplit(url).scheme in ("http", "https"):
                raise ValueError("unsupported stream URL")
            records.append((line, lines[i+1], url))
            i += 2
        else:
            if records:
                raise ValueError("unexpected playlist line after stream")
            prefix.append(line)
            i += 1
    return prefix, records

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    before = PLAYLIST.read_text(encoding="utf-8")
    prefix, records = parse(before)
    quarantined = json.loads(QUARANTINE.read_text(encoding="utf-8"))["entries"]
    flagged = {e["url_sha256"] for e in quarantined}
    # Scan existing streams; historical 503 is never deletion evidence.
    unique = list(dict.fromkeys(url for _, _, url in records))
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max(args.workers, 1), 4)) as pool:
        futures = {pool.submit(check, url): url for url in unique}
        for future in concurrent.futures.as_completed(futures):
            try:
                results[futures[future]] = future.result()
            except Exception:
                # A malformed or truncated response must never abort the full
                # read-only report or be interpreted as deletion evidence.
                results[futures[future]] = "unknown"
    # Preserve all category/order metadata and every 685 SECURITY HOLD entry.
    # No candidates promoted: there is no independently attested unlock inventory.
    remove = {url for url, state in results.items() if state == "confirmed_404" and hashlib.sha256(url.encode()).hexdigest() not in flagged}
    # Previously quarantined 404s require explicit independent confirmation; two checks are insufficient to override quarantine.
    new = "".join(prefix + [part for inf, stream, url in records if url not in remove for part in (inf, stream)])
    _, after = parse(new)
    assert len(after) == len(records) - sum(url in remove for _, _, url in records)
    assert [inf for inf, stream, url in records if url not in remove] == [inf for inf, _, _ in after]
    report = {"before": len(records), "removed": len(records)-len(after), "added": 0, "after": len(after), "checked_unique": len(unique), "states": {k: list(results.values()).count(k) for k in sorted(set(results.values()))}, "quarantine_hashes": len(flagged), "security_hold_released": 0}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    if args.apply and remove:
        PLAYLIST.write_text(new, encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()

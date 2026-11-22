#!/usr/bin/env python3
"""Conservative HTTP maintenance of the ONE canonical playlist; fail closed."""
import argparse
import concurrent.futures
import hashlib
import re
from collections import Counter
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
REPORT = Path("reports/latest_http_health.json")
DEAD = Path("reports/DEAD_URLS.txt")
CANDIDATES = Path("reports/new_source_candidates.json")
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
        return {"state": "blocked", "http_codes": ["blocked"]}
    outcomes = []
    for attempt in range(2):
        try:
            req = Request(url, headers={"User-Agent": "MADSC55-TV-Health/1.0", "Range": "bytes=0-2047"})
            with OPENER.open(req, timeout=3) as response:
                status = response.status
                response.read(2048)
        except HTTPError as e:
            status = e.code
        except (URLError, TimeoutError, OSError, ValueError, HTTPException) as exc:
            outcomes.append("timeout" if isinstance(exc, (TimeoutError,)) or "timed out" in str(exc).lower() else "network_error")
            break
        if status == 429:
            return {"state": "rate_limited", "http_codes": outcomes + [429]}
        if status in (301, 302, 303, 307, 308):
            return {"state": "unknown", "http_codes": outcomes + [status]}
        outcomes.append(status)
        if attempt == 0:
            time.sleep(3)
    state = "confirmed_404" if outcomes == [404, 404] else ("live" if len(outcomes) == 2 and all(isinstance(code, int) and 200 <= code < 300 for code in outcomes) else "unknown")
    return {"state": state, "http_codes": outcomes}

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
    ap.add_argument("--apply", action="store_true")\n    # Legacy flag accepted for compatibility; writes to playlist are disabled.
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    before = PLAYLIST.read_text(encoding="utf-8")
    prefix, records = parse(before)
    quarantined = json.loads(QUARANTINE.read_text(encoding="utf-8"))["entries"]
    flagged = {e["url_sha256"] for e in quarantined}
    # Report each playlist entry, including duplicates, in original order.
    unique = list(dict.fromkeys(url for _, _, url in records))
    candidates = []
    if CANDIDATES.exists():
        payload = json.loads(CANDIDATES.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("candidate inventory must be a JSON list")
        for item in payload:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str):
                raise ValueError("candidate must include url")
            candidates.append(item)
    candidate_urls = [item["url"] for item in candidates if item["url"] not in unique]
    all_urls = list(dict.fromkeys(unique + candidate_urls))
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(max(args.workers, 1), 4)) as pool:
        futures = {pool.submit(check, url): url for url in all_urls}
        for future in concurrent.futures.as_completed(futures):
            try:
                results[futures[future]] = future.result()
            except Exception:
                results[futures[future]] = {"state": "unknown", "http_codes": ["probe_error"]}
    def metadata(inf):
        name = inf.rstrip("\\r\\n").rsplit(",", 1)[-1]
        match = re.search(r'group-title="([^"]*)"', inf)
        return name, match.group(1) if match else ""
    entries = []
    line_number = 1
    for inf, stream, url in records:
        line_number += 1
        name, group = metadata(inf)
        entries.append({"line_number": line_number, "channel_name": name, "group_title": group,
                        "url": url, **results[url], "historical_quarantine": hashlib.sha256(url.encode()).hexdigest() in flagged})
        line_number += 1
    candidate_results = []
    for item in candidates:
        url = item["url"]
        candidate_results.append({"channel_name": item.get("name", ""), "group_title": item.get("group_title", ""),
                                  "url": url, **results[url], "eligible_for_review": results[url]["state"] == "live" and url not in unique})
    # 404 is a candidate for manual review, not authorization to remove 685 security holds.
    dead = sorted({e["url"] for e in entries if e["state"] == "confirmed_404" and not e["historical_quarantine"]})
    report = {"schema_version": 2, "read_only": True, "before": len(records),
              "checked_unique": len(all_urls), "states": dict(Counter(x["state"] for x in results.values())),
              "confirmed_404_review_count": len(dead), "candidate_count": len(candidate_results),
              "security_hold_released": 0, "entries": entries, "new_source_candidates": candidate_results}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    DEAD.write_text("".join(url + "\\n" for url in dead), encoding="utf-8")
    # This script never changes the canonical playlist, even with --apply.
    print(json.dumps({k: v for k, v in report.items() if k not in ("entries", "new_source_candidates")}, ensure_ascii=False))

if __name__ == "__main__":
    main()

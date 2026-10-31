#!/usr/bin/env python3
"""Offline, deterministic promotion of vetted public forge M3U sources.

Never guesses TR/AZ from search terms. Every forge result starts as candidate,
and URLs are only promoted after a separate, explicit review. No playlist writes.
"""
import hashlib
import json
from urllib.parse import urlsplit
from webpage_source_discovery import candidate_url, public_hostname

def valid_forge_source(url):
    try:
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname or not public_hostname(p.hostname):
            return False
        if p.username or p.password or p.port not in (None, 443) or p.fragment:
            return False
        if candidate_url(url):
            return True
        return (p.hostname == "gitlab.com"
                and p.path.startswith("/api/v4/projects/")
                and "/repository/files/" in p.path
                and p.path.endswith("/raw")
                and "ref=" in p.query)
    except ValueError:
        return False

def normalize(report):
    if report.get("schema") != 1:
        raise ValueError("Unknown forge discovery schema")
    sources, seen = [], set()
    for record in report.get("sources", [])[:500]:
        if not isinstance(record, dict):
            continue
        url = record.get("source_url", "")
        if not isinstance(url, str) or not valid_forge_source(url) or url in seen:
            continue
        seen.add(url)
        sources.append({"id": "forge-auto-" + hashlib.sha256(url.encode()).hexdigest()[:20],
                        "url": url, "scope": "candidate",
                        "kind": "m3u", "origin": record.get("forge", "unknown")})
    return sources

def approved_sources(report, approved_hashes):
    """Explicit SHA256 approvals prevent a forged or new source from auto-promoting."""
    return [source for source in normalize(report)
            if hashlib.sha256(source["url"].encode()).hexdigest() in approved_hashes]

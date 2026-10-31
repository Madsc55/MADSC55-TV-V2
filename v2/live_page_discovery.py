#!/usr/bin/env python3
"""Extract public official live-page references; never infer direct IPTV playback.

YouTube watch/live URLs are discovery metadata, not HLS/DASH URLs.
Only explicitly linked HTTPS pages are considered. No DRM or login bypass.
"""
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, parse_qs
from webpage_source_discovery import public_hostname

MAX_LINKS = 1000
class LiveLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() not in ("a", "link"):
            return
        data = dict(attrs)
        if data.get("href") and len(self.links) < MAX_LINKS:
            self.links.append(data["href"])

def live_reference(url):
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or not p.hostname or not public_hostname(p.hostname)
                or p.username or p.password or p.port not in (None, 443)
                or p.fragment):
            return None
        host = p.hostname.lower()
        if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if p.path == "/watch" and parse_qs(p.query).get("v"):
                return "youtube-video-page"
            if p.path.startswith(("/live/", "/channel/", "/@")):
                return "youtube-live-or-channel-page"
        if host == "youtu.be" and p.path.strip("/"):
            return "youtube-video-page"
        if any(segment in p.path.lower() for segment in ("/canli", "/canli-yayin", "/live", "/watch")):
            return "official-or-third-party-live-page"
        return None
    except ValueError:
        return None

def extract_live_references(page_url, html):
    try:
        origin = urlsplit(page_url)
        valid = (origin.scheme == "https" and bool(origin.hostname)
                 and public_hostname(origin.hostname) and not origin.username
                 and not origin.password and origin.port in (None, 443))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Public HTTPS page required")
    parser = LiveLinkParser()
    parser.feed(html[:2_000_000])
    result, seen = [], set()
    for href in parser.links:
        url = urljoin(page_url, href)
        kind = live_reference(url)
        if kind and url not in seen:
            result.append({"url": url, "kind": kind, "playback_verified": False,
                           "source_page": page_url})
            seen.add(url)
    return result

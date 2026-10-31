#!/usr/bin/env python3
"""Read-only public web-page source discovery; returns candidate M3U URLs, never streams.
Only public HTTPS links; no authentication, scraping bypass, or playlist mutation.
"""
import html
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import ipaddress

MAX_LINKS = 2000
EXTENSIONS = (".m3u", ".m3u8")

class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() not in ("a", "link"):
            return
        data = dict(attrs)
        url = data.get("href")
        if url and len(self.links) < MAX_LINKS:
            self.links.append(url)

def public_hostname(host):
    if host.lower() in ("localhost",) or host.lower().endswith((".local", ".internal", ".localhost")):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True

def candidate_url(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and public_hostname(parsed.hostname)
                and not parsed.username and not parsed.password
                and parsed.port in (None, 443)
                and parsed.path.lower().endswith(EXTENSIONS)
                and not parsed.fragment)
    except ValueError:
        return False

def discover_playlist_links(page_url, document):
    try:
        parsed = urlsplit(page_url)
        valid = (parsed.scheme == "https" and bool(parsed.hostname)
                 and public_hostname(parsed.hostname) and not parsed.username
                 and not parsed.password and parsed.port in (None, 443)
                 and not parsed.fragment)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("HTTPS public page required")
    parser = LinkParser()
    parser.feed(document[:2_000_000])
    seen, found = set(), []
    for href in parser.links:
        url = html.unescape(urljoin(page_url, href))
        if candidate_url(url) and url not in seen:
            seen.add(url)
            found.append(url)
    return found

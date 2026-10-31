#!/usr/bin/env python3
"""Classify public discovery references without confusing webpages with streams."""
from urllib.parse import urlsplit, parse_qs

def classify_reference(url):
    try:
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password:
            return None
        host = p.hostname.lower()
        if host in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            if p.path == "/watch" and parse_qs(p.query).get("v"):
                return {"kind": "youtube-video", "url": url, "playable_stream": False}
            if p.path.startswith(("/live/", "/channel/", "/@")):
                return {"kind": "youtube-page", "url": url, "playable_stream": False}
        if host == "youtu.be" and p.path.strip("/"):
            return {"kind": "youtube-video", "url": url, "playable_stream": False}
        if p.path.lower().endswith((".m3u", ".m3u8")) and not p.fragment:
            return {"kind": "playlist-source", "url": url, "playable_stream": False}
        return {"kind": "webpage", "url": url, "playable_stream": False}
    except ValueError:
        return None

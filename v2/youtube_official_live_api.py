#!/usr/bin/env python3
"""Optional read-only official YouTube live metadata, never a direct IPTV stream.

One videos.list request checks up to 50 discovered IDs. No account cookies,
playlist modifications, stream downloads or unsupported playback assertions.
"""
import json
import os
import re
from urllib.parse import urlencode, urlsplit
import urllib.error
import urllib.request

API_HOST = "www.googleapis.com"
BASE = "https://" + API_HOST + "/youtube/v3/videos"
MAX_BATCH = 50
ID_RE = re.compile(r"[A-Za-z0-9_-]{11}\Z")


def _official_request(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.path != "/youtube/v3/videos":
        raise ValueError("Untrusted official YouTube API endpoint")
    class SameHostRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            target = urlsplit(newurl)
            if target.scheme != "https" or target.hostname != API_HOST or target.path != "/youtube/v3/videos":
                raise ValueError("Unsafe YouTube API redirect")
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SameHostRedirect())
    request = urllib.request.Request(url, headers={
        "User-Agent": "MADSC55-TV-V2-PublicLiveMetadata/1.0",
        "Accept": "application/json"})
    with opener.open(request, timeout=18) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("Oversized public live metadata")
    return json.loads(data)


def classify(row):
    """Require explicit active-state evidence; do not infer from video titles."""
    if not isinstance(row, dict):
        return None
    snippet = row.get("snippet")
    if not isinstance(snippet, dict):
        return None
    broadcast = snippet.get("liveBroadcastContent")
    detail = row.get("liveStreamingDetails")
    detail = detail if isinstance(detail, dict) else {}
    if broadcast == "live":
        if detail.get("actualStartTime") and not detail.get("actualEndTime"):
            return "LIVE_METADATA_VERIFIED", "OFFICIAL_API_ACTIVE_LIVE"
        return None
    if broadcast in ("none", "upcoming"):
        return "NOT_CURRENTLY_LIVE", "OFFICIAL_API_NOT_LIVE"
    return None


def verify_ids(video_ids, key=None, request=None):
    """Map validated video IDs to status/reason; return an anonymous API state.

    A missing key is *not* proof of an offline stream. API errors are never
    logged verbatim since the request URL contains a private API key.
    """
    if key is None:
        key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return {}, "API_KEY_NOT_CONFIGURED"
    if not isinstance(key, str) or len(key) > 256 or any(x.isspace() for x in key):
        return {}, "API_KEY_INVALID"
    unique = list(dict.fromkeys(video_ids))
    if len(unique) > 5000 or any(not isinstance(x,str) or not ID_RE.fullmatch(x) for x in unique):
        return {}, "INVALID_VIDEO_IDS"
    request = request or _official_request
    checked = {}
    for start in range(0,len(unique),MAX_BATCH):
        batch = unique[start:start+MAX_BATCH]
        url = BASE + "?" + urlencode({"part":"snippet,liveStreamingDetails",
                                     "id":",".join(batch),"key":key})
        try:
            data = request(url)
            if not isinstance(data,dict) or not isinstance(data.get("items"),list):
                return checked,"API_INVALID_RESPONSE"
            for item in data["items"]:
                if not isinstance(item,dict) or item.get("id") not in batch:
                    continue
                status = classify(item)
                if status is not None:
                    checked[item["id"]] = status
        except urllib.error.HTTPError as exc:
            return checked, "API_HTTP_" + str(exc.code)
        except (OSError, ValueError, TimeoutError, TypeError):
            return checked,"API_REQUEST_FAILED"
    return checked,"API_QUERIES_FINISHED"

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
SEARCH_BASE = "https://" + API_HOST + "/youtube/v3/search"
MAX_SEARCH_QUERIES = 4
MAX_SEARCH_RESULTS = 25
MAX_BATCH = 50
ID_RE = re.compile(r"[A-Za-z0-9_-]{11}\Z")


def _official_request(url, endpoint="/videos"):
    parsed = urlsplit(url)
    if (endpoint not in ("/videos", "/search") or parsed.scheme != "https"
            or parsed.hostname != API_HOST or parsed.path != "/youtube/v3" + endpoint):
        raise ValueError("Untrusted official YouTube API endpoint")
    class SameHostRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            target = urlsplit(newurl)
            if (target.scheme != "https" or target.hostname != API_HOST
                    or target.path != "/youtube/v3" + endpoint):
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


def search_live(queries, key=None, search_request=None, video_request=None):
    """Search official active live videos, then cross-check videos.list.

    Metadata-only discovery. Search result snippets alone are not live proof;
    only videos.list liveBroadcastContent plus actualStartTime prove status.
    Search requests are capped to limit quota use (100 units per search).
    All output has public video IDs, not URL credentials.
    """
    if key is None:
        key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return [], "API_KEY_NOT_CONFIGURED"
    if not isinstance(key, str) or len(key) > 256 or any(c.isspace() for c in key):
        return [], "API_KEY_INVALID"
    if (not isinstance(queries, (list, tuple)) or
            any(not isinstance(q, str) or not 1 <= len(q) <= 140 or
                any(ord(c) in (10, 13) for c in q) for q in queries)):
        return [], "INVALID_SEARCH_QUERIES"
    search_request = search_request or (lambda url: _official_request(url, "/search"))
    results = {}
    for query in queries[:MAX_SEARCH_QUERIES]:
        url = SEARCH_BASE + "?" + urlencode({
            "part": "snippet", "type": "video", "eventType": "live",
            "q": query, "maxResults": str(MAX_SEARCH_RESULTS), "key": key})
        try:
            payload = search_request(url)
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                return [], "API_INVALID_SEARCH_RESPONSE"
            for row in payload["items"][:MAX_SEARCH_RESULTS]:
                if not isinstance(row, dict) or not isinstance(row.get("id"), dict):
                    continue
                video_id = row["id"].get("videoId")
                snippet = row.get("snippet")
                if (not isinstance(video_id, str) or not ID_RE.fullmatch(video_id)
                        or not isinstance(snippet, dict)):
                    continue
                results.setdefault(video_id, {
                    "video_id": video_id,
                    "url": "https://www.youtube.com/watch?v=" + video_id,
                    "title": str(snippet.get("title") or "")[:200],
                    "channel": str(snippet.get("channelTitle") or "")[:120],
                })
        except urllib.error.HTTPError as exc:
            return [], "API_SEARCH_HTTP_" + str(exc.code)
        except (OSError, ValueError, TypeError, TimeoutError):
            return [], "API_SEARCH_REQUEST_FAILED"
    if not results:
        return [], "API_SEARCH_NO_PUBLIC_VIDEOS"
    checked, state = verify_ids(list(results), key=key, request=video_request)
    if state != "API_QUERIES_FINISHED":
        return [], "API_SEARCH_VIDEO_CROSSCHECK_" + state
    verified = []
    for video_id, row in results.items():
        status = checked.get(video_id)
        if status is not None and status[0] == "LIVE_METADATA_VERIFIED":
            verified.append({
                **row, "status": status[0],
                "metadata_reason": status[1]})
    return verified, "API_LIVE_SEARCH_VERIFIED" if verified else "API_SEARCH_NO_VERIFIED_LIVE"

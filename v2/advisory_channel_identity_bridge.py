#!/usr/bin/env python3
"""Read-only exact-identity connection of official sites and YouTube to M3U scan.

No page URL, YouTube video or website becomes an IPTV stream candidate.
Official catalog identifiers are matched exactly; YouTube live metadata is
matched only on the uploader channel name, never the video headline.
"""
import hashlib
import json
import re
from pathlib import Path

MAX_ROWS = 50000
MAX_BYTES = 15_000_000


def norm(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def _read(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_BYTES:
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, UnicodeError):
        return None
    return raw if isinstance(raw, dict) else None


def link_advisory_identities(candidates, official_report, youtube_report):
    """Report only exact identity links; keep stream candidate objects intact."""
    if not isinstance(candidates, list) or len(candidates) > MAX_ROWS:
        raise ValueError("Invalid candidate list")
    official = _read(official_report)
    youtube = _read(youtube_report)
    names, ids = {}, {}
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("Invalid M3U candidate row")
        digest = item.get("url_sha256")
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError("Invalid M3U candidate URL hash")
        name = norm(item.get("name"))
        epg = norm(item.get("tvg_id"))
        if name:
            names.setdefault(name, set()).add(digest)
        if epg:
            ids.setdefault(epg, set()).add(digest)

    by_sha = {}
    def attach(digest, kind, row):
        record = by_sha.setdefault(digest, {"candidate_url_sha256": digest,
                                             "official_site_catalog_ids": set(),
                                             "youtube_live_video_sha256": set()})
        record[kind].add(row)

    official_checked = official_matches = 0
    official_valid = bool(official and official.get("policy") ==
                          "READ_ONLY_NO_PLAYLIST_CHANGES_NO_DRM_BYPASS"
                          and isinstance(official.get("channels"), list)
                          and official.get("count") == len(official["channels"])
                          and len(official["channels"]) <= MAX_ROWS)
    if official_valid:
        for row in official["channels"]:
            if not isinstance(row, dict):
                continue
            official_checked += 1
            epg = norm(row.get("channel_id"))
            channel_name = norm(row.get("name"))
            # EPG ID matches must be unique to a broadcaster entry; an
            # unrelated name with the same ID is not accepted without review.
            if not epg or not channel_name:
                continue
            for digest in ids.get(epg, ()):
                original = next((x for x in candidates if x["url_sha256"] == digest), None)
                if original and norm(original.get("name")) == channel_name:
                    attach(digest, "official_site_catalog_ids", epg)
                    official_matches += 1

    youtube_checked = youtube_matches = 0
    youtube_valid = bool(youtube and youtube.get("policy") ==
                         "ADVISORY_ONLY_NO_PLAYLIST_WRITES_NO_AUTOMATIC_IBO_IMPORT"
                         and isinstance(youtube.get("results"), list)
                         and len(youtube["results"]) <= MAX_ROWS)
    if youtube_valid:
        for row in youtube["results"]:
            if not isinstance(row, dict) or row.get("status") != "LIVE_METADATA_VERIFIED":
                continue
            youtube_checked += 1
            uploader = norm(row.get("channel"))
            video_id = row.get("video_id")
            if (not uploader or not isinstance(video_id, str)
                    or not re.fullmatch("[A-Za-z0-9_-]{11}", video_id)):
                continue
            video_hash = hashlib.sha256(video_id.encode("ascii")).hexdigest()
            for digest in names.get(uploader, ()):
                attach(digest, "youtube_live_video_sha256", video_hash)
                youtube_matches += 1
    links = []
    for digest, item in sorted(by_sha.items()):
        links.append({"candidate_url_sha256": digest,
                      "official_site_catalog_ids": sorted(item["official_site_catalog_ids"]),
                      "youtube_live_video_sha256": sorted(item["youtube_live_video_sha256"]),
                      "playback_verified": False,
                      "identity_match_only": True})
    return {
        "schema": 1, "status": "METADATA_LINKS_ONLY_NOT_PLAYBACK_VERIFIED",
        "official_catalog_status": "VALID" if official_valid else "MISSING_OR_INVALID",
        "youtube_catalog_status": "VALID" if youtube_valid else "MISSING_OR_INVALID",
        "official_entries_checked": official_checked,
        "official_exact_identity_connections": official_matches,
        "youtube_live_metadata_checked": youtube_checked,
        "youtube_exact_uploader_connections": youtube_matches,
        "linked_m3u_candidates": len(links),
        "links": links, "av_verified": False, "ibo_device_verified": False,
        "youtube_pages_are_not_m3u_streams": True,
        "official_websites_are_not_m3u_streams": True,
        "main_playlist_modified": False,
    }

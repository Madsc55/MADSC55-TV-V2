#!/usr/bin/env python3
"""Resolve verified official/YouTube live pages to encrypted direct HLS candidates.

This is candidate preparation only. It never proves AV playback or writes playlists.
"""
import argparse
import json
import os
import pathlib
import subprocess
import urllib.parse

from discovery_34 import identity
from secure_archive import atomic_write, encrypt

MAX_RESOLVE = 120
TIMEOUT_SECONDS = 65


def resolve_candidate(item, runner=subprocess.run):
    if not isinstance(item, dict):
        return None, "INVALID_CANDIDATE"
    source = item.get("source")
    if source not in ("official", "youtube"):
        return None, "UNSUPPORTED_SOURCE"
    page_url = item.get("url")
    try:
        identity(source, page_url)
    except (ValueError, TypeError):
        return None, "INVALID_PAGE_URL"
    if item.get("verified_av") is not False:
        return None, "INVALID_EVIDENCE_STATE"
    if source == "youtube" and item.get("status") != "LIVE_METADATA_VERIFIED":
        return None, "YOUTUBE_NOT_LIVE_VERIFIED"
    if source == "official" and item.get("status") != "DIRECTORY_REFERENCE_ONLY_NOT_STREAM_VERIFIED":
        return None, "OFFICIAL_DIRECTORY_STATE_INVALID"
    command = [
        "yt-dlp", "--no-warnings", "--no-playlist", "--skip-download",
        "--format", "best[protocol^=m3u8]/best",
        "--dump-single-json", "--socket-timeout", "10", page_url,
    ]
    try:
        result = runner(command, capture_output=True, text=True,
                        timeout=TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None, "YTDLP_TIMEOUT_OR_MISSING"
    if getattr(result, "returncode", 1) != 0:
        return None, "YTDLP_RESOLUTION_FAILED"
    try:
        metadata = json.loads(result.stdout)
    except (ValueError, TypeError):
        return None, "INVALID_YTDLP_JSON"
    if not isinstance(metadata, dict):
        return None, "INVALID_YTDLP_METADATA"
    live = metadata.get("is_live") is True or metadata.get("live_status") == "is_live"
    if not live:
        return None, "LIVE_STATUS_NOT_VERIFIED"
    direct_url = metadata.get("url")
    try:
        identity("m3u", direct_url)
    except (ValueError, TypeError):
        return None, "INVALID_DIRECT_URL"
    parsed = urllib.parse.urlsplit(direct_url)
    protocol = str(metadata.get("protocol") or "").lower()
    is_hls = protocol.startswith("m3u8") or parsed.path.lower().endswith((".m3u8", ".mpd"))
    if parsed.scheme != "https" or not is_hls or direct_url == page_url:
        return None, "NOT_DIRECT_HTTPS_HLS"
    source_id = item.get("source_id")
    if not isinstance(source_id, str) or not source_id:
        return None, "MISSING_SOURCE_ID"
    return {
        "source": source,
        "source_id": source_id,
        "source_page": page_url,
        "url": direct_url,
        "name": str(item.get("name") or source_id)[:200],
        "group": str(item.get("group") or "")[:120],
        "tvg_id": str(item.get("tvg_id") or "")[:200],
        "logo": str(item.get("logo") or "")[:1000],
        "live_metadata_verified": True,
        "verified_av": False,
        "status": "RESOLVED_DIRECT_HLS_NOT_AV_VERIFIED",
    }, None


def resolve_report(report, runner=subprocess.run, limit=MAX_RESOLVE):
    if not isinstance(report, dict) or not isinstance(report.get("candidates"), list):
        raise ValueError("Integrated discovery report requires a candidates list")
    candidates, errors = [], []
    youtube = [item for item in report["candidates"]
               if isinstance(item, dict) and item.get("source") == "youtube"
               and item.get("status") == "LIVE_METADATA_VERIFIED"]
    official = [item for item in report["candidates"]
                if isinstance(item, dict) and item.get("source") == "official"]
    youtube_limit = max(0, (limit + 1) // 2)
    official_limit = max(0, limit // 2)
    eligible_total = len(youtube) + len(official)
    eligible = youtube[:youtube_limit] + official[:official_limit]
    attempted = 0
    for item in eligible:
        attempted += 1
        resolved, error = resolve_candidate(item, runner=runner)
        if resolved is not None:
            candidates.append(resolved)
        elif error:
            errors.append({"source_id": item.get("source_id", ""), "reason": error})
    return {
        "policy": "CANDIDATES_ONLY_ENCRYPTED_DIRECT_URLS_NO_PLAYLIST_WRITES",
        "attempted": attempted,
        "eligible": eligible_total,
        "skipped_by_limit": max(0, len(youtube) - youtube_limit) + max(0, len(official) - official_limit),
        "resolved": len(candidates),
        "verified_av": 0,
        "candidates": candidates,
        "errors": errors,
    }


def write_encrypted_report(report, destination, passphrase):
    raw = json.dumps(report, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + bytes([10])
    blob = encrypt(raw, passphrase)
    atomic_write(destination, blob)
    return {"encrypted": True, "bytes": len(blob), "resolved": report["resolved"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=pathlib.Path,
                        default=pathlib.Path("v2/reports/discovery-34-integrated.json"))
    parser.add_argument("--output", type=pathlib.Path,
                        default=pathlib.Path("v2/reports/resolved-direct-streams.jsonl.enc"))
    parser.add_argument("--limit", type=int, default=MAX_RESOLVE)
    args = parser.parse_args()
    if not args.input.is_file():
        parser.error("Integrated discovery report missing")
    passphrase = os.environ.get("V2_ARCHIVE_PASSPHRASE", "")
    if len(passphrase) < 16:
        parser.error("V2_ARCHIVE_PASSPHRASE must contain at least 16 characters")
    report = resolve_report(json.loads(args.input.read_text(encoding="utf-8")), limit=args.limit)
    result = write_encrypted_report(report, args.output, passphrase)
    print("Direct HLS candidates resolved:", result["resolved"],
          "attempted:", report["attempted"], "errors:", len(report["errors"]),
          "encrypted:", result["encrypted"])


if __name__ == "__main__":
    main()

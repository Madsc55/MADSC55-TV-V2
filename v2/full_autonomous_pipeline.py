#!/usr/bin/env python3
"""Fail-closed one-click discovery: only proven decoded AV is promoted."""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
import urllib.error
import time
from pathlib import Path
from urllib.parse import urlsplit

from v2.ibo_single_playlist_transfer import parse
from v2.turkish_media_sample_capture import capture

PLAYLIST = Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
EVIDENCE = Path("autonomous-evidence.json")
HISTORICAL_MANIFEST_SHA256 = "b001bf48f07437e9ae67ed9f73b12ea9cfcab653523973435cf3b1cee3c31fcc"


def digest(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


_LAST_REQUEST = [0.0]


def fetch_feed(url):
    # Deliberately narrow: arbitrary web pages and YouTube metadata are NOT streams.
    # A separately reviewed source adapter is required before expanding this allowlist.
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "raw.githubusercontent.com" or parsed.port is not None:
        raise ValueError("Feed must be a reviewed raw.githubusercontent.com HTTPS M3U URL")
    if not parsed.path.lower().endswith((".m3u", ".m3u8")):
        raise ValueError("Not an M3U feed")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(url, headers={"User-Agent": "MADSC55-AV-Acceptance/1"})
    wait = 3.0 - (time.monotonic() - _LAST_REQUEST[0])
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST[0] = time.monotonic()
    try:
        response = opener.open(request, timeout=15)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise ValueError("RATE_LIMITED_429: stop; do not retry automatically") from exc
        raise
    with response:
        if response.geturl() != url or response.status != 200:
            raise ValueError("Redirect or unexpected response")
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("Feed exceeds bounded size")
    return data.decode("utf-8")


def candidates(feed, limit):
    lines = feed.splitlines()
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("Invalid feed header")
    pending = None
    found = []
    for line in lines[1:]:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            pending = line
        elif pending is not None and line and not line.startswith("#"):
            if re.match(r"^https?://", line) and len(line) <= 4096:
                label = pending.rsplit(",", 1)[-1].strip()
                if label and len(label) <= 100 and not any(c in label for c in "\\r\\n"):
                    found.append((label, line))
            pending = None
            if len(found) >= limit:
                break
    return found


def decoded_both(path):
    # The input is a local bounded sample produced with FFmpeg's file-only protocol.
    cmd = ["ffprobe", "-v", "error", "-protocol_whitelist", "file",
           "-show_entries", "stream=codec_type", "-of", "json", str(path)]
    result = subprocess.run(cmd, capture_output=True, timeout=12, check=False)
    if result.returncode:
        return False
    kinds = {s.get("codec_type") for s in json.loads(result.stdout).get("streams", [])}
    return {"audio", "video"}.issubset(kinds)



def discover_youtube_and_official_streams(source_urls, limit=30):
    """Accept verified official HTTPS M3U feeds; reject unverified video-page URLs."""
    pool = []
    for source in source_urls:
        if len(pool) >= limit:
            break
        parsed = urlsplit(source)
        if parsed.hostname in ("youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"):
            continue
        try:
            pool.extend(candidates(fetch_feed(source), limit - len(pool)))
        except (ValueError, OSError, urllib.error.URLError):
            continue
    return pool


def verify_685_locked_channels(manifest_path, playlist_blocks):
    """Probe immutable 685 identities using bounded pinned downloads and local-only FFmpeg."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest() != HISTORICAL_MANIFEST_SHA256:
        raise ValueError("Historical locked manifest checksum mismatch")
    queue = manifest.get("retry_queue")
    if not isinstance(queue, list) or len(queue) != 685:
        raise ValueError("Expected 685 locked manifest identities")
    by_identity = {digest(block.encode("utf-8")): block for block in playlist_blocks}
    if len(by_identity) != len(playlist_blocks):
        raise ValueError("Duplicate immutable playlist identities")
    verified_unlocked, quarantine, seen = [], [], set()
    with tempfile.TemporaryDirectory() as directory:
        for index, record in enumerate(queue):
            channel_hash = record.get("channel_sha256")
            block = by_identity.get(channel_hash)
            if channel_hash in seen or block is None or record.get("status") != "uncertain":
                raise ValueError("Locked manifest identity mismatch")
            seen.add(channel_hash)
            url = block.splitlines()[-1].strip()
            url_hash = digest(url)
            if record.get("url_sha256") != url_hash:
                raise ValueError("Locked URL identity mismatch")
            output = Path(directory) / f"locked-{index}.mkv"
            try:
                sample = capture(url, output, seconds=4, timeout=17,
                                 allow_hls_ts=urlsplit(url).path.lower().endswith(".m3u8"))
                passed = (sample.get("status") == "SAMPLE_CAPTURED_UNVERIFIED"
                          and decoded_both(output))
            except (ValueError, OSError, TimeoutError, subprocess.SubprocessError,
                    json.JSONDecodeError):
                passed = False
            evidence = {"channel_sha256": channel_hash, "url_sha256": url_hash,
                        "decoded_av_verified": passed, "security_lock_retained": True}
            if passed:
                verified_unlocked.append(evidence)
            else:
                quarantine.append({**evidence, "status": "RECHECK_REQUIRED"})
    return verified_unlocked, quarantine


def classify_and_merge_to_main_playlist(verified_candidates, existing_blocks):
    """Return M3U blocks only for independently AV- and language-verified new URLs."""
    known = {block.splitlines()[-1].strip() for block in existing_blocks}
    additions = []
    for item in verified_candidates:
        url, label = item.get("url"), item.get("label")
        if not isinstance(url, str) or not isinstance(label, str):
            continue
        if not item.get("decoded_av_verified") or not item.get("language_verified"):
            continue
        if item.get("language_evidence") != "independent_audio_review":
            continue
        if item.get("language") == "tr":
            group = "🇹🇷 ULUSAL-HEPSİ"
        elif item.get("language") == "foreign":
            group = "YABANCI ARŞİVİ"
        else:
            continue
        parsed = urlsplit(url)
        if (parsed.scheme not in ("https", "http") or not parsed.hostname
                or url in known or len(url) > 4096
                or not re.fullmatch(r'[^\\r\\n"<>]{1,100}', label)):
            continue
        additions.append(f'#EXTINF:-1 group-title="{group}",{label}\\n{url}\\n')
        known.add(url)
    return additions


def metadata_language_hint(label, group=""):
    """Metadata hints are never independently verified spoken-language evidence."""
    combined = (str(label) + " " + str(group)).casefold()
    if re.search(r"türk|turk|trt|\\btr\\b|azer|azər", combined):
        return "TURKISH_METADATA_HINT_REVIEW_REQUIRED"
    return "LANGUAGE_UNVERIFIED_REVIEW_REQUIRED"


def run_readonly_source_adapters(limit):
    """Call existing adapters; keep their outputs advisory and bounded."""
    import urllib.request
    results = {}
    for provider in ("gitlab", "codeberg"):
        try:
            from v2.federated_m3u_source_discovery import discover_provider
            data = discover_provider(provider, queries=("iptv",), configured_urls=set())
            results[provider] = data
        except Exception as exc:
            results[provider] = {"status": "error", "error_type": type(exc).__name__}
    try:
        from v2 import github_source_discovery as gh
        with tempfile.TemporaryDirectory() as tmp:
            previous_out, previous_queries = gh.OUT, gh.QUERIES
            try:
                gh.OUT = Path(tmp) / "github-source-discovery.json"
                gh.QUERIES = gh.QUERIES[:1]
                try:
                    gh.main()
                except SystemExit:
                    pass  # Preserve partial error reports rather than losing evidence.
                results["github"] = json.loads(gh.OUT.read_text()) if gh.OUT.exists() else {"status": "error", "reason": "no_report"}
            finally:
                gh.OUT, gh.QUERIES = previous_out, previous_queries
    except ImportError as exc:
        results["github"] = {"status": "error", "error_type": type(exc).__name__}
    try:
        from v2.youtube_discovery import search, QUERIES
        rows, error = search(QUERIES[0])
        results["youtube"] = {"status": "metadata_only", "candidates": rows[:limit],
                              "error": error, "stream_urls_verified": 0}
    except Exception as exc:
        results["youtube"] = {"status": "error", "error_type": type(exc).__name__}
    try:
        from v2.official_sites_discovery import select_official_sites, URL
        req = urllib.request.Request(URL, headers={"User-Agent": "MADSC55-Readonly/1"})
        with urllib.request.urlopen(req, timeout=35) as response:
            raw = response.read(30_000_001)
        if len(raw) > 30_000_000:
            raise ValueError("Official directory exceeds size limit")
        sites = select_official_sites(json.loads(raw))
        results["official_sites"] = {"status": "directory_only", "count": len(sites),
                                    "channels": sites[:limit], "stream_urls_verified": 0}
    except Exception as exc:
        results["official_sites"] = {"status": "error", "error_type": type(exc).__name__}
    return results

def main():
    raw = PLAYLIST.read_bytes()
    prefix, blocks = parse(raw)
    original = [b for b in blocks]
    known = {b.splitlines()[-1].strip() for b in blocks}
    source = os.environ.get("SOURCE_FEED", "").strip()
    limit = min(100, max(1, int(os.environ.get("MAX_CANDIDATES", "30"))))
    report = {"schema": 1, "original_playlist_sha256": hashlib.sha256(raw).hexdigest(),
              "original_entries": len(blocks), "candidates_checked": 0,
              "verified_additions": 0, "security_hold_685_preserved": True,
              "existing_categories_preserved": True, "language_verified": False,
              "youtube_and_web_discovery_not_yet_supported": True,
              "locked_685_live_retry": "SECURITY_HOLD_NO_OS_EGRESS_SANDBOX",
              "locked_685_quarantined": 685,
              "language_classification": "UNVERIFIED_NO_AUTOMATIC_REASSIGNMENT",
              "source_rate_limit_seconds": 3}
    try:
        report["source_adapters"] = run_readonly_source_adapters(limit)
        report["metadata_language_hints"] = {"policy": "REVIEW_ONLY_NOT_SPOKEN_LANGUAGE_VERIFIED", "results": [{"name": b.splitlines()[0].rsplit(",", 1)[-1], "hint": metadata_language_hint(b.splitlines()[0])} for b in original[:limit]]}
        proposed = discover_youtube_and_official_streams([source], limit) if source else []
        with tempfile.TemporaryDirectory() as directory:
            for index, (label, url) in enumerate(proposed):
                if url in known:
                    continue
                report["candidates_checked"] += 1
                output = Path(directory) / f"{index}.mkv"
                try:
                    # HTTPS/public-IP pinned; FFmpeg decodes local bytes only.
                    result = capture(url, output, seconds=4, timeout=17,
                                     allow_hls_ts=urlsplit(url).path.lower().endswith(".m3u8"))
                    if result.get("status") != "SAMPLE_CAPTURED_UNVERIFIED" or not decoded_both(output):
                        continue
                    safe_label = re.sub(r"[\\r\\n\"<>]", "", label)
                    if not safe_label:
                        continue
                    # Never assign a guessed country/language category.
                    new_block = f'#EXTINF:-1 group-title="🗂️ YEDEKLER", {safe_label}\n{url}\n'
                    blocks.append(new_block)
                    known.add(url)
                    report["verified_additions"] += 1
                except (ValueError, OSError, TimeoutError, subprocess.SubprocessError, json.JSONDecodeError):
                    continue
        if report["verified_additions"]:
            # Existing entries remain byte-for-byte and in exactly the same order.
            assert blocks[:len(original)] == original
            with PLAYLIST.open("ab") as handle:
                for block in blocks[len(original):]:
                    handle.write(block.encode("utf-8"))
    finally:
        EVIDENCE.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

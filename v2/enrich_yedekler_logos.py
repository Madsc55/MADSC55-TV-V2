#!/usr/bin/env python3
"""Attach evidence-backed logos to YEDEKLER only. Never invent or reuse unrelated logos."""
import json
import pathlib
import re
from collections import defaultdict
from urllib.parse import urlsplit
from real_ibo_scan import SOURCES, LIVE, fetch, parse_m3u

REPORT = pathlib.Path(__file__).resolve().parent / "reports" / "yedekler-logo-report.json"

def norm(name):
    name = re.sub(r"\s*\([^)]*(?:[0-9]{3,4}p|HD|FHD|UHD|QHD)[^)]*\)", "", name, flags=re.I)
    name = re.sub(r"\s*\[(?:not 24/7|geo-blocked)\]", "", name, flags=re.I)
    return re.sub(r"[^\w]+", "", name.casefold())

def valid_logo(url):
    if not isinstance(url, str) or len(url) > 2048 or any(c in url for c in '"\r\n<>'):
        return False
    parsed = urlsplit(url)
    return parsed.scheme == "https" and bool(parsed.netloc)

def main():
    original = LIVE.read_text(encoding="utf-8-sig")
    rows = original.splitlines(keepends=True)
    by_url = defaultdict(set)
    by_id = defaultdict(set)
    by_name = defaultdict(set)
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    stats = {"sources_checked": 0, "sources_failed": 0, "by_url": 0, "by_id": 0, "by_name": 0, "ambiguous": 0, "without_match": 0}
    for source in sources:
        try:
            data = fetch(source["url"], timeout=12)
            for item in parse_m3u(data):
                logo = item.get("logo", "")
                if not valid_logo(logo):
                    continue
                by_url[item["url"]].add(logo)
                channel_id = (item.get("tvg_id") or "").casefold().strip()
                if channel_id:
                    by_id[channel_id].add(logo)
                if norm(item["name"]):
                    by_name[norm(item["name"])].add(logo)
            stats["sources_checked"] += 1
        except (OSError, ValueError, UnicodeError) as exc:
            stats["sources_failed"] += 1
            print(f"Source skipped {source['id']}: {type(exc).__name__}")

    try:
        def api(name):
            return json.loads(fetch(f"https://iptv-org.github.io/api/{name}.json", timeout=30))
        logos = defaultdict(set)
        for logo in api("logos"):
            if valid_logo(logo.get("url")) and logo.get("channel"):
                logos[logo["channel"]].add(logo["url"])
        for stream in api("streams"):
            channel, url = stream.get("channel"), stream.get("url")
            if channel and url and channel in logos:
                by_url[url].update(logos[channel])
        for channel in api("channels"):
            channel_id = channel.get("id", "")
            if channel_id in logos:
                by_id[channel_id.casefold()].update(logos[channel_id])
                for name in [channel.get("name", "")] + (channel.get("alt_names") or []):
                    if norm(name):
                        by_name[norm(name)].update(logos[channel_id])
    except (OSError, ValueError, KeyError, UnicodeError) as exc:
        print(f"IPTV-org API skipped: {type(exc).__name__}")

    added = 0
    missing = []
    for i, row in enumerate(rows):
        if not row.startswith("#EXTINF:") or 'group-title="🗂️ YEDEKLER (' not in row:
            continue
        if re.search(r'\btvg-logo="https?://', row):
            continue
        name = row.rstrip("\r\n").rsplit(",", 1)[-1].strip()
        url = rows[i + 1].strip() if i + 1 < len(rows) else ""
        match_id = re.search(r'\btvg-id="([^"]+)"', row)
        channel_id = match_id.group(1).casefold().strip() if match_id else ""
        candidates = [
            ("by_url", by_url.get(url, set())),
            ("by_id", by_id.get(channel_id, set()) if channel_id else set()),
            ("by_name", by_name.get(norm(name), set())),
        ]
        found = False
        for method, options in candidates:
            if len(options) == 1:
                logo = next(iter(options))
                # Keep all other attributes, group names, stream URLs and order unchanged.
                rows[i] = row.replace("#EXTINF:-1", f'#EXTINF:-1 tvg-logo="{logo}"', 1)
                stats[method] += 1
                added += 1
                found = True
                break
            if len(options) > 1:
                stats["ambiguous"] += 1
                found = True
                break
        if not found:
            stats["without_match"] += 1
            missing.append(name)
    if added:
        LIVE.write_text("".join(rows), encoding="utf-8", newline="")
    stats["logos_added"] = added
    stats["still_missing_examples"] = missing[:100]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))

if __name__ == "__main__":
    main()

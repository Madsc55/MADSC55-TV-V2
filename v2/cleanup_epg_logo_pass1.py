#!/usr/bin/env python3
"""Offline, fail-closed playlist cleanup. Never downloads or invents metadata."""
import argparse
import collections
import json
import re
from pathlib import Path

PLAYLIST = Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
ATTR = re.compile(r'(?<!\\S)(tvg-id|tvg-logo)="([^"]*)"')
GROUP = re.compile(r'group-title="([^"]*)"')

def attr(line, name):
    match = re.search(r'(?<!\\S)' + re.escape(name) + r'="([^"]*)"', line)
    return match.group(1) if match else ""

def set_attr(line, name, value):
    if not value or attr(line, name):
        return line
    # Only metadata already present on the same exact URL is eligible.
    return line.replace(",", ' ' + name + '="' + value + '",', 1)

def parse(lines):
    blocks, prefix = [], []
    i = 0
    while i < len(lines):
        if lines[i].startswith("#EXTINF:"):
            start = i
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].startswith("#")):
                i += 1
            if i >= len(lines):
                raise ValueError("Unpaired EXTINF; refusing to change playlist")
            if lines[i].startswith("#EXTINF:"):
                raise ValueError("Unpaired EXTINF; refusing to change playlist")
            url = lines[i].strip()
            if not url or url.startswith("#"):
                raise ValueError("Invalid URL; refusing to change playlist")
            blocks.append([lines[start:i + 1], url])
            i += 1
        else:
            if blocks:
                blocks[-1][0].append(lines[i])
            else:
                prefix.append(lines[i])
            i += 1
    return prefix, blocks

def channel_name(header):
    return header.split(",", 1)[1].strip().casefold() if "," in header else ""

def record_key(header, url):
    return (url, channel_name(header))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", type=Path, default=PLAYLIST)
    ap.add_argument("--output", type=Path, default=Path("pass1-results") / PLAYLIST.name)
    ap.add_argument("--report", type=Path, default=Path("pass1-results/report.json"))
    args = ap.parse_args()
    original = args.playlist.read_text(encoding="utf-8-sig")
    prefix, blocks = parse(original.splitlines(keepends=True))
    if not blocks:
        raise ValueError("No channels parsed")
    # The only trusted pool is metadata already present in this same playlist
    # for the exact same stream URL. Conflicting values are never propagated.
    candidates = collections.defaultdict(lambda: {"tvg-id": set(), "tvg-logo": set()})
    for block, url in blocks:
        for field in ("tvg-id", "tvg-logo"):
            val = attr(block[0], field)
            if val:
                candidates[url][field].add(val)
    unique = []
    removed = []
    seen = set()
    names_by_url = collections.defaultdict(set)
    for block, url in blocks:
        names_by_url[url].add(channel_name(block[0]))
    stats = {"original_channels": len(blocks), "duplicates_removed": 0,
             "epg_added": 0, "logos_added": 0, "metadata_conflicts": 0}
    stats["same_url_different_names"] = sum(len(names) for names in names_by_url.values() if len(names) > 1)
    for block, url in blocks:
        key = record_key(block[0], url)
        if key in seen:
            stats["duplicates_removed"] += 1
            removed.append("".join(block))
            continue
        seen.add(key)
        head = block[0]
        for field, key in (("tvg-id", "epg_added"), ("tvg-logo", "logos_added")):
            values = candidates[url][field]
            if len(values) > 1:
                stats["metadata_conflicts"] += 1
            elif len(values) == 1 and not attr(head, field):
                value = next(iter(values))
                new_head = set_attr(head, field, value)
                if new_head != head:
                    stats[key] += 1
                    head = new_head
        block[0] = head
        unique.append(block)
    # Preserve original category ordering and every surviving record's position.
    # Consequently an already alphabetized ANA ARŞİV remains alphabetized.
    result = "".join(prefix) + "".join("".join(block) for block, _ in unique)
    stats["final_channels"] = len(unique)
    stats["categories"] = dict(collections.Counter(
        attr(block[0], "group-title") for block, _ in unique))
    stats["changed"] = result != original
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result, encoding="utf-8")
    args.report.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.report.parent / "removed-records.m3u8").write_text("#EXTM3U\\n" + "".join(removed), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Offline invariants for MADSC55 TV V2 playlist and source configuration."""
import json
import subprocess
import pathlib
import sys
from collections import Counter
from discover import ROOT, LIVE, SOURCES, entries

def main():
    # Original bytes stay identical; only appended YEDEKLER entries are allowed.
    current = LIVE.read_bytes()
    original_size = 207344
    assert len(current) >= original_size, "Original playlist was truncated"
    original = current[:original_size]
    original_hash = subprocess.run(
        ["git", "hash-object", "--stdin"], input=original,
        capture_output=True, check=True
    ).stdout.decode().strip()
    assert original_hash == "4b1c3cea4b5107a425abab60f62d41f9f81e05a7", "Original playlist bytes changed"
    suffix = current[original_size:]
    if suffix:
        rows = [line for line in suffix.decode("utf-8").splitlines() if line.strip()]
        assert len(rows) % 2 == 0, "Incomplete appended M3U record"
        existing = {line.strip() for line in original.decode("utf-8-sig").splitlines()
                    if line.strip().startswith(("http://", "https://"))}
        for i in range(0, len(rows), 2):
            header, url = rows[i:i + 2]
            assert header.startswith("#EXTINF:") and 'group-title="🗂️ YEDEKLER (2)"' in header, "Only YEDEKLER may be appended"
            assert url.startswith(("https://", "http://")) and url not in existing, "Invalid or duplicate stream URL"
            assert not any(term in header.casefold() for term in ("trt arabi", "trt world")), "Blocked foreign-language channel"
            existing.add(url)
    text = LIVE.read_text(encoding="utf-8-sig")
    channels = list(entries(text))
    assert text.startswith("#EXTM3U"), "Missing M3U header"
    assert len(channels) >= 840, "Playlist shrank below the verified post-deduplication baseline"
    backups = [x for x in channels if "YEDEKLER" in x["group"]]
    assert len(backups) >= 2, "YEDEKLER must preserve the two original channels"
    assert any(x["name"] == "TRT 1 1440P QHD" for x in backups), "Original TRT 1 backup missing"
    assert any(x["name"] == "DHA CANLI 720P HD" for x in backups), "Original DHA backup missing"
    assert not any(x["name"].startswith(("TRT Arabi", "TRT World")) for x in channels), "Unwanted foreign-language trials remain"
    for name in ("Aras TV (576p) [Not 24/7]", "Haber61 TV (720p) [Not 24/7]", "TV Den (576p) [Not 24/7]", "YOL TV"):
        assert any(x["name"] == name and x["group"].startswith("📍 YEREL (") for x in channels), f"{name} missing from YEREL"
        assert any(x["name"] == name and x["group"].startswith("🇹🇷 ULUSAL-HEPSİ (") for x in channels), f"{name} missing from HEPSİ"
    for x in channels:
        assert x["url"].startswith(("https://", "http://")), "Invalid stream scheme"
    category_counts = Counter(x["group"] for x in channels)
    for group, count in category_counts.items():
        import re
        match = re.search(r"\((\d+)\)$", group)
        assert match, f"Missing category counter: {group}"
        if group == "🗂️ YEDEKLER (2)":
            assert count >= 2, "Original backup channels missing"
        else:
            assert int(match.group(1)) == count, f"Category count mismatch: {group}, actual {count}"
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    assert len(sources) >= 3, "Discovery sources missing"
    note = ROOT / "DEVAM_NOTU.md"
    assert note.exists(), "Canonical continuation note missing"
    print("PASS:", len(channels), "channels;", len(backups), "backups;", len(category_counts), "categories;", len(sources), "discovery sources; one continuation note")
if __name__ == "__main__":
    main()

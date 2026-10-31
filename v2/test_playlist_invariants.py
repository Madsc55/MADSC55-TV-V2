#!/usr/bin/env python3
"""Offline invariants for MADSC55 TV V2 playlist and source configuration."""
import json
import hashlib
import pathlib
import sys
from collections import Counter
from discover import ROOT, LIVE, SOURCES, entries

def main():
    # Protect the exact original bytes and permit only append-only YEDEKLER records.
    current = LIVE.read_bytes()
    original = current[:211257]
    original_hash = hashlib.sha1(b"blob " + str(len(original)).encode("ascii") + b"\0" + original).hexdigest()
    assert original_hash == "4b1c3cea4b5107a425abab60f62d41f9f81e05a7", (
        f"Original playlist bytes changed: actual={original_hash}, size={len(current)}, "
        f"prefix_size={len(original)}, path={LIVE}. Verify the workflow branch and checkout."
    )
    assert current.startswith(original), "Protected IBO playlist content changed"
    extra = current[len(original):]
    if extra:
        rows = [row for row in extra.decode("utf-8").splitlines() if row.strip()]
        assert len(rows) % 2 == 0, "Incomplete appended channel"
        known = {row.strip() for row in original.decode("utf-8-sig").splitlines() if row.strip().startswith(("http://", "https://"))}
        for i in range(0, len(rows), 2):
            header, url = rows[i:i+2]
            assert header.startswith("#EXTINF:") and 'group-title="🗂️ YEDEKLER (2)"' in header, "Non-YEDEKLER append blocked"
            assert url.startswith(("http://", "https://")) and url not in known, "Duplicate or invalid appended URL"
            assert not any(x in header.casefold() for x in ("trt arabi", "trt world")), "Foreign-language channel blocked"
            known.add(url)
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
            assert count >= 2, "Original backups missing"
        else:
            assert int(match.group(1)) == count, f"Category count mismatch: {group}, actual {count}"
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    assert len(sources) >= 3, "Discovery sources missing"
    note = ROOT / "DEVAM_NOTU.md"
    assert note.exists(), "Canonical continuation note missing"
    print("PASS:", len(channels), "channels;", len(backups), "backups;", len(category_counts), "categories;", len(sources), "discovery sources; one continuation note")
if __name__ == "__main__":
    main()

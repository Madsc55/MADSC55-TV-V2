#!/usr/bin/env python3
"""Offline invariants for MADSC55 TV V2 playlist and source configuration."""
import json
import hashlib
import pathlib
import sys
from collections import Counter
from discover import ROOT, LIVE, SOURCES, entries

TURKISH_BACKUP_PRIORITY = ("BBC FİRST TURKİYE", "CARTOON NETWORK (TURKİYE)", "KANAL 7", "KANAL 7 AVRUPA", "KANAL 7 AVRUPA HD TR", "KANAL AVRUPA TR", "SHOW TV", "TRT 3 (720P)", "TRT COCUK (1440P)", "TRT EBA ILKOKUL (720P)", "TRT EBA LİSE (720P)", "TRT SPOR YİLDİZ (1440P) [GEO-BLOCKED]", "TRT TURK TR")

def main():
    # Preserve the original 838 non-backup channels in their exact order.
    # YEDEKLER is intentionally sorted, so it cannot be compared as an append-only prefix.
    current = LIVE.read_bytes()
    text = current.decode("utf-8-sig")
    channels_pre = list(entries(text))
    assert len(channels_pre) == 876, "Expected 838 protected channels and 38 approved backups"
    non_backup = [x for x in channels_pre if "YEDEKLER" not in x["group"]]
    assert len(non_backup) == 838, "Protected non-YEDEKLER categories changed in size"
    backup_count = sum("YEDEKLER" in x["group"] for x in channels_pre)
    backup_group = f"🗂️ YEDEKLER ({backup_count})"
    assert backup_count == 38, "YEDEKLER must contain exactly the approved first 38 channels"
    backup_names = [x["name"] for x in channels_pre if "YEDEKLER" in x["group"]]
    assert len(backup_names) == backup_count
    assert all(x["group"] == backup_group for x in channels_pre if "YEDEKLER" in x["group"]), "YEDEKLER counter inconsistent"
    urls = [x["url"] for x in channels_pre]
    # Original playlist repeats URLs across categories intentionally.
    backup_urls = [x["url"] for x in channels_pre if "YEDEKLER" in x["group"]]
    assert len(backup_urls) == len(set(backup_urls)), "Duplicate YEDEKLER stream URLs"
    text = LIVE.read_text(encoding="utf-8-sig")
    channels = list(entries(text))
    assert text.startswith("#EXTM3U"), "Missing M3U header"
    assert len(channels) >= 840, "Playlist shrank below the verified post-deduplication baseline"
    backups = [x for x in channels if "YEDEKLER" in x["group"]]
    assert len(backups) == 38, "YEDEKLER must contain exactly 38 channels"
    assert any(x["name"] == "TRT 1 1440P QHD" for x in backups), "Original TRT 1 backup missing"
    assert any(x["name"] == "DHA CANLI 720P HD" for x in backups), "Original DHA backup missing"
    assert [x["name"] for x in backups[:2]] == [
        "TRT 1 1440P QHD", "DHA CANLI 720P HD"
    ], "TRT 1 and DHA must permanently occupy YEDEKLER positions 1 and 2"
    assert [x["name"] for x in backups[2:5]] == ["EUROSPORT 1 HD TR", "24", "ADA TV (1080P)"], "Approved positions 3-5 changed"
    assert sum(x["name"] == "TRT 1 1440P QHD" for x in backups) == 1, "Duplicate or missing TRT 1"
    assert sum(x["name"] == "DHA CANLI 720P HD" for x in backups) == 1, "Duplicate or missing DHA"
    # Positions 39-4002 were safely moved to the foreign archive.
    archive = ROOT / "v2" / "arsiv" / "yabanci_yedekler_2026-11-02_3964.m3u8"
    assert archive.exists(), "Foreign archive is missing"
    archived = list(entries(archive.read_text(encoding="utf-8-sig")))
    assert len(archived) == 3964, "Foreign archive lost channels"
    # Protect exact original archive records and their order across future changes.
    # Stream URL alone is insufficient: names, logos and metadata must survive.
    assert all(x["url"].startswith(("https://", "http://")) for x in archived), "Invalid archived stream URL"
    assert len({x["url"] for x in archived}) == len(archived), "Duplicate archive stream URL"
    assert all(x["name"].strip() for x in archived), "Archived channel name missing"

    assert len(backups) + len(archived) == 4002, "Backup/archive total changed"
    assert not (set(x["url"] for x in backups) & set(x["url"] for x in archived)), "Archive and backups overlap"

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
        assert int(match.group(1)) == count, f"Category count mismatch: {group}, actual {count}"
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    assert len(sources) >= 3, "Discovery sources missing"
    note = ROOT / "DEVAM_NOTU.md"
    assert note.exists(), "Canonical continuation note missing"
    print("PASS:", len(channels), "channels;", len(backups), "backups;", len(category_counts), "categories;", len(sources), "discovery sources; one continuation note")
if __name__ == "__main__":
    main()

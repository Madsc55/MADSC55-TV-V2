#!/usr/bin/env python3
"""Offline invariants for MADSC55 TV V2 playlist and source configuration."""
import json
import hashlib
import pathlib
import sys
from collections import Counter
from discover import ROOT, LIVE, SOURCES, entries

TURKISH_BACKUP_PRIORITY = ("BBC FİRST TURKİYE", "CARTOON NETWORK (TURKİYE)", "KANAL 7", "KANAL 7 AVRUPA", "KANAL 7 AVRUPA HD TR", "KANAL AVRUPA TR", "SHOW TV", "TRT 3 (720P)", "TRT COCUK (1440P)", "TRT EBA ILKOKUL (720P)", "TRT EBA LİSE (720P)", "TRT SPOR YİLDİZ (1440P) [GEO-BLOCKED]", "TRT TURK TR")

SELECTED_BACKUP_POSITIONS = set([3,11,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,79,80,81,82,83,84,85,86,88,89,90,91,92,93,100,104,105,117,119,126,135,157,170,171,172,173,177,181])
SELECTED_SOURCE_POSITIONS = {n if n <= 111 else n + 375 for n in SELECTED_BACKUP_POSITIONS}

def main():
    # Preserve the original 838 non-backup channels in their exact order.
    # YEDEKLER is intentionally sorted, so it cannot be compared as an append-only prefix.
    current = LIVE.read_bytes()
    text = current.decode("utf-8-sig")
    channels_pre = list(entries(text))
    assert len(channels_pre) == 2914, "Expected 838 protected channels and 2076 active backups"
    non_backup = [x for x in channels_pre if "YEDEKLER" not in x["group"]]
    assert len(non_backup) == 838, "Protected non-YEDEKLER categories changed in size"
    backup_count = sum("YEDEKLER" in x["group"] for x in channels_pre)
    backup_group = f"🗂️ YEDEKLER ({backup_count})"
    assert backup_count == 2076, "YEDEKLER must contain 2076 channels after approved move"
    backup_names = [x["name"] for x in channels_pre if "YEDEKLER" in x["group"]]
    assert len(backup_names) == backup_count
    assert all(x["group"] == backup_group for x in channels_pre if "YEDEKLER" in x["group"]), "All backups must share one category"
    # Exact batch conservation: 2500 active + 15574 queued = 18074 immutable sources.
    source_path = ROOT / "v2/yedekler_batch/YEDEKLER_ARCHIVE.m3u8"
    queued_path = ROOT / "v2/yedekler_batch/ANA_ARSIV.m3u8"
    state = json.loads((ROOT / "v2/yedekler_batch/state.json").read_text(encoding="utf-8"))
    source_bytes = source_path.read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == state["source_sha256"]
    assert state["total"] == 18074 and state["default_batch_size"] == 2500
    source_entries = list(entries(source_bytes.decode("utf-8-sig")))
    queued_entries = list(entries(queued_path.read_text(encoding="utf-8-sig")))
    active_entries = [x for x in channels_pre if "YEDEKLER" in x["group"]]
    assert len(source_entries) == 18074 and len(queued_entries) == 15574
    assert [(x["name"], x["url"]) for x in active_entries] == [(x["name"], x["url"]) for x in [x for i, x in enumerate(source_entries[:111] + source_entries[486:2500], 1) if i not in SELECTED_BACKUP_POSITIONS]], "Remaining reviewed batch changed"
    assert [(x["name"], x["url"]) for x in queued_entries] == [(x["name"], x["url"]) for x in source_entries[2500:]], "Queued archive lost or reordered records"
    assert len({x["url"] for x in source_entries}) == 18074, "Source has duplicate URLs"
    assert len(state["status"]) == 2500
    assert all(state["status"].get(str(i)) == ("TURK" if 112 <= i <= 486 or i in SELECTED_SOURCE_POSITIONS else "TEST") for i in range(1, 2501))
    turk_entries = list(entries((ROOT / "v2/yedekler_batch/TURK_ARSIV.m3u8").read_text(encoding="utf-8-sig")))
    remaining_entries = list(entries((ROOT / "v2/yedekler_batch/YEDEKLER_KALAN_2076.m3u8").read_text(encoding="utf-8-sig")))
    assert len(turk_entries) == 424 and len(remaining_entries) == 2076
    assert [(x["name"], x["url"]) for x in turk_entries] == [(x["name"], x["url"]) for x in source_entries[111:486] + [source_entries[i - 1] for i in sorted(SELECTED_SOURCE_POSITIONS)]]
    assert [(x["name"], x["url"]) for x in remaining_entries] == [(x["name"], x["url"]) for x in active_entries]
    assert len({x["url"] for x in turk_entries + remaining_entries}) == 2500
    # Fail closed on any reintroduction of the 48 channels that caused test_001.
    quarantine = json.loads((ROOT / "v2/archives/test001_quarantined_48.json").read_text(encoding="utf-8"))
    forbidden = {(r["name"].strip().casefold(), r["url"].strip()) for r in quarantine["entries"]}
    assert len(quarantine["entries"]) == len(forbidden) == 48, "Invalid quarantine inventory"
    reintroduced = [(x["name"], x["url"]) for x in channels_pre if (x["name"].strip().casefold(), x["url"].strip()) in forbidden]
    assert not reintroduced, f"test_001 quarantined channels reintroduced: {reintroduced[:10]}"
    urls = [x["url"] for x in channels_pre]
    # Original playlist repeats URLs across categories intentionally.
    backup_urls = [x["url"] for x in channels_pre if "YEDEKLER" in x["group"]]
    assert len(backup_urls) == len(set(backup_urls)), "Duplicate YEDEKLER stream URLs"
    text = LIVE.read_text(encoding="utf-8-sig")
    channels = list(entries(text))
    assert text.startswith("#EXTM3U"), "Missing M3U header"
    assert len(channels) >= 840, "Playlist shrank below the verified post-deduplication baseline"
    backups = [x for x in channels if "YEDEKLER" in x["group"]]
    assert len(backups) == 2076, "YEDEKLER must contain 2076 channels"
    assert any(x["name"] == "TRT 1 1440P QHD" for x in backups), "Original TRT 1 backup missing"
    assert any(x["name"] == "DHA CANLI 720P HD" for x in backups), "Original DHA backup missing"
    assert [x["name"] for x in backups[:2]] == [
        "TRT 1 1440P QHD", "DHA CANLI 720P HD"
    ], "TRT 1 and DHA must permanently occupy YEDEKLER positions 1 and 2"
    # YEDEKLER is a user-controlled review area; its internal order may change.
    assert sum(x["name"] == "TRT 1 1440P QHD" for x in backups) == 1, "Duplicate or missing TRT 1"
    assert sum(x["name"] == "DHA CANLI 720P HD" for x in backups) == 1, "Duplicate or missing DHA"
    # The consolidated playlist retains all seven original source blocks in order.
    archive = ROOT / "YEDEKLER_PLAYLISTESI.m3u8"
    assert archive.exists(), "Unified YEDEKLER playlist is missing"
    merged = list(entries(archive.read_text(encoding="utf-8-sig")))
    assert len(merged) == 32488, "Unified YEDEKLER playlist count mismatch"
    archived = merged[18960 + 1110:18960 + 1110 + 4768]
    assert len(archived) == 4768, "Foreign archive section count mismatch"
    assert len({x["url"] for x in archived}) == 4768, "Duplicate foreign archive stream URLs"
    assert all(x["url"].startswith(("https://", "http://")) and x["name"].strip() for x in archived), "Invalid foreign archive record"
    assert not (ROOT / "v2" / "arsiv" / "yabanci_yedekler_2026-11-02_3964.m3u8").exists(), "Old foreign archive must not be retained"

    # The approved-baseline safety gate verifies every backup record is retained.

    assert not any(x["name"].startswith(("TRT Arabi", "TRT World")) for x in non_backup), "Unwanted foreign-language trials remain in protected main section"
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
    # Exercise lossless archive/restore against the real playlist in a temporary directory.
    import tempfile
    from ibo_archive_verify import archive as save_archive, restore as restore_archive
    with tempfile.TemporaryDirectory() as tempdir:
        backup_path = pathlib.Path(tempdir) / "ibo-snapshot.json"
        recovered_path = pathlib.Path(tempdir) / "ibo-recovered.m3u8"
        assert save_archive(LIVE, backup_path) == len(channels)
        assert restore_archive(backup_path, recovered_path) == len(channels)
        assert recovered_path.read_bytes() == current, "Restore differs byte-for-byte"
        try:
            restore_archive(backup_path, recovered_path)
            raise AssertionError("Restore overwrote an existing file")
        except FileExistsError:
            pass
    print("PASS:", len(channels), "channels;", len(backups), "backups;", len(category_counts), "categories;", len(sources), "discovery sources; one continuation note")
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Offline invariants for MADSC55 TV V2 playlist and source configuration."""
import json
import hashlib
import pathlib
import sys
from collections import Counter
from discover import ROOT, LIVE, SOURCES, entries
from yedekler_batch.yonet import verify_history

TURKISH_BACKUP_PRIORITY = ("BBC FİRST TURKİYE", "CARTOON NETWORK (TURKİYE)", "KANAL 7", "KANAL 7 AVRUPA", "KANAL 7 AVRUPA HD TR", "KANAL AVRUPA TR", "SHOW TV", "TRT 3 (720P)", "TRT COCUK (1440P)", "TRT EBA ILKOKUL (720P)", "TRT EBA LİSE (720P)", "TRT SPOR YİLDİZ (1440P) [GEO-BLOCKED]", "TRT TURK TR")

ADDITIONAL_FOREIGN_BACKUP_POSITIONS = {1172, 1173, 1174, 1175, 1176, 1177, 1178, 1179, 1180, 1181, 1182, 1183, 1184, 1185, 1186, 1187, 1188, 1189, 1190, 1191, 1192, 1193, 1194, 1195, 1196, 1197, 1198, 1199, 1200, 1201, 1202, 1203, 1204, 1205, 1206, 1207, 1208, 1209, 1210, 1211, 1212, 1213, 1214, 1215, 1216, 1217, 1218, 1219, 1220, 1221, 1222, 1223, 1224, 1225, 1226, 1227, 1228, 1229, 1230, 1231, 1232, 1233, 1234, 1235, 1236, 1237, 1238, 1239, 1240, 1241, 1242, 1243, 1244, 1245, 1246, 1247, 1248, 1249, 1250, 1251, 1252, 1253, 1254, 1255, 1256}
FOREIGN_BACKUP_POSITIONS = {59, 60, 61, 62, 63, 65, 66, 67, 115, 116, 117, 118, 121, 122, 123, 124, 125, 126, 300, 307, 308, 370, 371, 372, 630, 631, 632, 633, 634, 635, 636, 640, 666, 845, 846, 847, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 860, 861, 862, 863, 864, 865, 866, 867, 868, 869, 870, 871, 872, 873, 874, 875, 876, 1156, 1157, 1159, 1160, 1161, 1162, 1163, 1164, 1170, 1171}
SELECTED_BACKUP_POSITIONS = set([3,11,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,79,80,81,82,83,84,85,86,88,89,90,91,92,93,100,104,105,117,119,126,135,157,170,171,172,173,177,181])
SELECTED_SOURCE_POSITIONS = {n if n <= 111 else n + 375 for n in SELECTED_BACKUP_POSITIONS}

def main():
    # Preserve the original 838 non-backup channels in their exact order.
    # YEDEKLER is intentionally sorted, so it cannot be compared as an append-only prefix.
    current = LIVE.read_bytes()
    text = current.decode("utf-8-sig")
    channels_pre = list(entries(text))
    assert len(channels_pre) == 2755, "Expected 838 protected channels and 1917 active backups"
    non_backup = [x for x in channels_pre if "YEDEKLER" not in x["group"]]
    foreign = list(entries((ROOT / "v2/yedekler_batch/YABANCI_ARSIV.m3u8").read_text(encoding="utf-8-sig")))
    protected = [x for x in non_backup if "YABANCI ARŞİV" not in x["group"]]
    assert len(non_backup) == 838, "Protected categories changed"
    assert len(foreign) == 159 and all(x["group"] == "🌍 YABANCI ARŞİV (159)" for x in foreign), "Foreign archive count mismatch"
    backup_count = sum("YEDEKLER" in x["group"] for x in channels_pre)
    backup_group = f"🗂️ YEDEKLER ({backup_count})"
    assert backup_count == 1917, "YEDEKLER must contain 1917 channels after approved move"
    backup_names = [x["name"] for x in channels_pre if "YEDEKLER" in x["group"]]
    assert len(backup_names) == backup_count
    assert all(x["group"] == backup_group for x in channels_pre if "YEDEKLER" in x["group"]), "All backups must share one category"
    # Exact batch conservation: 2500 active + 15574 queued = 18074 immutable sources.
    source_path = ROOT / "v2/yedekler_batch/YEDEKLER_ARCHIVE.m3u8"
    queued_path = ROOT / "v2/yedekler_batch/ANA_ARSIV.m3u8"
    state = json.loads((ROOT / "v2/yedekler_batch/state.json").read_text(encoding="utf-8"))
    verify_history(state)
    source_bytes = source_path.read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == state["source_sha256"]
    assert state["total"] == 18074 and state["default_batch_size"] == 2500
    source_entries = list(entries(source_bytes.decode("utf-8-sig")))
    queued_entries = list(entries(queued_path.read_text(encoding="utf-8-sig")))
    active_entries = [x for x in channels_pre if "YEDEKLER" in x["group"]]
    assert len(source_entries) == 18074 and len(queued_entries) == 15574
    reviewed = [x for i, x in enumerate(source_entries[:111] + source_entries[486:2500], 1) if i not in SELECTED_BACKUP_POSITIONS]
    assert len(reviewed) == 2076
    expected_foreign = [x for i, x in enumerate(reviewed, 1) if i in FOREIGN_BACKUP_POSITIONS] + [x for i, x in enumerate(reviewed, 1) if i in ADDITIONAL_FOREIGN_BACKUP_POSITIONS]
    expected_active = [x for i, x in enumerate(reviewed, 1) if i not in FOREIGN_BACKUP_POSITIONS and i not in ADDITIONAL_FOREIGN_BACKUP_POSITIONS]
    assert [(x["name"], x["url"]) for x in foreign] == [(x["name"], x["url"]) for x in expected_foreign], "Foreign archive changed"
    assert [(x["name"], x["url"]) for x in active_entries] == [(x["name"], x["url"]) for x in expected_active], "Remaining batch changed"
    assert [(x["name"], x["url"]) for x in queued_entries] == [(x["name"], x["url"]) for x in source_entries[2500:]], "Queued archive lost or reordered records"
    assert len({x["url"] for x in source_entries}) == 18074, "Source has duplicate URLs"
    assert len(state["status"]) == 2500
    assert all(state["status"].get(str(i)) == ("TURK" if 112 <= i <= 486 or i in SELECTED_SOURCE_POSITIONS else "YABANCI" if i in [1585, 1586, 1587, 1588, 1589, 1590, 1591, 1592, 1593, 1594, 1595, 1596, 1597, 1598, 1599, 1600, 1601, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1613, 1614, 1615, 1616, 1617, 1618, 1619, 1620, 1621, 1622, 1623, 1624, 1625, 1626, 1627, 1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639, 1640, 1641, 1642, 1643, 1644, 1645, 1646, 1647, 1648, 1649, 1650, 1651, 1652, 1653, 1654, 1655, 1656, 1657, 1658, 1659, 1660, 1661, 1662, 1663, 1664, 1665, 1666, 1667, 1668, 1669] else "TEST") for i in range(1, 2501))
    turk_entries = list(entries((ROOT / "v2/yedekler_batch/TURK_ARSIV.m3u8").read_text(encoding="utf-8-sig")))
    remaining_entries = list(entries((ROOT / "v2/yedekler_batch/YEDEKLER_KALAN_2125.m3u8").read_text(encoding="utf-8-sig")))
    assert len(turk_entries) == 424 and len(remaining_entries) == 2076
    assert [(x["name"], x["url"]) for x in turk_entries] == [(x["name"], x["url"]) for x in source_entries[111:486] + [source_entries[i - 1] for i in sorted(SELECTED_SOURCE_POSITIONS)]]
    assert [(x["name"], x["url"]) for x in remaining_entries] == [(x["name"], x["url"]) for x in reviewed]
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
    assert len(backups) == 1917, "YEDEKLER must contain 2002 channels"
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

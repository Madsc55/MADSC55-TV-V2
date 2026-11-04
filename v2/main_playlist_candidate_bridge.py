#!/usr/bin/env python3
"""Strict read-only bridge from the protected V2 main playlists to orphan evidence.

No rewriting, importing or automatically promoting any archived channels.
Use only pinned exact Git blob identities, then match immutable EXTINF/EPG.
"""
import hashlib
from pathlib import Path
import re

PINNED_BLOBS = {
    "v2-main-ibo-876": "165c726cd9211f9f51c31f1c718e0911bab79e1b",
    "v2-main-foreign-3964": "c54272e97f711c3074303cec74739d6d0ec806b2",
}
MAX_SNAPSHOT_BYTES = 8_000_000
ANCHORS = ("TRT 1 1440P QHD", "DHA CANLI 720P HD")


def read_verified_snapshot(source):
    if source.get("origin") != "v2-main-protected-playlist":
        raise ValueError("Not a pinned V2 main snapshot")
    identity = source.get("id")
    if identity not in PINNED_BLOBS:
        raise ValueError("Unrecognized V2 main playlist identity")
    p = Path(source["local_path"])
    if p.is_symlink() or not p.is_file():
        raise ValueError("Missing or symlinked protected V2 source")
    raw = p.read_bytes()
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Protected V2 source exceeds size guard")
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
    if actual != PINNED_BLOBS[identity]:
        raise ValueError("Protected V2 main playlist Git blob mismatch")
    text = raw.decode("utf-8-sig")
    if not text.lstrip().startswith("#EXTM3U"):
        raise ValueError("Protected source is not M3U")
    return text


def _entries(text):
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("#EXTINF:"):
            continue
        match = re.search(r'\bgroup-title="([^"]*)"', line)
        rows.append((line.rsplit(",", 1)[-1].strip(), match.group(1) if match else ""))
    return rows


def validated_v2_main_catalog(main_path, foreign_archive_path):
    catalog = [
        {"id": "v2-main-ibo-876", "origin": "v2-main-protected-playlist",
         "local_path": str(main_path), "scope": "candidate", "kind": "m3u"},
        {"id": "v2-main-foreign-3964", "origin": "v2-main-protected-playlist",
         "local_path": str(foreign_archive_path), "scope": "candidate", "kind": "m3u"},
    ]
    if Path(main_path).resolve() == Path(foreign_archive_path).resolve():
        raise ValueError("V2 main and foreign snapshots must be separate")
    main_rows = _entries(read_verified_snapshot(catalog[0]))
    archived_rows = _entries(read_verified_snapshot(catalog[1]))
    backups = [name for name, group in main_rows if "YEDEKLER" in group]
    if len(main_rows) != 876 or len(backups) != 38 or tuple(backups[:2]) != ANCHORS:
        raise ValueError("Protected V2 main 876/38/two anchor contract mismatch")
    if len(archived_rows) != 3964:
        raise ValueError("Protected V2 foreign archive 3964 contract mismatch")
    if any("YEDEKLER" not in group for _, group in archived_rows):
        raise ValueError("Original foreign snapshot legacy group metadata changed")
    return catalog, {
        "active_main_channels": len(main_rows),
        "active_yedekler": len(backups),
        "fixed_anchor_channels": 2,
        "separate_archived_yabancilar": len(archived_rows),
        "archived_group_metadata": "LEGACY_YEDEKLER_HEADER_NOT_ACTIVE_PLAYLIST",
        "immutable_blobs_verified": True,
        "ibo_device_verified": False,
        "playlist_modified": False,
    }

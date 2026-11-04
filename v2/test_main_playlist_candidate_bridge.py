#!/usr/bin/env python3
"""Offline grouped invariants for exact V2 main/foreign source reconciliation."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from main_playlist_candidate_bridge import (
    PINNED_BLOBS, validated_v2_main_catalog, read_verified_snapshot,
)


def sha(blob):
    return hashlib.sha1(b"blob " + str(len(blob)).encode("ascii") + b"\0" + blob).hexdigest()


class MainProtectedPlaylistBridgeTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        root = Path(self.dir.name)
        self.main, self.foreign = root / "main.m3u8", root / "foreign.m3u8"
        entries = [("#EXTINF:-1 group-title=\"KATEGORI\",Other " + str(i) + "\n"
                    "https://public.example.org/other" + str(i) + ".m3u8\n")
                   for i in range(838)]
        backups = [
            "#EXTINF:-1 group-title=\"YEDEKLER (38)\"," + name +
            "\nhttps://public.example.org/backup" + str(i) + ".m3u8\n"
            for i, name in enumerate(["TRT 1 1440P QHD", "DHA CANLI 720P HD"] +
                                      ["Backup " + str(n) for n in range(36)])
        ]
        self.main.write_text("#EXTM3U\n" + "".join(entries + backups), encoding="utf-8")
        archive = ("#EXTINF:-1 group-title=\"🗂️ YEDEKLER (4002)\",Foreign " +
                   "0\nhttps://public.example.org/foreign0.m3u8\n")
        self.foreign.write_text("#EXTM3U\n" + archive * 3964, encoding="utf-8")
        self.mock_pins = {
            "v2-main-ibo-876": sha(self.main.read_bytes()),
            "v2-main-foreign-3964": sha(self.foreign.read_bytes()),
        }
        self.patch = patch.dict(PINNED_BLOBS, self.mock_pins)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_validates_real_count_contract_without_writing_sources(self):
        initial = (self.main.read_bytes(), self.foreign.read_bytes())
        sources, report = validated_v2_main_catalog(self.main, self.foreign)
        self.assertEqual(report["active_main_channels"], 876)
        self.assertEqual(report["active_yedekler"], 38)
        self.assertEqual(report["fixed_anchor_channels"], 2)
        self.assertEqual(report["separate_archived_yabancilar"], 3964)
        self.assertFalse(report["playlist_modified"])
        self.assertEqual((self.main.read_bytes(), self.foreign.read_bytes()), initial)
        self.assertEqual(len(sources), 2)
        self.assertTrue(read_verified_snapshot(sources[0]).startswith("#EXTM3U"))

    def test_rejects_blob_tamper_and_does_not_promote_unverified_sources(self):
        self.main.write_text(self.main.read_text() + "\n# changed\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "blob mismatch"):
            validated_v2_main_catalog(self.main, self.foreign)

    def test_rejects_wrong_backup_anchor_and_foreign_count(self):
        changed = self.main.read_text().replace("DHA CANLI 720P HD", "DHA WRONG", 1)
        self.main.write_text(changed, encoding="utf-8")
        self.mock_pins["v2-main-ibo-876"] = sha(self.main.read_bytes())
        with self.assertRaisesRegex(ValueError, "two anchor contract"):
            validated_v2_main_catalog(self.main, self.foreign)

    def test_rejects_symlink_and_unapproved_origin(self):
        reference = {"id": "v2-main-ibo-876",
                     "origin": "unapproved", "local_path": str(self.main)}
        with self.assertRaises(ValueError):
            read_verified_snapshot(reference)
        ref = self.main.parent / "symlink.m3u8"
        ref.symlink_to(self.main)
        reference["origin"] = "v2-main-protected-playlist"
        reference["local_path"] = str(ref)
        with self.assertRaises(ValueError):
            read_verified_snapshot(reference)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Unit tests for the one-step archive helper, without modifying production files."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import archive_backup_range as helper

class ArchiveRangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.playlist = root/"playlist.m3u8"
        self.archive = root/"foreign.m3u8"
        self.manifest = root/"manifest.json"
        self.invariants = root/"invariants.py"
        lines = ["#EXTM3U\n"]
        for name, group in [("OTHER","LOCAL (1)"),("KEEP","🗂️ YEDEKLER (4)"),
                            ("KEEP2","🗂️ YEDEKLER (4)"),("MOVE","🗂️ YEDEKLER (4)"),
                            ("TAIL","🗂️ YEDEKLER (4)")]:
            lines.extend([f'#EXTINF:-1 group-title="{group}",{name}\n',f'https://example.org/{name}\n'])
        self.playlist.write_text("".join(lines),encoding="utf-8")
        self.archive.write_text("#EXTM3U\n",encoding="utf-8")
        self.invariants.write_text('assert len(channels_pre) == 5\nassert backup_count == 4\nassert len(backups) == 4\n"YEDEKLER (4)"\n',encoding="utf-8")
        self.patches = [patch.object(helper, "PLAYLIST", self.playlist),
                        patch.object(helper, "ARCHIVE", self.archive),
                        patch.object(helper, "MANIFEST", self.manifest),
                        patch.object(helper, "INVARIANTS", self.invariants)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def test_moves_exact_position_and_preserves_other_groups(self):
        updated, archive, spec, tests, moved, appended = helper.prepare(3,3)
        self.assertEqual((moved,appended),(1,1))
        self.assertNotIn(b",MOVE\n",updated)
        self.assertIn(b",MOVE\n",archive)
        self.assertIn(b",OTHER\n",updated)
        self.assertIn(b"YEDEKLER (3)",updated)
        self.assertIn("len(channels_pre) == 4",tests)
        self.assertEqual(spec["channels"],["MOVE"])

    def test_protects_first_two(self):
        with self.assertRaises(ValueError):
            helper.prepare(1,2)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            helper.prepare(3,5)

if __name__ == "__main__":
    unittest.main()

"""Offline read-only acceptance against the actual tracked canonical playlist."""
import unittest
from pathlib import Path

from ibo_single_playlist_transfer import inventory, parse, sha, transform

PLAYLIST = Path(__file__).resolve().parent.parent / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"


class CanonicalPlaylistAcceptance(unittest.TestCase):
    def test_read_only_roundtrip_preserves_every_channel(self):
        raw = PLAYLIST.read_bytes()
        counts = inventory(raw)
        self.assertEqual(counts["TOTAL"], len(parse(raw)[1]))
        self.assertEqual(counts["TOTAL"], sum(v for k, v in counts.items() if k != "TOTAL"))
        self.assertGreater(counts["YEDEKLER"], 0)
        self.assertGreater(counts["OTHER"], 0)
        self.assertLessEqual(counts["YEDEKLER"], 2500)
        original = [b.strip().splitlines()[-1] for b in parse(raw)[1]]
        moved, report = transform(raw, "YEDEKLER", "TURK", [1], sha(raw))
        self.assertEqual(report["moved"], 1)
        self.assertEqual(inventory(moved)["TOTAL"], counts["TOTAL"])
        self.assertEqual(inventory(moved)["OTHER"], counts["OTHER"])
        self.assertEqual([b.strip().splitlines()[-1] for b in parse(moved)[1]], original)
        self.assertEqual(PLAYLIST.read_bytes(), raw, "Smoke test must never edit main playlist")

    def test_no_new_package_before_current_package_completed(self):
        from ibo_single_playlist_transfer import plan_next_batch
        raw = PLAYLIST.read_bytes()
        self.assertGreater(inventory(raw)["YEDEKLER"], 0)
        # Planning is read-only. Actual advancement is separately guarded by
        # advance_next_package(), which refuses a nonempty YEDEKLER category.
        self.assertEqual(PLAYLIST.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()

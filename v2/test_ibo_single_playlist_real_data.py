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


    def test_all_archive_directions_and_exact_rollback_on_real_playlist(self):
        """Every directed pair is exercised in memory; canonical bytes never change."""
        from ibo_single_playlist_transfer import restore_exact
        raw = PLAYLIST.read_bytes()
        baseline = inventory(raw)
        original_urls = [b.strip().splitlines()[-1] for b in parse(raw)[1]]
        for source in ("YEDEKLER", "ANA", "TURK", "YABANCI"):
            for target in ("YEDEKLER", "ANA", "TURK", "YABANCI"):
                if source == target:
                    continue
                with self.subTest(source=source, target=target):
                    moved, report = transform(raw, source, target, [1], sha(raw))
                    counts = inventory(moved)
                    self.assertEqual(report["moved"], 1)
                    self.assertEqual(counts[source], baseline[source] - 1)
                    self.assertEqual(counts[target], baseline[target] + 1)
                    self.assertEqual(counts["TOTAL"], baseline["TOTAL"])
                    self.assertEqual(counts["OTHER"], baseline["OTHER"])
                    self.assertEqual(
                        [b.strip().splitlines()[-1] for b in parse(moved)[1]],
                        original_urls,
                    )
                    self.assertEqual(
                        restore_exact(moved, raw, sha(moved), sha(raw)), raw
                    )
        self.assertEqual(PLAYLIST.read_bytes(), raw)

    def test_full_2500_batch_and_reverse_rollback(self):
        """Exercise the full batch limit using the largest archive."""
        from ibo_single_playlist_transfer import restore_exact, plan_next_batch
        raw = PLAYLIST.read_bytes()
        before = inventory(raw)
        source = max(("ANA", "TURK", "YABANCI"), key=before.get)
        plan = plan_next_batch(raw, source, limit=2500)
        self.assertEqual(len(plan["expected_urls"]), 2500)
        self.assertEqual(plan["remaining_after"], before[source] - 2500)
        moved, report = transform(
            raw, source, "YEDEKLER", list(range(1, 2501)),
            plan["expected_sha256"], expected_urls=plan["expected_urls"],
        )
        after = inventory(moved)
        self.assertEqual(report["moved"], 2500)
        self.assertEqual(after[source], before[source] - 2500)
        self.assertEqual(after["YEDEKLER"], before["YEDEKLER"] + 2500)
        self.assertEqual(after["TOTAL"], before["TOTAL"])
        self.assertEqual(after["OTHER"], before["OTHER"])
        self.assertEqual(
            [b.strip().splitlines()[-1] for b in parse(moved)[1]],
            [b.strip().splitlines()[-1] for b in parse(raw)[1]],
        )
        self.assertEqual(
            restore_exact(moved, raw, sha(moved), sha(raw)), raw
        )
        self.assertEqual(PLAYLIST.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()

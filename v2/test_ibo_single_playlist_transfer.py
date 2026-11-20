import hashlib
import unittest

from ibo_single_playlist_transfer import parse, transform, sha, category, inventory, restore_exact

SAMPLE = ('#EXTM3U\n'
          '#EXTINF:-1 group-title="⭐ FAVORİLER (1)",Favorite\nhttps://example.org/f\n'
          '#EXTINF:-1 group-title="🗂️ YEDEKLER (3)",One\nhttps://example.org/1\n'
          '#EXTINF:-1 group-title="🗂️ YEDEKLER (1)",Two\nhttps://example.org/2\n'
          '#EXTINF:-1 group-title="🗂️ YEDEKLER (3)",Three\nhttps://example.org/3\n').encode()


class SinglePlaylistTransferTests(unittest.TestCase):
    def test_move_preserves_unselected_and_count(self):
        output, report = transform(SAMPLE, "YEDEKLER", "TURK", [1, 3], sha(SAMPLE))
        self.assertEqual(report["moved"], 2)
        self.assertEqual(report["total"], 4)
        self.assertEqual(len(parse(output)[1]), 4)
        self.assertIn("TÜRK ARŞİVİ (2)", output.decode())
        self.assertIn(b'group-title="\xe2\xad\x90 FAVOR', output)
        self.assertIn(b'group-title="\xf0\x9f\x97\x82\xef\xb8\x8f YEDEKLER (3)",Two', output)
        self.assertEqual(sum(category(b.split("\n")[0]) == "TURK"
                             for b in parse(output)[1]), 2)

    def test_sha_lock(self):
        with self.assertRaisesRegex(ValueError, "SHA"):
            transform(SAMPLE, "YEDEKLER", "ANA", [1], "0" * 64)

    def test_out_of_bounds(self):
        with self.assertRaisesRegex(ValueError, "Ordinal"):
            transform(SAMPLE, "YEDEKLER", "ANA", [4], sha(SAMPLE))

    def test_duplicate_selection(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            transform(SAMPLE, "YEDEKLER", "ANA", [1, 1], sha(SAMPLE))

    def test_roundtrip_categories(self):
        output, _ = transform(SAMPLE, "YEDEKLER", "TURK", [2], sha(SAMPLE))
        restored, _ = transform(output, "TURK", "YEDEKLER", [1], sha(output))
        self.assertEqual(len(parse(restored)[1]), 4)
        self.assertIn("YEDEKLER (3)", restored.decode())
        self.assertEqual(sum(category(b.split("\n")[0]) == "YEDEKLER"
                             for b in parse(restored)[1]), 3)

    def test_duplicate_url_fails_closed(self):
        duplicated = SAMPLE + ('#EXTINF:-1 group-title="🗂️ YEDEKLER (4)",Again\n'
                               'https://example.org/1\n').encode()
        with self.assertRaisesRegex(ValueError, "Duplicate stream URL"):
            transform(duplicated, "YEDEKLER", "ANA", [1], sha(duplicated))

    def test_transform_enforces_2500_limit(self):
        with self.assertRaisesRegex(ValueError, "2500"):
            transform(SAMPLE, "YEDEKLER", "ANA", [1] * 2501, sha(SAMPLE))

    def test_exact_url_manifest_prevents_stale_ordinals(self):
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
            transform(SAMPLE, "YEDEKLER", "ANA", [1], sha(SAMPLE),
                      expected_urls=["https://example.org/2"])
        output, report = transform(SAMPLE, "YEDEKLER", "ANA", [1], sha(SAMPLE),
                                   expected_urls=["https://example.org/1"])
        self.assertEqual(report["moved"], 1)
        self.assertEqual(len(report["selected_urls_sha256"]), 64)
        self.assertEqual(len(parse(output)[1]), len(parse(SAMPLE)[1]))

    def test_full_inventory_parity_and_exact_rollback(self):
        output, report = transform(SAMPLE, "YEDEKLER", "ANA", [1, 3], sha(SAMPLE))
        self.assertEqual(report["counts_before"]["YEDEKLER"], 3)
        self.assertEqual(report["counts_after"]["YEDEKLER"], 1)
        self.assertEqual(report["counts_after"]["ANA"], 2)
        self.assertEqual(report["counts_after"]["OTHER"], 1)
        self.assertEqual(report["counts_after"]["TOTAL"], 4)
        self.assertEqual(restore_exact(output, SAMPLE, sha(output), sha(SAMPLE)), SAMPLE)

    def test_rollback_rejects_intervening_changes(self):
        output, _ = transform(SAMPLE, "YEDEKLER", "TURK", [1], sha(SAMPLE))
        with self.assertRaisesRegex(ValueError, "SHA"):
            restore_exact(output + b"\\n", SAMPLE, sha(output), sha(SAMPLE))

    def test_inclusive_range_math(self):
        self.assertEqual(len(list(range(112, 486 + 1))), 375)


if __name__ == "__main__":
    unittest.main()

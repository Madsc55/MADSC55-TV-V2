import hashlib
import unittest

from ibo_single_playlist_transfer import parse, transform, sha, category

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

    def test_inclusive_range_math(self):
        self.assertEqual(len(list(range(112, 486 + 1))), 375)


if __name__ == "__main__":
    unittest.main()

import unittest
from live_archive_key import resolve_key

class LiveArchiveKeyTests(unittest.TestCase):
    def test_existing_passphrase_derives_stable_hex_key(self):
        first, source = resolve_key("", "a sufficiently long private passphrase")
        second, _ = resolve_key("", "a sufficiently long private passphrase")
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)
        self.assertEqual(source, "passphrase-scrypt-v1")

    def test_distinct_passphrases_derive_distinct_keys(self):
        self.assertNotEqual(resolve_key("", "one sufficiently long passphrase")[0],
                            resolve_key("", "another sufficiently long passphrase")[0])

    def test_valid_hex_has_priority(self):
        self.assertEqual(resolve_key("AB" * 32, "a sufficiently long passphrase"),
                         ("ab" * 32, "hex"))

    def test_invalid_hex_falls_back_to_existing_passphrase(self):
        self.assertEqual(resolve_key("not-hex", "a sufficiently long passphrase")[1],
                         "passphrase-scrypt-v1")

    def test_missing_or_short_passphrase_fails_closed(self):
        for phrase in ("", "short", "   "):
            with self.subTest(phrase=phrase):
                with self.assertRaises(ValueError):
                    resolve_key("", phrase)

if __name__ == "__main__":
    unittest.main()

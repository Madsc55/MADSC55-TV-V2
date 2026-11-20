import hashlib
import tempfile
import unittest
from pathlib import Path
from v2.ibo_main_playlist_transfer import MAIN, move, run

def fixture():
    rows = ["#EXTM3U\n"]
    for i in range(2600):
        group = "YEDEKLER" if i < 2505 else "FAVORİLER"
        rows += [f'#EXTINF:-1 group-title="{group}",Channel {i}\n',
                 f'https://example.invalid/{i}\n']
    return "".join(rows).encode()

class TransferTests(unittest.TestCase):
    def test_batch_and_category_parity(self):
        raw = fixture()
        updated, summary = move(raw, "YEDEKLER", "ANA ARŞİV", 1, 2500)
        self.assertEqual(summary["moved"], 2500)
        self.assertEqual(summary["after"]["YEDEKLER"], 5)
        self.assertEqual(summary["after"]["ANA ARŞİV"], 2500)
        self.assertEqual(summary["after"]["FAVORİLER"], 95)
        self.assertEqual(updated.count(b"https://example.invalid/"), 2600)
        next_data, s2 = move(updated, "ANA ARŞİV", "TURK ARŞİVİ", 112, 486)
        self.assertEqual(s2["moved"], 375)
        self.assertEqual(s2["after"]["TURK ARŞİVİ"], 375)
        self.assertEqual(s2["after"]["ANA ARŞİV"], 2125)
        self.assertEqual(next_data.count(b"https://example.invalid/"), 2600)

    def test_stale_no_replay_and_undo(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            path = root / MAIN
            path.write_bytes(fixture())
            journal = root / "transaction.json"
            before = path.read_bytes()
            digest = hashlib.sha256(before).hexdigest()
            preview = run(path, journal, "YEDEKLER", "ANA ARŞİV", 1, 2500, digest)
            self.assertFalse(preview["applied"])
            self.assertEqual(path.read_bytes(), before)
            run(path, journal, "YEDEKLER", "ANA ARŞİV", 1, 2500, digest, apply=True)
            self.assertNotEqual(path.read_bytes(), before)
            with self.assertRaises(ValueError):
                run(path, journal, "YEDEKLER", "ANA ARŞİV", 1, 2500, digest, apply=True)
            after_sha = hashlib.sha256(path.read_bytes()).hexdigest()
            run(path, journal, expected_sha=after_sha, apply=True, undo=True)
            self.assertEqual(path.read_bytes(), before)

    def test_reject_invalid_batch(self):
        with self.assertRaises(ValueError):
            move(fixture(), "YEDEKLER", "ANA ARŞİV", 1, 2501)
        with self.assertRaises(ValueError):
            move(fixture(), "YEDEKLER", "ANA ARŞİV", 0, 10)

if __name__ == "__main__":
    unittest.main()

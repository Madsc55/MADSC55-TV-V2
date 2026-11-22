"""Offline migration invariants; no network or playlist writes."""
import hashlib
import json
import unittest
from unittest.mock import patch
from v2 import unlock_and_move_685 as mod


class MigrationTests(unittest.TestCase):
    def test_exact_move_and_preservation(self):
        def block(n, group):
            return f'#EXTINF:-1 group-title="{group}",Channel {n}\nhttps://example.com/{n}\n'
        originals = [block(i, "🗂️ YEDEKLER") for i in range(685)]
        other = block(700, "OTHER")
        archive = block(701, "ANA ARŞİV")
        raw = ("#EXTM3U\n" + other + "".join(originals) + archive).encode()
        manifest = json.dumps({"retry_queue": [
            {"channel_sha256": hashlib.sha256(b.encode()).hexdigest(),
             "url_sha256": hashlib.sha256(b.splitlines()[-1].encode()).hexdigest(),
             "status": "uncertain"} for b in originals
        ]}).encode()
        with patch.object(mod, "EXPECTED_MANIFEST_SHA256", hashlib.sha256(manifest).hexdigest()):
            result, report = mod.move(raw, manifest)
        self.assertEqual(report["moved"], 685)
        self.assertEqual(report["from_groups"], {"🗂️ YEDEKLER": 685})
        self.assertEqual(result.count(b"#EXTINF"), 687)
        self.assertTrue(result.startswith(("#EXTM3U\n" + other).encode()))
        self.assertIn((originals[0].replace("🗂️ YEDEKLER", "ANA ARŞİV") + archive).encode(), result)
        self.assertNotIn('group-title="🗂️ YEDEKLER"'.encode(), result)

    def test_missing_identity_fails_closed(self):
        raw = b'#EXTM3U\n#EXTINF:-1 group-title="YEDEKLER",X\nhttps://example.com/x\n'
        manifest = json.dumps({"retry_queue": [{"channel_sha256": "a"*64,
            "url_sha256": "b"*64, "status": "uncertain"} for _ in range(685)]}).encode()
        with patch.object(mod, "EXPECTED_MANIFEST_SHA256", hashlib.sha256(manifest).hexdigest()):
            with self.assertRaises(ValueError):
                mod.move(raw, manifest)


if __name__ == "__main__":
    unittest.main()

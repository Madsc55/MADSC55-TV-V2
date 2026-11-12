"""Offline recovery-inventory URL identity contract tests."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from consolidate_inventory import merge_records


class RecoveryIdentityTests(unittest.TestCase):
    def test_matching_digest_and_sources_survive_merge(self):
        url = "https://example.invalid/live.m3u8?token=private"
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index in (1, 2):
                path = Path(tmp) / f"{index}.jsonl"
                path.write_text(json.dumps({"url": url, "url_sha256": digest,
                                            "source_id": f"source-{index}"}) + "\n")
                paths.append(path)
            records, _ = merge_records(paths)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[url]["source_ids"], ["source-1", "source-2"])
            self.assertEqual(records[url]["url_sha256"], digest)

    def test_mismatched_digest_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.jsonl"
            path.write_text(json.dumps({"url": "https://example.invalid/live.m3u8",
                                        "url_sha256": "0" * 64}) + "\n")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                merge_records([path])


if __name__ == "__main__":
    unittest.main(verbosity=2)

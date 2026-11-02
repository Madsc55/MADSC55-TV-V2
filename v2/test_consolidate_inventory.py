#!/usr/bin/env python3
"""Offline regression tests; no channel search or protected playlist changes."""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        first = base / "first.jsonl"
        second = base / "second.jsonl"
        first.write_text(json.dumps({"url": "https://example.org/a.m3u8",
            "name": "Test channel", "source_ids": ["source-A"],
            "http_hls_status": "AV_VERIFIED"}) + "\n", encoding="utf-8")
        second.write_text(json.dumps({"url": "https://example.org/a.m3u8",
            "source_ids": ["source-B"], "http_hls_status": "FAILED"}) + "\n" +
            json.dumps({"url": "https://example.org/b.m3u8",
            "name": "Another test", "source_ids": ["source-B"]}) + "\n", encoding="utf-8")
        env = dict(os.environ, V2_ARCHIVE_PASSPHRASE="offline-test-passphrase-not-for-production")
        output = base / "inventory.enc"
        report = base / "report.json"
        subprocess.run([sys.executable, str(ROOT / "consolidate_inventory.py"),
                        "--input", str(first), "--input", str(second),
                        "--encrypted-output", str(output), "--report", str(report)],
                       env=env, check=True, capture_output=True, text=True)
        info = json.loads(report.read_text(encoding="utf-8"))
        assert info["unique_urls"] == 2
        assert info["observations_preserved"] == 3
        assert info["restore_test_passed"]
        sys.path.insert(0, str(ROOT))
        from secure_archive import decrypt
        restored = [json.loads(line) for line in decrypt(output.read_bytes(),
                    env["V2_ARCHIVE_PASSPHRASE"]).decode().splitlines()]
        assert restored[0]["source_ids"] == ["source-A", "source-B"]
        assert len(restored[0]["observations"]) == 2
        assert restored[0]["name"] == "Test channel"
        assert len(restored) == 2
        print("PASS: offline encrypted inventory merge, source retention, restore")

if __name__ == "__main__":
    main()

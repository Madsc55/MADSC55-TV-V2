#!/usr/bin/env python3
"""Offline regression checks: read-only playlist parser and master contract."""
import hashlib
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "v2"))
from discover import entries, discover

def main():
    fixture = '#EXTM3U\n#EXTINF:-1 tvg-id="test.tr" group-title="HABER" tvg-logo="https://example.org/a.png",TEST TV\nhttps://example.org/live.m3u8\n#EXTINF:-1 tvg-id="radio.tr" group-title="RADYO",RADYO\nhttps://example.org/radio\n'
    parsed = list(entries(fixture))
    assert len(parsed) == 2, parsed
    assert parsed[0]["tvg_id"] == "test.tr", parsed
    assert parsed[0]["group"] == "HABER", parsed
    assert parsed[0]["logo"] == "https://example.org/a.png", parsed
    assert not discover([("test", fixture)], fixture, {"test": "TR"}), "Existing streams must not become candidates"
    playlist = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
    assert playlist.exists(), "Protected playlist missing"
    before = hashlib.sha256(playlist.read_bytes()).hexdigest()
    result = subprocess.run([sys.executable, str(ROOT / "master.py"), "--help"], capture_output=True, text=True)
    assert result.returncode == 0 and "--run" in result.stdout, result.stderr
    assert hashlib.sha256(playlist.read_bytes()).hexdigest() == before, "Playlist unexpectedly changed"
    print("PASS: parser, deduplication, master CLI, playlist SHA-256 unchanged")

if __name__ == "__main__":
    main()

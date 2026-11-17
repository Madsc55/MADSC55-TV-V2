#!/usr/bin/env python3
"""Build a standalone backup playlist from all tracked M3U/M3U8 files except main."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
OUTPUT = "YEDEKLER_PLAYLISTESI.m3u8"
EXPECTED_SOURCES = 7

def main():
    tracked = subprocess.check_output(["git", "-C", str(ROOT), "ls-files", "-z"]).decode().split("\0")
    sources = sorted(p for p in tracked if p.lower().endswith((".m3u", ".m3u8")) and p not in (MAIN, OUTPUT))
    if len(sources) != EXPECTED_SOURCES:
        raise SystemExit(f"FAIL CLOSED: expected {EXPECTED_SOURCES} source playlists, found {len(sources)}: {sources}")
    blocks = []
    counts = {}
    for name in sources:
        raw = (ROOT / name).read_text(encoding="utf-8-sig")
        lines = raw.splitlines()
        if not lines or lines[0].strip() != "#EXTM3U":
            raise SystemExit(f"Invalid M3U header: {name}")
        entries = sum(line.startswith("#EXTINF:") for line in lines)
        if not entries:
            raise SystemExit(f"No entries: {name}")
        counts[name] = entries
        blocks.append("\n".join(lines[1:]).strip())
    output = "#EXTM3U\n" + "\n".join(blocks) + "\n"
    target = ROOT / OUTPUT
    target.write_text(output, encoding="utf-8")
    if output.count("#EXTINF:") != sum(counts.values()):
        raise SystemExit("Entry count mismatch")
    print(f"Created {OUTPUT}: {sum(counts.values())} records from {len(sources)} playlists")
    for name, count in counts.items():
        print(f"{name}: {count}")

if __name__ == "__main__":
    main()

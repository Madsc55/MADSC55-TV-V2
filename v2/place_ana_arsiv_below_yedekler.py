#!/usr/bin/env python3
"""Move the existing ANA ARŞİV category immediately after YEDEKLER in the ONE canonical playlist.

No URL, metadata, channel count, or relative order within any category is changed.
"""
from collections import Counter
from pathlib import Path
import re
import sys

PLAYLIST = Path(__file__).resolve().parents[1] / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
GROUP = re.compile(rb'group-title="([^"]*)"')

def category(block):
    match = GROUP.search(block.splitlines()[0])
    if not match:
        raise ValueError("Missing group-title in EXTINF block")
    label = match.group(1).decode("utf-8")
    if "YEDEKLER" in label.upper():
        return "YEDEKLER"
    if "ANA ARŞİV" in label.upper():
        return "ANA ARŞİV"
    return label

def main():
    original = PLAYLIST.read_bytes()
    # Preserve all original bytes, including line endings, headers and ancillary lines.
    matches = list(re.finditer(rb"(?m)^#EXTINF:", original))
    if not matches:
        raise ValueError("No EXTINF entries")
    prefix = original[:matches[0].start()]
    blocks = [original[m.start():matches[i+1].start() if i+1 < len(matches) else len(original)]
              for i, m in enumerate(matches)]
    groups = [category(b) for b in blocks]
    before = Counter(groups)
    if before["YEDEKLER"] != 1107 or before["ANA ARŞİV"] != 15703:
        raise ValueError(f"Unexpected inventory: YEDEKLER={before['YEDEKLER']}, ANA ARŞİV={before['ANA ARŞİV']}")
    archive = [b for b, g in zip(blocks, groups) if g == "ANA ARŞİV"]
    rest = [(b, g) for b, g in zip(blocks, groups) if g != "ANA ARŞİV"]
    last_yedekler = max(i for i, (_, g) in enumerate(rest) if g == "YEDEKLER")
    arranged = [b for b, _ in rest[:last_yedekler+1]] + archive + [b for b, _ in rest[last_yedekler+1:]]
    after = [category(b) for b in arranged]
    assert Counter(after) == before
    assert Counter(arranged) == Counter(blocks), "Channel block identity changed"
    assert after[last_yedekler+1:last_yedekler+1+len(archive)] == ["ANA ARŞİV"] * len(archive)
    output = prefix + b"".join(arranged)
    if output == original:
        print("Already ordered; no changes")
        return
    PLAYLIST.write_bytes(output)
    print(f"Reordered: YEDEKLER {before['YEDEKLER']} -> ANA ARŞİV {before['ANA ARŞİV']}; {len(blocks)} blocks preserved")

if __name__ == "__main__":
    main()

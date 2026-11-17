#!/usr/bin/env python3
"""Offline M3U inventory -> read-only Turkish channel review.

No stream URLs in output, no network, no mutation of the source playlist.
Each EXTINF record receives a stable 1-based ordinal, including non-Turkish
channels. Source title/group are *hints*, never verified country/language.
"""
import argparse
import json
import re
from pathlib import Path
try:
    from .turkish_channel_triage import classify_channel
except ImportError:
    from turkish_channel_triage import classify_channel

MAX_CHANNELS = 25000
MAX_BYTES = 32 * 1024 * 1024
GROUP_RE = re.compile(r'group-title="([^"]{0,256})"')

def inventory_review(playlist, output):
    playlist, output = Path(playlist), Path(output)
    if playlist.resolve() == output.resolve():
        raise ValueError("Output cannot replace input")
    if output.exists():
        raise FileExistsError("Review output already exists")
    if playlist.stat().st_size > MAX_BYTES:
        raise ValueError("Playlist too large")
    rows = []
    pending = None
    with playlist.open(encoding="utf-8-sig", errors="replace") as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("#EXTINF:"):
                if pending is not None:
                    raise ValueError("Unpaired EXTINF entry")
                if "," not in line:
                    raise ValueError("Missing channel title")
                title = line.rsplit(",", 1)[1].strip()
                group_match = GROUP_RE.search(line)
                pending = (title, group_match.group(1) if group_match else "")
            elif line and not line.startswith("#") and pending is not None:
                title, group = pending
                pending = None
                if len(rows) >= MAX_CHANNELS:
                    raise ValueError("Channel limit exceeded")
                triage = classify_channel(title)
                rows.append({"playlist_ordinal": len(rows) + 1,
                             "source_group": group,
                             "title": title,
                             **triage})
    if pending is not None:
        raise ValueError("Unpaired final EXTINF entry")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"channels": len(rows), "approved": 0, "playlist_modified": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inventory_review(args.playlist, args.output)))

if __name__ == "__main__":
    main()

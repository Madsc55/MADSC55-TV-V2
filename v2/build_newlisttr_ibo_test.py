#!/usr/bin/env python3
"""Create separate IBO test playlist: existing V2 entries + decoded NewlistTR in YEDEKLER."""
import re
from pathlib import Path
from discover import ROOT, LIVE, entries

SOURCE = ROOT / "v2/reports/newlisttr-decoded-only.m3u8"
DEST = ROOT / "MADSC55_IBO_NEWLISTTR_YEDEKLER_TEST.m3u8"

def main():
    original = LIVE.read_text(encoding="utf-8-sig").rstrip() + "\n"
    decoded = list(entries(SOURCE.read_text(encoding="utf-8-sig")))
    existing_urls = {item["url"] for item in entries(original)}
    added = [item for item in decoded if item["url"] not in existing_urls]
    original_backups = sum("YEDEKLER" in item["group"] for item in entries(original))
    backup_group = f"🗂️ YEDEKLER ({original_backups + len(added)})"
    # Only change category count in the *separate* test playlist.
    original = re.sub(r'group-title="([^"]*YEDEKLER) \(\d+\)"',
                      lambda m: 'group-title="' + backup_group + '"', original)
    lines = [original.rstrip()]
    for item in added:
        def clean(s):
            return str(s or "").replace('"', "'").replace("\n", " ").replace("\r", " ")
        lines.append(f'#EXTINF:-1 tvg-id="{clean(item["tvg_id"])}" tvg-logo="{clean(item["logo"])}" group-title="{backup_group}",{clean(item["name"])}')
        lines.append(item["url"])
    DEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"IBO separate test playlist: original={len(list(entries(original)))} added={len(added)} backups={original_backups + len(added)}")
    assert original_backups == 2, "Original backup invariant failed"
    assert len(list(entries(DEST.read_text(encoding="utf-8")))) == len(list(entries(original))) + len(added)

if __name__ == "__main__":
    main()

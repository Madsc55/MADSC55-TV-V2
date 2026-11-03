#!/usr/bin/env python3
"""One-shot guarded promotion of Turkish trial channels into V2 YEDEKLER."""
from pathlib import Path
from discover import ROOT, LIVE, entries
import re

TRIAL = ROOT / "v2/reports/YEDEKLER_TEST.m3u8"
ALLOWED = ("TRT WORLD", "TRT ARABI", "HABER61 TV", "YOL TV", "ARAS TV", "TV DEN")
def main():
    original = LIVE.read_text(encoding="utf-8-sig")
    existing = list(entries(original))
    backups = [e for e in existing if "YEDEKLER" in e["group"]]
    if len(backups) != 2 or not any("TRT 1" in e["name"] for e in backups) or not any("DHA CANLI" in e["name"] for e in backups):
        raise SystemExit("SAFETY STOP: expected two original YEDEKLER entries missing")
    trial = list(entries(TRIAL.read_text(encoding="utf-8-sig")))
    existing_urls = {e["url"] for e in existing}
    selected = []
    for e in trial:
        name = e["name"].upper()
        if not any(name.startswith(prefix) for prefix in ALLOWED) or e["url"] in existing_urls:
            continue
        if any(c in e["url"] for c in "\r\n") or not e["url"].startswith(("http://", "https://")):
            continue
        selected.append(e)
        existing_urls.add(e["url"])
    if not selected:
        raise SystemExit("SAFETY STOP: no eligible verified Turkish streams; no playlist changes")
    updated = original.replace('group-title="📦 YEDEKLER (2)"', f'group-title="📦 YEDEKLER ({2+len(selected)})"')
    lines = []
    for e in selected:
        clean = lambda s: re.sub(r'[\r\n"]', " ", s or "")
        lines.append(f'#EXTINF:-1 tvg-id="{clean(e["tvg_id"])}" tvg-logo="{clean(e["logo"])}" group-title="📦 YEDEKLER ({2+len(selected)})",{clean(e["name"])}')
        lines.append(e["url"])
    updated = updated.rstrip("\n") + "\n" + "\n".join(lines) + "\n"
    check = list(entries(updated))
    if len(check) != len(existing) + len(selected) or check[:len(existing)] != [dict(e, group=(f"📦 YEDEKLER ({2+len(selected)})" if "YEDEKLER" in e["group"] else e["group"])) for e in existing]:
        raise SystemExit("SAFETY STOP: existing playlist changed unexpectedly")
    LIVE.write_text(updated, encoding="utf-8")
    print("Added to YEDEKLER:", [e["name"] for e in selected], "preserved original:", len(existing))
if __name__ == "__main__":
    main()

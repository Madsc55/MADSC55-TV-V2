#!/usr/bin/env python3
"""Import one deduplicated scan batch into YEDEKLER without changing protected channels.

Usage: python v2/import_scan_backup_batch.py --source /tmp/IBO_YENI_ADAYLAR_PART1.m3u8 --count 1000
Run in a checked-out repository, then review and submit the changed files via PR.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
ARCHIVE = ROOT / "v2/arsiv/yabanci_kanallar_2026-11-16_2881.m3u8"
TEST = ROOT / "v2/test_playlist_invariants.py"
MANIFEST = ROOT / "v2/ibo_authorized_change.json"
GROUP_RE = re.compile(r'group-title="[^"]*"')


def records(text):
    lines = text.splitlines(keepends=True)
    header = []
    blocks = []
    for line in lines:
        if line.startswith("#EXTINF:"):
            blocks.append([line])
        elif blocks:
            blocks[-1].append(line)
        else:
            header.append(line)
    return "".join(header), ["".join(b) for b in blocks]


def url(block):
    return next((line.strip() for line in block.splitlines()[1:]
                 if line.strip().startswith(("http://", "https://"))), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--count", type=int, default=1000)
    args = ap.parse_args()
    if not 1 <= args.count <= 2000:
        ap.error("count must be between 1 and 2000")
    original = LIVE.read_bytes()
    text = original.decode("utf-8-sig")
    header, current = records(text)
    main = [b for b in current if "YEDEKLER" not in b.splitlines()[0]]
    backups = [b for b in current if "YEDEKLER" in b.splitlines()[0]]
    if len(main) != 838 or len(main) + len(backups) != len(current):
        raise SystemExit("Protected main-channel invariant failed")
    if current != main + backups:
        raise SystemExit("Backups are not contiguous at playlist end")
    if len(backups) != 285:
        raise SystemExit("Expected 285 existing backups; rebase before importing")
    seen = {u for b in current if (u := url(b))}
    _, archived = records(ARCHIVE.read_text(encoding="utf-8-sig"))
    seen.update(u for b in archived if (u := url(b)))
    _, candidates = records(args.source.read_text(encoding="utf-8-sig"))
    selected = []
    for b in candidates:
        u = url(b)
        if not u or u in seen:
            continue
        meta = b.splitlines()[0]
        if not GROUP_RE.search(meta):
            raise SystemExit("Candidate missing group-title")
        seen.add(u)
        selected.append(b)
        if len(selected) == args.count:
            break
    if len(selected) != args.count:
        raise SystemExit(f"Only {len(selected)} fresh candidates available; no partial write")
    new_count = len(backups) + len(selected)
    group = f'group-title="🗂️ YEDEKLER ({new_count})"'
    def relabel(block):
        lines = block.splitlines(keepends=True)
        lines[0] = GROUP_RE.sub(lambda _: group, lines[0], count=1)
        return "".join(lines)
    result = header + "".join(main) + "".join(map(relabel, backups + selected))
    _, after = records(result)
    if after[:838] != main or len(after) != 838 + new_count:
        raise SystemExit("Protected channels or count changed")
    if [url(b) for b in after[838:838+285]] != [url(b) for b in backups]:
        raise SystemExit("Existing backups changed order")
    if len({url(b) for b in after[838:]}) != new_count:
        raise SystemExit("Duplicate backup URLs")
    tests = TEST.read_text(encoding="utf-8")
    if tests.count("1123") != 1 or tests.count("285") < 3:
        raise SystemExit("Unexpected invariant-test layout")
    tests = tests.replace("1123", str(838 + new_count))
    tests = tests.replace("285", str(new_count))
    manifest = {
        "base_sha256": hashlib.sha256(original).hexdigest(),
        "result_sha256": hashlib.sha256(result.encode("utf-8")).hexdigest(),
        "operation": "category",
        "request": f"User-authorized: add {len(selected)} unique scan candidates to YEDEKLER for IBO Player review; retain 838 protected channels and 285 existing backups in order.",
        "channels": [f"Scan review candidates: {len(selected)} new unique stream URLs; playback not assumed verified"],
    }
    LIVE.write_bytes(result.encode("utf-8"))
    TEST.write_text(tests, encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(selected)} candidates; {new_count} backups; protected 838 unchanged")


if __name__ == "__main__":
    main()

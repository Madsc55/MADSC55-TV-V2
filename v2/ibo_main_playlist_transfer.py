#!/usr/bin/env python3
"""Offline, reversible in-place category moves for the ONE canonical IBO playlist.

Never scans streams. Dry-run by default. Only group-title fields are rewritten.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

MAIN = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
GROUP = re.compile(r'(group-title\s*=\s*")([^"]*)(")', re.I)
CATEGORIES = {"YEDEKLER", "ANA ARŞİV", "TURK ARŞİVİ", "YABANCI ARŞİV"}
ALIAS = {"TURK": "TURK ARŞİVİ", "YABANCI": "YABANCI ARŞİV",
         "ANA": "ANA ARŞİV", "YEDEKLER": "YEDEKLER"}
def sha(data):
    return hashlib.sha256(data).hexdigest()

def parse(data):
    text = data.decode("utf-8-sig")
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("Invalid M3U header")
    chunks, block, prelude = [], None, []
    for line in lines[1:]:
        if line.startswith("#EXTINF:"):
            if block is not None:
                raise ValueError("Unfinished EXTINF record")
            block = [line]
        elif block is None:
            prelude.append(line)
        else:
            block.append(line)
            if line.strip() and not line.startswith("#"):
                match = GROUP.search(block[0])
                if not match:
                    raise ValueError("Missing group-title")
                chunks.append({"lines": block, "group": match.group(2),
                               "url": line.strip()})
                block = None
    if block is not None:
        raise ValueError("Incomplete final record")
    return lines[0], prelude, chunks

def render(header, prelude, chunks):
    return (header + "".join(prelude) +
            "".join("".join(x["lines"]) for x in chunks)).encode("utf-8")

def counts(chunks):
    out = {}
    for x in chunks:
        out[x["group"]] = out.get(x["group"], 0) + 1
    return out

def move(data, source, target, start, end):
    header, prelude, chunks = parse(data)
    if source == target or source not in CATEGORIES or target not in CATEGORIES:
        raise ValueError("Invalid source/target")
    selected = [x for x in chunks if x["group"] == source]
    if not 1 <= start <= end <= len(selected) or end-start+1 > 2500:
        raise ValueError("Invalid 1-based inclusive range or batch >2500")
    original = counts(chunks)
    chosen = selected[start-1:end]
    urls = [x["url"] for x in chosen]
    if len(urls) != len(set(urls)):
        raise ValueError("Duplicate URL in selected batch")
    # Reassign only selected records; no deletion, insertion or sorting.
    for x in chosen:
        x["lines"][0] = GROUP.sub(lambda m: m.group(1)+target+m.group(3),
                                   x["lines"][0], count=1)
        x["group"] = target
    updated = render(header, prelude, chunks)
    _, _, verify = parse(updated)
    after = counts(verify)
    if len(verify) != len(chunks) or sum(after.values()) != sum(original.values()):
        raise ValueError("Inventory parity failure")
    for category in set(original) | set(after):
        expected = original.get(category, 0) + (
            len(chosen) if category == target else -len(chosen) if category == source else 0)
        if after.get(category, 0) != expected:
            raise ValueError("Unexpected category change")
    return updated, {"from": source, "to": target, "moved": len(chosen),
                     "before": original, "after": after,
                     "url_fingerprints": [sha(u.encode()) for u in urls]}

def private_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

def replace_checked(path, data, expected_sha):
    if path.is_symlink() or sha(path.read_bytes()) != expected_sha:
        raise ValueError("Playlist changed or is symlink: refusing write")
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".ibo-transaction-")
    try:
        os.fchmod(fd, path.stat().st_mode & 0o777)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if sha(path.read_bytes()) != expected_sha:
            raise ValueError("Concurrent playlist update")
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

def run(path, journal, source=None, target=None, start=None, end=None,
        expected_sha=None, apply=False, undo=False):
    path, journal = Path(path), Path(journal)
    if path.name != MAIN or path.is_symlink() or journal.resolve() == path.resolve():
        raise ValueError("Only canonical main playlist is supported")
    raw = path.read_bytes()
    if expected_sha is None or sha(raw) != expected_sha:
        raise ValueError("Explicit current playlist SHA-256 required")
    if undo:
        meta = json.loads(journal.read_text(encoding="utf-8"))
        if meta["after_sha256"] != sha(raw):
            raise ValueError("Cannot undo: playlist changed")
        backup = journal.with_suffix(".backup")
        previous = backup.read_bytes()
        if sha(previous) != meta["before_sha256"]:
            raise ValueError("Corrupt undo backup")
        result = {"undo": True, "before_sha256": sha(raw),
                  "after_sha256": sha(previous)}
        if apply:
            replace_checked(path, previous, sha(raw))
        return result
    if journal.exists() or journal.with_suffix(".backup").exists():
        raise ValueError("Transaction journal already exists: no replay")
    updated, result = move(raw, source, target, start, end)
    result.update({"before_sha256": sha(raw), "after_sha256": sha(updated),
                   "applied": apply})
    if apply:
        private_new(journal.with_suffix(".backup"), raw)
        private_new(journal, (json.dumps(result, ensure_ascii=False, indent=2)+"\n").encode())
        replace_checked(path, updated, sha(raw))
    return result

def main():
    p = argparse.ArgumentParser(description="Offline in-place playlist category transfers")
    p.add_argument("--playlist", type=Path, default=Path(MAIN))
    p.add_argument("--journal", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--source", choices=sorted(CATEGORIES))
    p.add_argument("--target", choices=sorted(CATEGORIES))
    p.add_argument("--start", type=int)
    p.add_argument("--end", type=int)
    p.add_argument("--undo", action="store_true")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args()
    if not a.undo and None in (a.source, a.target, a.start, a.end):
        p.error("Source, target and inclusive start/end required")
    print(json.dumps(run(a.playlist, a.journal, a.source, a.target,
                         a.start, a.end, a.expected_sha256, a.apply, a.undo),
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

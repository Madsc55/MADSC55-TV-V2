#!/usr/bin/env python3
"""Fail-closed, single-playlist YEDEKLER/archive category moves. No network access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

GROUP = re.compile(r'(group-title\s*=\s*")([^"]*)(")', re.I)
ARCHIVE_NAMES = {"YEDEKLER": "🗂️ YEDEKLER", "ANA": "ANA ARŞİV",
                 "TURK": "TÜRK ARŞİVİ", "YABANCI": "YABANCI ARŞİVİ"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def category(extinf):
    match = GROUP.search(extinf)
    if not match:
        return None
    value = match.group(2).upper()
    if "YEDEKLER" in value:
        return "YEDEKLER"
    if "ANA ARŞİV" in value or "ANA ARSIV" in value:
        return "ANA"
    if "TÜRK ARŞİV" in value or "TURK ARSIV" in value:
        return "TURK"
    if "YABANCI ARŞİV" in value or "YABANCI ARSIV" in value:
        return "YABANCI"
    return None


def parse(raw):
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("#EXTM3U"):
        raise ValueError("Invalid M3U header")
    prefix, blocks, current = [], [], None
    for line in lines:
        if line.startswith("#EXTINF:"):
            if current is not None:
                raise ValueError("Incomplete EXTINF block")
            current = [line]
        elif current is None:
            prefix.append(line)
        else:
            current.append(line)
            if line.strip() and not line.startswith("#"):
                blocks.append("".join(current))
                current = None
    if current is not None:
        raise ValueError("Incomplete final EXTINF block")
    if not blocks:
        raise ValueError("Empty playlist")
    return "".join(prefix), blocks


def rewrite_group(block, target):
    head, sep, tail = block.partition("\n")
    match = GROUP.search(head)
    if not match:
        raise ValueError("Missing group-title")
    old = match.group(2)
    # Visible count suffixes are normalized by transform().
    replacement = ARCHIVE_NAMES[target]
    return head[:match.start(2)] + replacement + head[match.end(2):] + sep + tail


def transform(raw, source, target, ordinals, expected_sha, expected_urls=None):
    if sha(raw) != expected_sha:
        raise ValueError("Source SHA mismatch")
    if source not in ARCHIVE_NAMES or target not in ARCHIVE_NAMES or source == target:
        raise ValueError("Invalid category transition")
    prefix, blocks = parse(raw)
    indices = [i for i, b in enumerate(blocks) if category(b.split("\n", 1)[0]) == source]
    if len(ordinals) > 2500:
        raise ValueError("Selection exceeds 2500 entries")
    if not indices or not ordinals or len(ordinals) != len(set(ordinals)):
        raise ValueError("Empty/duplicate selection")
    if min(ordinals) < 1 or max(ordinals) > len(indices):
        raise ValueError("Ordinal outside source category")
    chosen = {indices[n - 1] for n in ordinals}
    selected_urls = [blocks[indices[n - 1]].strip().splitlines()[-1].strip() for n in ordinals]
    if expected_urls is not None and selected_urls != expected_urls:
        raise ValueError("Selected URL manifest mismatch; refusing stale ordinal selection")
    # Fail closed on duplicate stream URLs: ordinal-only moves would be ambiguous.
    urls = [b.strip().splitlines()[-1].strip() for b in blocks]
    if len(urls) != len(set(urls)):
        raise ValueError("Duplicate stream URL in playlist")
    updated = [rewrite_group(b, target) if i in chosen else b for i, b in enumerate(blocks)]
    # Recompute visible counts in both affected groups; preserve other categories.
    counts = {key: sum(category(b.split("\n", 1)[0]) == key for b in updated)
              for key in (source, target)}
    for i, block in enumerate(updated):
        key = category(block.split("\n", 1)[0])
        if key not in counts:
            continue
        head, sep, tail = block.partition("\n")
        match = GROUP.search(head)
        if not match:
            raise ValueError("Missing group-title")
        label = match.group(2)
        if re.search(r"\(\d+\)", label):
            label = re.sub(r"\(\d+\)", f"({counts[key]})", label)
        else:
            label = ARCHIVE_NAMES[key] + f" ({counts[key]})"
        updated[i] = head[:match.start(2)] + label + head[match.end(2):] + sep + tail
    for i, (before, after) in enumerate(zip(blocks, updated)):
        if i not in chosen and category(before.split("\n", 1)[0]) not in counts and before != after:
            raise ValueError("Unrelated category changed")
    result = (prefix + "".join(updated)).encode("utf-8")
    _, verified = parse(result)
    if len(verified) != len(blocks):
        raise ValueError("Record count changed")
    for key in (source, target):
        actual = sum(category(b.split("\n", 1)[0]) == key for b in verified)
        if actual != counts[key]:
            raise ValueError("Category parity failed")
    return result, {"source": source, "target": target, "moved": len(chosen),
                    "selected_urls_sha256": sha(json.dumps(selected_urls, ensure_ascii=False).encode("utf-8")),
                    "total": len(blocks), "before_sha256": expected_sha,
                    "after_sha256": sha(result)}


def publish(path, raw, result, backup):
    if backup.exists() or backup.is_symlink():
        raise ValueError("Backup already exists")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Refusing symlink/non-file playlist")
    if sha(path.read_bytes()) != sha(raw):
        raise ValueError("Concurrent playlist modification")
    if backup.parent.resolve() != path.parent.resolve():
        raise ValueError("Backup must share playlist directory")
    os.link(path, backup)  # no overwrite; preserves exact original bytes
    fd, tmp = tempfile.mkstemp(prefix=".ibo-archive-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(result)
            out.flush()
            os.fsync(out.fileno())
        if sha(path.read_bytes()) != sha(raw):
            raise ValueError("Concurrent playlist modification")
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--playlist", type=Path, required=True)
    p.add_argument("--source", choices=sorted(ARCHIVE_NAMES), required=True)
    p.add_argument("--target", choices=sorted(ARCHIVE_NAMES), required=True)
    p.add_argument("--start", type=int, required=True)
    p.add_argument("--end", type=int, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--expected-urls-json", type=Path,
                   help="JSON array of exact selected URLs in ordinal order; required for apply")
    p.add_argument("--backup", type=Path)
    a = p.parse_args()
    if a.start < 1 or a.end < a.start or a.end - a.start + 1 > 2500:
        p.error("Selection must be 1..2500 consecutive source-category entries")
    raw = a.playlist.read_bytes()
    if a.apply and a.expected_urls_json is None:
        p.error("--expected-urls-json required for --apply to prevent stale ordinal moves")
    expected_urls = None
    if a.expected_urls_json is not None:
        expected_urls = json.loads(a.expected_urls_json.read_text(encoding="utf-8"))
        if not isinstance(expected_urls, list) or not all(isinstance(x, str) for x in expected_urls):
            p.error("--expected-urls-json must contain a JSON string array")
    output, report = transform(raw, a.source, a.target,
                               list(range(a.start, a.end + 1)), a.expected_sha256,
                               expected_urls=expected_urls)
    if a.apply:
        if a.backup is None:
            p.error("--backup required for --apply")
        publish(a.playlist, raw, output, a.backup)
    report["applied"] = a.apply
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Fail-closed scope detector for fast, lossless owner-requested channel moves.

A true result allows only media/unrelated regression STEPS to be skipped.
It does not replace the separate workflow security and canonical parts gates.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

from channel_command_engine import grouped, key
from playlist_parts_manager import ROOT, category, checksum, logical, split_records

PLAYLIST = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
PARTS = Path("v2/playlists/parts")
AUTHORIZATION = "v2/ibo_authorized_change.json"
FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")
PART_FILE = re.compile(r"v2/playlists/parts/[0-9]{4}\.m3u\Z")
GROUP_TITLE = re.compile(rb'group-title\s*=\s*"[^"]*"', re.I)
COUNT_TITLE = re.compile(r"\((\d+)\)\s*\Z")


def identity(record):
    """Keep URL, name, logos and every byte except the group-title value."""
    if not GROUP_TITLE.search(record.split(b"\n", 1)[0]):
        raise ValueError("Missing group-title")
    return GROUP_TITLE.sub(b'group-title="<PRESERVED>"', record, count=1)


def subsequence(shorter, longer):
    it = iter(longer)
    return all(any(v == wanted for v in it) for wanted in shorter)


def safe_move_bytes(original, candidate, spec, parts_dir=PARTS):
    """Require exactly one move: source loses N and target gains the SAME N records."""
    if not isinstance(spec, dict) or set(spec) != {
        "base_sha256", "result_sha256", "operation", "request", "channels"
    }:
        return False
    if spec["operation"] != "move" or not isinstance(spec["request"], str) or len(spec["request"].strip()) < 12:
        return False
    selected = spec["channels"]
    if not isinstance(selected, list) or not 1 <= len(selected) <= 2500 or not all(
        isinstance(v, str) and v.strip() for v in selected
    ):
        return False
    if spec["base_sha256"] != checksum(original) or spec["result_sha256"] != checksum(candidate):
        return False
    h0, r0 = split_records(original)
    h1, r1 = split_records(candidate)
    if h0 != h1 or not r0 or len(r0) != len(r1):
        return False
    if Counter(map(identity, r0)) != Counter(map(identity, r1)):
        return False

    _, g0, labels0 = grouped(original)
    _, g1, labels1 = grouped(candidate)
    if list(g0) != list(g1) or labels0 != labels1:
        return False
    diffs = {group: len(g1[group]) - len(g0[group]) for group in g0}
    changed = {group: delta for group, delta in diffs.items() if delta}
    if len(changed) != 2 or sorted(changed.values()) != [-len(selected), len(selected)]:
        return False
    src = next(group for group, delta in changed.items() if delta < 0)
    dst = next(group for group, delta in changed.items() if delta > 0)
    old_src = [identity(x) for x in g0[src]]
    new_src = [identity(x) for x in g1[src]]
    old_dst = [identity(x) for x in g0[dst]]
    new_dst = [identity(x) for x in g1[dst]]
    moved = Counter(old_src) - Counter(new_src)
    arrived = Counter(new_dst) - Counter(old_dst)
    if moved != arrived or sum(moved.values()) != len(selected):
        return False
    if not subsequence(new_src, old_src) or not subsequence(old_dst, new_dst):
        return False
    for group in g0:
        if group not in (src, dst) and [identity(x) for x in g0[group]] != [
            identity(x) for x in g1[group]
        ]:
            return False
    # All displayed category count suffixes must match the actual contents.
    for group, records in g1.items():
        for rec in records:
            label = category(rec)
            match = COUNT_TITLE.search(label)
            if not match or int(match.group(1)) != len(records) or key(label) != group:
                return False

    manifest = json.loads((parts_dir / "manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("version") != 1 or manifest.get("source_sha256") != checksum(original)
            or manifest.get("total_records") != len(r1)
            or manifest.get("header_hex") != h1.hex()):
        return False
    parts, names = [], []
    for entry in manifest["entries"]:
        name = entry["file"]
        if not re.fullmatch(r"[0-9]{4}\.m3u", name) or name in names:
            return False
        payload = (parts_dir / name).read_bytes()
        if checksum(payload) != entry["sha256"]:
            return False
        _, rows = split_records(payload)
        if len(rows) != entry["records"] or any(
            logical(category(row)) != entry["group"] for row in rows
        ):
            return False
        names.append(name)
        parts.append(payload)
    return (bool(parts) and {f.name for f in parts_dir.glob("*.m3u")} == set(names)
            and h1 + b"".join(parts) == candidate)


def eligible_pr(base, repo, head_repo, author, head_ref, root=ROOT):
    if not (FULL_SHA.fullmatch(base or "") and repo == head_repo and author == "Madsc55"
            and head_ref.startswith("command/ibo-")):
        return False
    raw = subprocess.check_output(
        ["git", "diff", "--name-only", "-z", "--no-renames", base, "HEAD"], cwd=root
    )
    paths = {name.decode("utf-8") for name in raw.split(b"\0") if name}
    required = {PLAYLIST, AUTHORIZATION, "v2/playlists/parts/manifest.json"}
    if not required <= paths or any(
        name not in required and not PART_FILE.fullmatch(name) for name in paths
    ):
        return False
    original = subprocess.check_output(["git", "show", base + ":" + PLAYLIST], cwd=root)
    candidate = (root / PLAYLIST).read_bytes()
    spec = json.loads((root / AUTHORIZATION).read_text(encoding="utf-8"))
    return safe_move_bytes(original, candidate, spec, root / PARTS)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="")
    parser.add_argument("--repo", default="")
    parser.add_argument("--head-repo", default="")
    parser.add_argument("--author", default="")
    parser.add_argument("--head-ref", default="")
    args = parser.parse_args()
    try:
        eligible = eligible_pr(args.base, args.repo, args.head_repo, args.author, args.head_ref)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, subprocess.CalledProcessError):
        eligible = False
    # Never skip full tests if detection encounters unknown data or an error.
    print("eligible=" + ("true" if eligible else "false"))


if __name__ == "__main__":
    main()

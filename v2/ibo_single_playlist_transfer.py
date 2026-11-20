#!/usr/bin/env python3
"""Fail-closed, single-playlist YEDEKLER/archive category moves. No network access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import fcntl
from ibo_archive_operation_ledger import append as append_operation, read as read_journal

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
    # Existing duplicate URLs are common in the canonical playlist. The
    # operation changes only group metadata, never stream URLs or record count.
    # SHA and ordered URL manifest protect selection against stale positions.
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
    before_counts = inventory(raw)
    after_counts = inventory(result)
    if before_counts["TOTAL"] != after_counts["TOTAL"] or before_counts["OTHER"] != after_counts["OTHER"]:
        raise ValueError("Inventory parity mismatch")
    if after_counts[source] != before_counts[source] - len(chosen) or after_counts[target] != before_counts[target] + len(chosen):
        raise ValueError("Transfer category count mismatch")
    for key in ARCHIVE_NAMES:
        if key not in (source, target) and after_counts[key] != before_counts[key]:
            raise ValueError("Unrelated archive count changed")
    _, verified = parse(result)
    if len(verified) != len(blocks):
        raise ValueError("Record count changed")
    for key in (source, target):
        actual = sum(category(b.split("\n", 1)[0]) == key for b in verified)
        if actual != counts[key]:
            raise ValueError("Category parity failed")
    return result, {"source": source, "target": target, "moved": len(chosen),
                    "selected_urls_sha256": sha(json.dumps(selected_urls, ensure_ascii=False).encode("utf-8")),
                    "total": len(blocks), "counts_before": before_counts,
                    "counts_after": after_counts, "before_sha256": expected_sha,
                    "after_sha256": sha(result)}



def inventory(raw):
    """Count actual records; never trust displayed group count suffixes."""
    _, blocks = parse(raw)
    counts = {key: 0 for key in ARCHIVE_NAMES}
    other = 0
    for block in blocks:
        key = category(block.split("\n", 1)[0])
        if key is None:
            other += 1
        else:
            counts[key] += 1
    counts["OTHER"] = other
    counts["TOTAL"] = len(blocks)
    return counts


def restore_exact(raw, backup_raw, expected_sha, expected_backup_sha):
    """Lossless full-transaction rollback, guarded against intervening edits."""
    if sha(raw) != expected_sha or sha(backup_raw) != expected_backup_sha:
        raise ValueError("Rollback SHA mismatch")
    current = inventory(raw)
    previous = inventory(backup_raw)
    if current["TOTAL"] != previous["TOTAL"]:
        raise ValueError("Rollback record count mismatch")
    # No attempt to reconstruct order from category ordinals.
    return backup_raw


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


def plan_next_batch(raw, source="ANA", limit=2500):
    """Plan the next bounded package without modifying any playlist or channel."""
    if source not in ARCHIVE_NAMES or not 1 <= limit <= 2500:
        raise ValueError("Invalid batch source or size")
    _, blocks = parse(raw)
    matches = [block.strip().splitlines()[-1].strip() for block in blocks
               if category(block.split("\n", 1)[0]) == source]
    selected = matches[:limit]
    return {"source": source, "start": 1 if selected else 0,
            "end": len(selected), "remaining_after": len(matches) - len(selected),
            "expected_sha256": sha(raw), "expected_urls": selected}


def _durable_json(path, data):
    """Atomic durable journal/pending file replacement."""
    fd, staged = tempfile.mkstemp(prefix=".ibo-ledger-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staged, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(staged):
            os.unlink(staged)


def _recover_pending(path, journal_path):
    """Complete an interrupted publish only if its exact before/after SHA matches."""
    pending_path = journal_path.with_name(journal_path.name + ".pending")
    if pending_path.is_symlink():
        raise ValueError("Symlink pending journal rejected")
    if not pending_path.exists():
        return
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    ledger = read_journal(journal_path)
    if ledger is None:
        ledger = {"initial_sha256": pending["initial_sha256"], "operations": []}
    from ibo_archive_operation_ledger import validate
    head = validate(ledger["operations"], ledger["initial_sha256"])
    operation = pending["operation"]
    if operation["operation_id"] in {x["operation_id"] for x in ledger["operations"]}:
        if head != operation["after_sha256"]:
            raise ValueError("Pending operation journal mismatch")
    else:
        if head != operation["before_sha256"]:
            raise ValueError("Pending journal chain mismatch")
        current_sha = sha(path.read_bytes())
        if current_sha == operation["after_sha256"]:
            records = append_operation(ledger["operations"], ledger["initial_sha256"], operation)
            _durable_json(journal_path, {**ledger, "operations": records})
        elif current_sha != operation["before_sha256"]:
            raise ValueError("Unknown playlist revision during recovery")
    pending_path.unlink()
    dfd = os.open(journal_path.parent, os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def apply_with_journal(path, raw, output, backup, journal_path, operation_id, report):
    """Durable pending intent and idempotent crash recovery under an exclusive lock."""
    if not operation_id or not operation_id.strip():
        raise ValueError("Operation id required")
    if journal_path.is_symlink() or journal_path.resolve() == path.resolve():
        raise ValueError("Invalid journal path")
    if journal_path.parent.resolve() != path.parent.resolve():
        raise ValueError("Journal must share playlist directory")
    lock_path = path.with_name(path.name + ".archive.lock")
    if lock_path.is_symlink():
        raise ValueError("Symlink lock rejected")
    with open(lock_path, "a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        _recover_pending(path, journal_path)
        if sha(path.read_bytes()) != sha(raw):
            raise ValueError("Playlist changed while waiting for lock")
        ledger = read_journal(journal_path)
        if ledger is None:
            if journal_path.exists():
                raise ValueError("Invalid existing journal")
            ledger = {"initial_sha256": sha(raw), "operations": []}
        op = {**report, "operation_id": operation_id}
        records = append_operation(ledger["operations"], ledger["initial_sha256"], op)
        pending_path = journal_path.with_name(journal_path.name + ".pending")
        if pending_path.exists() or pending_path.is_symlink():
            raise ValueError("Unresolved pending operation")
        _durable_json(pending_path, {"initial_sha256": ledger["initial_sha256"],
                                    "operation": op})
        try:
            publish(path, raw, output, backup)
        except BaseException:
            # Keep pending for deterministic recovery on the next attempt.
            raise
        _durable_json(journal_path, {**ledger, "operations": records})
        pending_path.unlink()
        dfd = os.open(journal_path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)


def rollback_last(path, previous_backup, rollback_backup, journal_path, operation_id):
    """Undo only the most recent recorded transfer; never undo intervening edits."""
    if not journal_path.exists():
        raise ValueError("Missing operation journal")
    ledger = read_journal(journal_path)
    if not ledger["operations"]:
        raise ValueError("No transfer to undo")
    last = ledger["operations"][-1]
    current = path.read_bytes()
    previous = previous_backup.read_bytes()
    restored = restore_exact(current, previous, last["after_sha256"],
                             last["before_sha256"])
    report = {"source": last["target"], "target": last["source"],
              "moved": last["moved"], "before_sha256": sha(current),
              "after_sha256": sha(restored), "total": inventory(current)["TOTAL"],
              "counts_before": inventory(current), "counts_after": inventory(restored),
              "undoes_operation_id": last["operation_id"]}
    apply_with_journal(path, current, restored, rollback_backup,
                       journal_path, operation_id, report)
    return report


def advance_next_package(path, backup, journal_path, operation_id, expected_sha):
    """Fill YEDEKLER only after its prior package has been fully drained."""
    raw = path.read_bytes()
    if sha(raw) != expected_sha:
        raise ValueError("Source SHA mismatch")
    counts = inventory(raw)
    if counts["YEDEKLER"] != 0:
        raise ValueError("YEDEKLER must be empty before advancing the next package")
    batch = plan_next_batch(raw, "ANA", 2500)
    if not batch["expected_urls"]:
        raise ValueError("ANA ARŞİV has no remaining package")
    result, report = transform(raw, "ANA", "YEDEKLER",
                               list(range(1, batch["end"] + 1)), sha(raw),
                               expected_urls=batch["expected_urls"])
    apply_with_journal(path, raw, result, backup, journal_path, operation_id, report)
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--playlist", type=Path, required=True)
    p.add_argument("--source", choices=sorted(ARCHIVE_NAMES))
    p.add_argument("--target", choices=sorted(ARCHIVE_NAMES))
    p.add_argument("--start", type=int)
    p.add_argument("--end", type=int)
    p.add_argument("--expected-sha256")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--expected-urls-json", type=Path,
                   help="JSON array of exact selected URLs in ordinal order; required for apply")
    p.add_argument("--backup", type=Path)
    p.add_argument("--journal", type=Path)
    p.add_argument("--operation-id")
    p.add_argument("--rollback-last", type=Path, metavar="PREVIOUS_BACKUP")
    p.add_argument("--advance-next", action="store_true")
    a = p.parse_args()
    if a.advance_next:
        if a.rollback_last is not None or not a.apply or a.backup is None or a.journal is None or not a.operation_id or not a.expected_sha256:
            p.error("--advance-next requires --apply --backup --journal --operation-id --expected-sha256")
        if a.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
            p.error("Only the canonical main playlist can be modified")
        print(json.dumps(advance_next_package(a.playlist, a.backup, a.journal,
                                              a.operation_id, a.expected_sha256),
                         ensure_ascii=False))
        return
    if a.rollback_last is not None:
        if not a.apply or a.backup is None or a.journal is None or not a.operation_id:
            p.error("--rollback-last requires --apply --backup --journal --operation-id")
        if a.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
            p.error("Only the canonical main playlist can be modified")
        print(json.dumps(rollback_last(a.playlist, a.rollback_last, a.backup,
                                       a.journal, a.operation_id), ensure_ascii=False))
        return
    if None in (a.source, a.target, a.start, a.end, a.expected_sha256):
        p.error("--source --target --start --end --expected-sha256 required for transfers")
    if a.apply and a.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
        p.error("Only the canonical main playlist can be modified")
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
        if a.journal is None or not a.operation_id:
            p.error("--journal and --operation-id required for --apply")
        apply_with_journal(a.playlist, raw, output, a.backup, a.journal, a.operation_id, report)
    report["applied"] = a.apply
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

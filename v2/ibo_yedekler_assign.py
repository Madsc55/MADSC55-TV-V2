#!/usr/bin/env python3
"""Transactional Turkish/Foreign assignments for the protected IBO YEDEKLER archive.

This tool NEVER edits the source IBO playlist. It writes an independent ledger
and keeps reversible snapshots. Ordinals are 1-based WITHIN YEDEKLER only.
"""
import argparse
import hashlib
import json
from pathlib import Path

from ibo_yedekler_archive import inventory

SCHEMA = 1
TARGETS = {"TURK", "YABANCI"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_new(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError("Refusing to overwrite an existing artifact")
    with path.open("xb") as out:
        out.write(data)


def read_archive(source):
    raw, _, records = inventory(source)
    if len(records) != 18074:
        raise ValueError(f"Expected 18074 YEDEKLER records, found {len(records)}")
    return digest(raw), records


def initial_ledger(source_sha, records):
    return {"schema": SCHEMA, "source_sha256": source_sha,
            "total": len(records), "revision": 0, "assignments": {},
            "history": []}


def validate_ledger(ledger, source_sha, records):
    if (ledger.get("schema") != SCHEMA or ledger.get("source_sha256") != source_sha
            or ledger.get("total") != len(records)):
        raise ValueError("Source playlist changed: refuse stale ledger")
    for key, value in ledger.get("assignments", {}).items():
        if not key.isdigit() or not 1 <= int(key) <= len(records) or value not in TARGETS:
            raise ValueError("Invalid assignment ledger")


def plan(ledger, records, start, end, target):
    if target not in TARGETS or not 1 <= start <= end <= len(records):
        raise ValueError("Invalid target or YEDEKLER-local range")
    changes = []
    for local in range(start, end + 1):
        key = str(local)
        previous = ledger["assignments"].get(key)
        if previous != target:
            record = records[local - 1]
            changes.append({"local_ordinal": local, "global_ordinal": record["ordinal"],
                            "url_sha256": record["url_sha256"], "from": previous, "to": target})
    return changes


def commit(ledger, changes, expected_revision):
    if ledger["revision"] != expected_revision:
        raise ValueError("Stale revision")
    # Replaying an already-applied assignment must not create a new revision.
    if not changes:
        return json.loads(json.dumps(ledger))
    result = json.loads(json.dumps(ledger))
    for change in changes:
        key = str(change["local_ordinal"])
        if result["assignments"].get(key) != change["from"]:
            raise ValueError("Conflicting assignment")
        result["assignments"][key] = change["to"]
    result["revision"] += 1
    result["history"].append({"revision": result["revision"], "changes": changes})
    return result


def rollback(ledger):
    if not ledger["history"]:
        raise ValueError("Nothing to undo")
    result = json.loads(json.dumps(ledger))
    while result["history"] and "undo_of_revision" in result["history"][-1]:
        result["history"].pop()
    if not result["history"]:
        raise ValueError("Nothing to undo")
    last = result["history"].pop()
    for change in reversed(last["changes"]):
        key = str(change["local_ordinal"])
        if result["assignments"].get(key) != change["to"]:
            raise ValueError("Cannot undo modified assignment")
        if change["from"] is None:
            result["assignments"].pop(key, None)
        else:
            result["assignments"][key] = change["from"]
    result["revision"] += 1
    result["history"].append({"revision": result["revision"],
                              "undo_of_revision": last["revision"], "changes": []})
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", default="MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
    p.add_argument("--ledger", required=True)
    p.add_argument("--output", required=True, help="New immutable JSON ledger output")
    p.add_argument("--start", type=int)
    p.add_argument("--end", type=int)
    p.add_argument("--target", choices=sorted(TARGETS))
    p.add_argument("--apply", action="store_true", help="Explicitly authorize writing NEW ledger artifact")
    p.add_argument("--undo-last", action="store_true")
    args = p.parse_args()
    source_sha, records = read_archive(args.source)
    ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8")) if Path(args.ledger).exists() else initial_ledger(source_sha, records)
    validate_ledger(ledger, source_sha, records)
    if args.undo_last:
        if any(x is not None for x in (args.start, args.end, args.target)):
            p.error("Undo cannot be combined with a range")
        updated = rollback(ledger)
        summary = {"operation": "undo_last", "revision": updated["revision"]}
    else:
        if args.start is None or args.end is None or args.target is None:
            p.error("start, end and target required")
        changes = plan(ledger, records, args.start, args.end, args.target)
        updated = commit(ledger, changes, ledger["revision"])
        summary = {"operation": "assign", "start": args.start, "end": args.end,
                   "target": args.target, "changed": len(changes),
                   "revision": updated["revision"]}
    summary.update({"source_sha256": source_sha, "source_modified": False,
                    "other_categories_modified": False})
    if args.apply and updated["revision"] != ledger["revision"]:
        atomic_new(args.output, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode())
        summary["ledger_written"] = str(args.output)
    elif args.apply:
        summary["already_applied"] = True
    else:
        summary["dry_run"] = True
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

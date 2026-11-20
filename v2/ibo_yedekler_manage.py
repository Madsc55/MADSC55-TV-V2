#!/usr/bin/env python3
"""One-command, local-only YEDEKLER archive manager.

Examples:
 python v2/ibo_yedekler_manage.py init --source MADSC55_TV_IBO_CALISANLAR_TEST.m3u8 --root private_archive
 python v2/ibo_yedekler_manage.py assign --root private_archive --start 221 --end 458 --target YABANCI
 python v2/ibo_yedekler_manage.py assign --root private_archive --start 221 --end 458 --target YABANCI --apply
 python v2/ibo_yedekler_manage.py undo --root private_archive --apply
"""
import argparse
import hashlib
import json
from pathlib import Path
from ibo_yedekler_archive import snapshot, inventory
from ibo_yedekler_assign import initial_ledger, validate_ledger, plan, commit, rollback, atomic_new


def ledger_files(root):
    return sorted(root.glob("ledger-*.json"), key=lambda p: int(p.stem.split("-")[-1]))


def load(root):
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    archive = root / "YEDEKLER_ARCHIVE.m3u8"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Archive hash mismatch")
    source_sha = manifest["source_sha256"]
    _, _, records = inventory(archive)
    if len(records) != 18074:
        raise ValueError("Archive is incomplete")
    files = ledger_files(root)
    if not files:
        raise ValueError("Missing ledger")
    ledger = json.loads(files[-1].read_text(encoding="utf-8"))
    validate_ledger(ledger, source_sha, records)
    if ledger["revision"] != int(files[-1].stem.split("-")[-1]):
        raise ValueError("Ledger revision mismatch")
    return ledger, records


def main():
    parser = argparse.ArgumentParser(description="Only YEDEKLER; never changes main playlist")
    subs = parser.add_subparsers(dest="command", required=True)
    init = subs.add_parser("init")
    init.add_argument("--source", required=True)
    init.add_argument("--root", type=Path, required=True)
    assign = subs.add_parser("assign")
    assign.add_argument("--root", type=Path, required=True)
    assign.add_argument("--start", type=int, required=True)
    assign.add_argument("--end", type=int, required=True)
    assign.add_argument("--target", choices=["TURK", "YABANCI"], required=True)
    assign.add_argument("--apply", action="store_true")
    undo = subs.add_parser("undo")
    undo.add_argument("--root", type=Path, required=True)
    undo.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.command == "init":
        manifest = snapshot(args.source, args.root)
        _, _, records = inventory(args.root / "YEDEKLER_ARCHIVE.m3u8")
        ledger = initial_ledger(manifest["source_sha256"], records)
        atomic_new(args.root / "ledger-0.json", (json.dumps(ledger, ensure_ascii=False, indent=2) + "\n").encode())
        print(json.dumps({"initialized": True, "count": len(records), "source_modified": False}))
        return
    ledger, records = load(args.root)
    if args.command == "assign":
        changes = plan(ledger, records, args.start, args.end, args.target)
        updated = commit(ledger, changes, ledger["revision"])
        summary = {"target": args.target, "start": args.start, "end": args.end,
                   "changed": len(changes)}
    else:
        updated = rollback(ledger)
        summary = {"undo": True}
    summary["revision"] = updated["revision"]
    summary["applied"] = bool(args.apply)
    summary["main_playlist_modified"] = False
    if args.apply and updated["revision"] != ledger["revision"]:
        path = args.root / f"ledger-{updated['revision']}.json"
        atomic_new(path, (json.dumps(updated, ensure_ascii=False, indent=2) + "\n").encode())
        summary["ledger"] = str(path)
    elif args.apply:
        summary["already_applied"] = True
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()

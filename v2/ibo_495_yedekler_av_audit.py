#!/usr/bin/env python3
"""Read-only YEDEKLER AV audit. Emits hashed identities only; never edits playlists."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sys

from ibo_single_playlist_transfer import parse, category
from stream_probe import probe, verify_decoded_av

PLAYLIST = Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
WORKERS = 12
TIMEOUT = 15

def digest(data):
    return hashlib.sha256(data).hexdigest()

def audit_one(item):
    index, block = item
    lines = block.splitlines()
    url = lines[-1].strip()
    first = probe(url, timeout=TIMEOUT)
    outcome = first
    attempts = 1
    if first.get("status") == "AV_STREAMS_PRESENT":
        decoded = verify_decoded_av(url, timeout=TIMEOUT)
        outcome = {**first, **decoded}
        outcome["status"] = "AV_VERIFIED" if decoded.get("decoded_av_verified") else decoded.get("decode_status", "DECODE_FAILED")
    # One bounded confirmation attempt for inconclusive/non-verified outcomes.
    if outcome.get("status") != "AV_VERIFIED":
        attempts = 2
        second = probe(url, timeout=TIMEOUT)
        if second.get("status") == "AV_STREAMS_PRESENT":
            decoded = verify_decoded_av(url, timeout=TIMEOUT)
            second = {**second, **decoded}
            second["status"] = "AV_VERIFIED" if decoded.get("decoded_av_verified") else decoded.get("decode_status", "DECODE_FAILED")
        if second.get("status") == "AV_VERIFIED":
            outcome = second
        else:
            outcome = second
    canonical = json.dumps(outcome, sort_keys=True, separators=(",", ":")).encode()
    # Only repeatable media absence is a failed candidate; transport/probe errors stay uncertain.
    deterministic = outcome.get("status") in ("NO_MEDIA", "NO_DECODED_FRAME")
    status = "verified" if outcome.get("status") == "AV_VERIFIED" else (
        "failed" if deterministic and attempts >= 2 else "uncertain")
    return {
        "ordinal": index,
        "channel_sha256": digest(block.encode("utf-8")),
        "url_sha256": digest(url.encode("utf-8")),
        "run_id": int(os.environ["GITHUB_RUN_ID"]),
        "evidence_sha256": digest(canonical),
        "attempts": attempts,
        "repeatable_av_failure": status == "failed",
        "status": status,
        "probe_status": outcome.get("status", "UNKNOWN"),
        "decode_status": outcome.get("decode_status", "NOT_RUN"),
        "evidence_level": outcome.get("evidence_level", "ffprobe_ffmpeg"),
        "decoded_av_verified": bool(outcome.get("decoded_av_verified")),
    }

def main():
    raw = PLAYLIST.read_bytes()
    _, blocks = parse(raw)
    selected = [b for b in blocks if category(b.splitlines()[0]) == "YEDEKLER"]
    if len(selected) != 1792:
        raise SystemExit(f"Expected 1792 YEDEKLER entries; found {len(selected)}")
    if len({digest(b.encode("utf-8")) for b in selected}) != len(selected):
        raise SystemExit("Duplicate immutable channel identity; fail closed")
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        entries = list(pool.map(audit_one, enumerate(selected, 1)))
    from collections import Counter
    counts = dict(Counter(x["status"] for x in entries))
    report = {
        "schema": 1,
        "playlist_sha256": digest(raw),
        "source_run_id": int(os.environ["GITHUB_RUN_ID"]),
        "source_commit": os.environ["GITHUB_SHA"],
        "entries": entries,
        "counts": counts,
        "read_only": True,
    }
    Path("report.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\\n", encoding="utf-8")
    print(json.dumps({"run_id": report["source_run_id"], "playlist_sha256": report["playlist_sha256"], "counts": counts, "entries": len(entries)}))
if __name__ == "__main__":
    main()

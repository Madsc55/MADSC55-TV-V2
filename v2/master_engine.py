#!/usr/bin/env python3
"""V2 master orchestration: public source discovery, history, checks, encrypted archive, device batches."""
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
from discover import ROOT, LIVE, SOURCES, entries, turkish_candidate, fetch, approved_github_source, DYNAMIC, GITHUB_APPROVALS, FORGE, FORGE_APPROVALS
from historical_url_recovery import recover, read_records, validate_url
from encrypted_archive import append, restore
from real_ibo_scan import check_hls

def build(source_texts, live_text, history=(), checker=None, workers=8):
    """Pure integration boundary; source_texts contains actual fetched M3U contents."""
    existing = {x["url"] for x in entries(live_text)}
    candidate_map = {}
    audit = []
    for source, data in source_texts:
        if not data.lstrip().startswith("#EXTM3U"):
            audit.append({"id": source["id"], "parsed": 0, "eligible": 0, "status": "INVALID_M3U"})
            continue
        parsed = list(entries(data))
        eligible = 0
        for item in parsed:
            if not turkish_candidate(item, source.get("scope", "candidate")):
                continue
            eligible += 1
            url = item["url"]
            if url in existing or not validate_url(url):
                continue
            row = candidate_map.setdefault(url, dict(item, source_ids=[], history=[]))
            if source["id"] not in row["source_ids"]:
                row["source_ids"].append(source["id"])
        audit.append({"id": source["id"], "parsed": len(parsed), "eligible": eligible, "status": "FETCHED"})
    historic, history_report = recover(history, [{"url": url} for url in existing])
    for item in historic:
        url = item["url"]
        if not validate_url(url):
            continue
        if url in existing:
            continue
        row = candidate_map.setdefault(url, dict(item, source_ids=[], history=[]))
        row["history"].append({"status": "HISTORICAL_NOT_REVERIFIED", "source": item.get("source", "historical")})
    items = list(candidate_map.values())
    if checker is None:
        return items, audit, history_report
    def check(item):
        try:
            return bool(checker(item))
        except Exception:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(check, items))
    for item, ok in zip(items, outcomes):
        item["network_status"] = "HLS_MANIFEST_REACHABLE" if ok else "UNKNOWN_OR_FAILED"
        item["device_verified"] = False
    return items, audit, history_report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--history", type=Path)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=float, default=12)
    p.add_argument("--limit", type=int, default=500)
    args = p.parse_args()
    if not 1 <= args.limit <= 500 or not 1 <= args.workers <= 32 or not 0 < args.timeout <= 120:
        p.error("limit 1..500; workers 1..32; timeout >0 and <=120")
    if not os.environ.get("V2_ARCHIVE_KEY_HEX"):
        p.error("V2_ARCHIVE_KEY_HEX secret is required")
    if args.archive.exists() or args.out.exists():
        p.error("Refusing to overwrite previous archive or output directory")
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    # Include only previously approved dynamic GitHub and forge sources.
    if DYNAMIC.exists() and GITHUB_APPROVALS.exists():
        approvals = set(json.loads(GITHUB_APPROVALS.read_text(encoding="utf-8")).get("approved_sha256", []))
        for candidate in json.loads(DYNAMIC.read_text(encoding="utf-8")).get("sources", [])[:240]:
            url = candidate.get("url", "")
            if approved_github_source(url, approvals) and not any(s["url"] == url for s in sources):
                sources.append({"id": "github-auto-" + hashlib.sha256(url.encode()).hexdigest()[:20], "url": url, "scope": "candidate"})
    if FORGE.exists() and FORGE_APPROVALS.exists():
        from forge_source_review import approved_sources
        approvals = set(json.loads(FORGE_APPROVALS.read_text(encoding="utf-8")).get("approved_sha256", []))
        for candidate in approved_sources(json.loads(FORGE.read_text(encoding="utf-8")), approvals):
            if not any(s["url"] == candidate["url"] for s in sources):
                sources.append(candidate)
    live_text = LIVE.read_text(encoding="utf-8-sig")
    source_texts, failures = [], []
    for source in sources:
        try:
            content = fetch(source["url"])
            if not content.lstrip().startswith("#EXTM3U"):
                raise ValueError("Source returned non-M3U content")
            source_texts.append((source, content))
        except Exception as exc:
            failures.append({"id": source["id"], "status": "FETCH_FAILED", "reason": type(exc).__name__})
    history = list(read_records(args.history)) if args.history else []
    items, audit, history_report = build(source_texts, live_text, history,
                                         checker=lambda x: check_hls(x, args.timeout),
                                         workers=args.workers)
    # Never silently publish a partial scan as complete.
    args.out.mkdir(parents=True)
    for item in items:
        append(args.archive, item)
    restored = restore(args.archive) if items else []
    if restored != items:
        raise RuntimeError("Encrypted archive restore mismatch")
    if not items:
        raise RuntimeError("No valid candidates; refusing to report an empty scan as successful")
    if not any(item["network_status"] == "HLS_MANIFEST_REACHABLE" for item in items):
        raise RuntimeError("No reachable HLS manifests; refusing successful scan status")
    verified = [x for x in items if x["network_status"] == "HLS_MANIFEST_REACHABLE"]
    for n in range(0, len(verified), args.limit):
        batch = verified[n:n + args.limit]
        lines = ["#EXTM3U"]
        for item in batch:
            name = str(item.get("name", "Unknown")).replace("\n", " ").replace("\r", " ").replace(",", " ")
            lines += [f'#EXTINF:-1,{name}', item["url"]]
        (args.out / f"ibo_part_{n // args.limit + 1:04}.m3u8").write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = {"configured_sources": len(sources), "fetched_sources": len(audit),
              "failed_sources": failures, "source_audit": audit, "unique_candidates": len(items),
              "manifest_reachable": len(verified), "unknown_or_failed": len(items) - len(verified),
              "historical": history_report, "archive_restore_verified": restored == items,
              "device_verified": False, "batch_count": (len(verified) + args.limit - 1) // args.limit,
              "status": "PARTIAL_SOURCE_FAILURE" if failures else "COMPLETE_SOURCE_FETCH"}
    (args.out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "source_audit"}, ensure_ascii=False))
    if failures:
        raise SystemExit("Partial source coverage; results preserved but run not successful")

if __name__ == "__main__":
    main()

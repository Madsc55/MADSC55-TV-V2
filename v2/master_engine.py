#!/usr/bin/env python3
"""V2 master orchestration: public source discovery, history, checks, encrypted archive, device batches."""
import argparse
import concurrent.futures
import hashlib
import json
import math
import multiprocessing
import os
import signal
import time
from pathlib import Path
from urllib.parse import urlsplit
from discover import ROOT, LIVE, SOURCES, entries, turkish_candidate, fetch, approved_github_source, DYNAMIC, GITHUB_APPROVALS, FORGE, FORGE_APPROVALS
from historical_url_recovery import recover, read_records, validate_url
from historical_inventory_guard import classify, reconcile, _chunks
from encrypted_archive import append, restore
from real_ibo_scan import check_hls
from media_decode import decode_media

def active_sources(configured):
    """Keep retired sources in the catalog but never fetch them in live runs."""
    return [source for source in configured if source.get("enabled", True) is not False]


def approved_dynamic_sources(configured, dynamic, approvals):
    """Review every discovered source; position in a report is not approval."""
    sources = list(configured)
    seen = {source["url"] for source in sources}
    for candidate in dynamic.get("sources", []):
        url = candidate.get("url", "")
        if approved_github_source(url, approvals) and url not in seen:
            sources.append({"id": "github-auto-" + hashlib.sha256(url.encode()).hexdigest()[:20],
                            "url": url, "scope": "candidate"})
            seen.add(url)
    return sources


def _isolated_call(connection, operation):
    # Each Linux worker owns its process group, including any FFmpeg children.
    os.setsid()
    try:
        connection.send(("ready", None))
        connection.send(("ok", operation()))
    except BaseException as exc:
        connection.send(("error", type(exc).__name__))
    finally:
        connection.close()


def run_bounded(operation, seconds):
    """Run one small batch with a hard wall deadline and reap its whole group.

    Linux fork intentionally supports the existing checker closures. A blocked
    socket or executor cannot keep the parent waiting after the batch deadline.
    """
    if seconds <= 0:
        return "timeout", None
    context = multiprocessing.get_context("fork")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(target=_isolated_call, args=(writer, operation))
    deadline = time.monotonic() + seconds
    ready = False
    process.start()
    writer.close()
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not reader.poll(remaining):
                return "timeout", None
            try:
                status, result = reader.recv()
            except EOFError:
                return "error", "WorkerExited"
            if status == "ready":
                ready = True
                continue
            return status, result
    finally:
        # A deadline can race the ready message. Verify the worker created its
        # own group even when that message has not yet reached the parent.
        isolated = ready
        if not isolated:
            try:
                isolated = os.getpgid(process.pid) == process.pid
            except ProcessLookupError:
                pass
        if isolated:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif process.is_alive():
            process.kill()
        process.join()
        reader.close()
        process.close()


def _verify_batch(batch, checker, media_checker):
    def check(original):
        item = dict(original)
        item.update(network_status="UNKNOWN_OR_FAILED", media_decoded=False,
                    device_verified=False, verification_status="CHECKED")
        try:
            if checker(item) is True:
                item["network_status"] = "HLS_MANIFEST_REACHABLE"
                item["media_decoded"] = media_checker(item) is True
        except Exception:
            pass
        return item
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as pool:
        return list(pool.map(check, batch))


def verify_in_batches(items, checker, media_checker, *, workers, deadline,
                      batch_timeout, checkpoint, clock=None, runner=None):
    """Keep all candidates; submit at most one worker-sized batch at a time."""
    clock = time.monotonic if clock is None else clock
    runner = run_bounded if runner is None else runner
    for item in items:
        item.update(network_status="UNTESTED", media_decoded=False,
                    device_verified=False, verification_status="UNTESTED")
    checkpoint(items, "inventory_before_verification")
    for offset in range(0, len(items), workers):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        batch = items[offset:offset + workers]
        status, results = runner(lambda: _verify_batch(batch, checker, media_checker),
                                 min(batch_timeout, remaining))
        if status == "ok":
            for item, result in zip(batch, results):
                item.update(result)
        else:
            for item in batch:
                item["verification_status"] = "UNTESTED_BATCH_" + status.upper()
        checkpoint(batch, "verification_batch")
    return all(item["verification_status"] == "CHECKED" for item in items)


def build(source_texts, live_text, history=(), checker=None, workers=8, media_checker=None):
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
            row = candidate_map.setdefault(url, dict(item, scope=source.get("scope", "candidate"), source_ids=[], history=[]))
            if source.get("scope") in ("TR", "AZ") and row.get("scope") not in ("TR", "AZ"):
                row["scope"] = source["scope"]
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
        previous_sources = item.get("source_ids", [])
        for source_id in previous_sources if isinstance(previous_sources, list) else []:
            if isinstance(source_id, str) and source_id and source_id not in row["source_ids"]:
                row["source_ids"].append(source_id)
        for field in ("name", "logo", "tvg_id", "group", "scope", "country"):
            if not row.get(field) and item.get(field):
                row[field] = item[field]
    # Historical duplicates carry independent source attribution. Never discard it.
    for old_row in history:
        old_url = old_row.get("url") if isinstance(old_row, dict) else None
        if validate_url(old_url) and old_url in candidate_map:
            item = candidate_map[old_url]
            historical_sources = old_row.get("source_ids", [])
            historical_sources = historical_sources if isinstance(historical_sources, list) else []
            for source_id in [old_row.get("source"), *historical_sources]:
                if isinstance(source_id, str) and source_id and source_id not in item["source_ids"]:
                    item["source_ids"].append(source_id)
            for field in ("name", "logo", "tvg_id", "group", "scope", "country"):
                if not item.get(field) and old_row.get(field):
                    item[field] = old_row[field]
    items = list(candidate_map.values())
    for item in items:
        item.update(classify(item))
        item["spoken_language_verified"] = False
    if checker is None:
        return items, audit, history_report
    def check(item):
        try:
            # Reject truthy error payloads; only explicit reachability is accepted.
            return checker(item) is True
        except Exception:
            return False
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(check, items))
    for item, ok in zip(items, outcomes):
        item["network_status"] = "HLS_MANIFEST_REACHABLE" if ok else "UNKNOWN_OR_FAILED"
        item["media_decoded"] = False
        item["device_verified"] = False
    if media_checker is not None:
        reachable = [item for item in items if item["network_status"] == "HLS_MANIFEST_REACHABLE"]
        def decode(item):
            try:
                # Only an explicit decoder success can promote a stream to AV-verified.
                # Non-empty error dictionaries and strings must never count as playback.
                return media_checker(item) is True
            except Exception:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            decoded = list(pool.map(decode, reachable))
        for item, ok in zip(reachable, decoded):
            item["media_decoded"] = ok
    return items, audit, history_report

def hls_reachable(item, timeout):
    """Scanner returns the same entry on actual HLS manifest success, not True."""
    return check_hls(item, timeout) is item


def archive_records(items, history):
    """Archive every historical row, including duplicates/hash-only and failures."""
    return list(_chunks(history, "raw_historical_evidence")) + list(items)


def export_candidates(items):
    """Decoded TR/AZ candidates only; do not publish unclassified history."""
    return [row for row in items if row.get("media_decoded") is True
            and row.get("region_candidate") in ("TR", "AZ")]


def render_m3u(batch):
    """Render only real candidate records; never synthesize stream addresses."""
    lines = ["#EXTM3U"]
    for item in batch:
        name = str(item.get("name", "Unknown")).replace("\n", " ").replace("\r", " ").replace(",", " ")
        attrs = " ".join(f'{label}="{str(item[key]).replace(chr(34), "&quot;").replace(chr(10), " ").replace(chr(13), " ")}"' for key, label in (("tvg_id", "tvg-id"), ("logo", "tvg-logo"), ("group", "group-title")) if item.get(key))
        lines.extend((f"#EXTINF:-1{chr(32) + attrs if attrs else chr(0)[:0]},{name}", item["url"]))
    return "\n".join(lines) + "\n"

def main():
    started = time.monotonic()
    p = argparse.ArgumentParser()
    p.add_argument("--history", type=Path)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=float, default=12)
    p.add_argument("--limit", type=int, default=500, help="M3U package size, not scan coverage")
    p.add_argument("--max-seconds", type=float, default=5400,
                   help="Total network/AV budget; reserve time for encrypted finalization")
    args = p.parse_args()
    if not 1 <= args.limit <= 2000 or not 1 <= args.workers <= 32 or not math.isfinite(args.timeout) or not 0 < args.timeout <= 120:
        p.error("limit 1..2000; workers 1..32; timeout >0 and <=120")
    if not math.isfinite(args.max_seconds) or not 0 < args.max_seconds <= 5400:
        p.error("max-seconds must be finite, >0 and <=5400")
    deadline = started + args.max_seconds
    key_hex = os.environ.get("V2_ARCHIVE_KEY_HEX", "")
    if len(key_hex) != 64:
        p.error("V2_ARCHIVE_KEY_HEX must contain 64 hex characters")
    try:
        bytes.fromhex(key_hex)
    except ValueError:
        p.error("V2_ARCHIVE_KEY_HEX must be hexadecimal")
    archive_path = args.archive.resolve(strict=False)
    output_path = args.out.resolve(strict=False)
    if (args.archive.is_symlink() or args.out.is_symlink() or
            archive_path.exists() or output_path.exists()):
        p.error("Refusing to overwrite previous archive or output directory")
    if archive_path == output_path or archive_path in output_path.parents or output_path in archive_path.parents:
        p.error("Archive and output directory must be separate, non-nested paths")
    sources = active_sources(json.loads(SOURCES.read_text(encoding="utf-8"))["sources"])
    # Include only previously approved dynamic GitHub and forge sources.
    if DYNAMIC.exists() and GITHUB_APPROVALS.exists():
        approvals = set(json.loads(GITHUB_APPROVALS.read_text(encoding="utf-8")).get("approved_sha256", []))
        sources = approved_dynamic_sources(sources, json.loads(DYNAMIC.read_text(encoding="utf-8")), approvals)
    if FORGE.exists() and FORGE_APPROVALS.exists():
        from forge_source_review import approved_sources
        approvals = set(json.loads(FORGE_APPROVALS.read_text(encoding="utf-8")).get("approved_sha256", []))
        for candidate in approved_sources(json.loads(FORGE.read_text(encoding="utf-8")), approvals):
            if not any(s["url"] == candidate["url"] for s in sources):
                sources.append(candidate)
    # Fail closed before any network access if a requested output would target
    # the protected playlist or source configuration (including symlink aliases).
    protected_paths = [LIVE.resolve(strict=False), SOURCES.resolve(strict=False)]
    if args.history is not None:
        protected_paths.append(args.history.resolve(strict=False))
    if DYNAMIC.exists():
        protected_paths.append(DYNAMIC.resolve(strict=False))
    if GITHUB_APPROVALS.exists():
        protected_paths.append(GITHUB_APPROVALS.resolve(strict=False))
    if FORGE.exists():
        protected_paths.append(FORGE.resolve(strict=False))
    if FORGE_APPROVALS.exists():
        protected_paths.append(FORGE_APPROVALS.resolve(strict=False))
    if any(path == archive_path or path == output_path or
           output_path in path.parents for path in protected_paths):
        p.error("Archive/output path overlaps protected playlist or source configuration")
    protected_hash_before = hashlib.sha256(LIVE.read_bytes()).hexdigest()
    live_text = LIVE.read_text(encoding="utf-8-sig")
    from source_failover import SourceCache, execute_pipeline
    cache = SourceCache(ROOT / "cache" / "source-failover")
    history = list(read_records(args.history)) if args.history else []
    args.out.mkdir(parents=True)
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path = args.out / "checkpoint.enc"
    def checkpoint(records, stage):
        for block in _chunks(records, stage):
            append(checkpoint_path, block)
    # Protect raw history before the first network operation. Source metadata
    # and every parsed candidate are checkpointed without plaintext URL output.
    checkpoint(history, "raw_historical_evidence")
    checkpoint(sources, "planned_sources")
    source_texts, failures, recovery_audit = [], [], []
    for source in sources:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result = {"id": source["id"], "status": "BUDGET_EXHAUSTED", "fresh": False}
            content = None
        else:
            status, response = run_bounded(
                lambda: execute_pipeline([source], cache)[0], min(90, remaining))
            if status == "ok":
                _, content, result = response
            else:
                content = None
                result = {"id": source["id"], "status": "SOURCE_" + status.upper(), "fresh": False}
        recovery_audit.append(result)
        checkpoint([result], "source_fetch_result")
        if content is not None:
            source_texts.append((source, content))
            parsed_items, _, _ = build([(source, content)], live_text)
            checkpoint(parsed_items, "source_candidates")
        if not result["fresh"]:
            failures.append({"id": source["id"], "status": result["status"],
                             "reason": "Fresh source unavailable"})
    from collections import Counter
    av_diagnostics = Counter()
    def probe_with_diagnostics(item):
        detail = {}
        ok = decode_media(item, args.timeout, diagnostic=detail)
        item["decoder_diagnostic"] = detail
        return ok
    items, audit, history_report = build(source_texts, live_text, history)
    verification_complete = verify_in_batches(
        items, lambda x: hls_reachable(x, args.timeout), probe_with_diagnostics,
        workers=args.workers, deadline=deadline, batch_timeout=2 * args.timeout + 10,
        checkpoint=checkpoint)
    for item in items:
        detail = item.get("decoder_diagnostic")
        if detail is not None:
            category = detail.get("reason", "unknown")
            if category == "ffmpeg_nonzero_exit":
                category += ":" + detail.get("stderr_category", "other")
            av_diagnostics[category] += 1
    incomplete = bool(failures) or not verification_complete
    checkpoint([{"verification_complete": verification_complete,
                 "failed_sources": len(failures),
                 "budget_exhausted": time.monotonic() >= deadline}], "checkpoint_summary")
    # The protected archive includes original historical rows even if they
    # are dead, duplicated, hash-only, or not classified as TR/AZ.
    protected_history = None
    if history:
        _, _, protected_history = reconcile(history, [{"url": x["url"]} for x in items])
        protected_history["expected_historical_records"] = 4955
        protected_history["real_4955_baseline_present"] = len(history) == 4955
    archived_items = archive_records(items, history)
    for item in archived_items:
        append(args.archive, item)
    restored = restore(args.archive) if archived_items else []
    if restored != archived_items:
        raise RuntimeError("Encrypted archive restore mismatch")
    verified = export_candidates(items)
    # A manifest check is not media decoding; never export it as a verified stream.
    # A partial source fetch cannot publish a new package as complete.
    if not incomplete:
        for n in range(0, len(verified), args.limit):
            batch = verified[n:n + args.limit]
            (args.out / f"ibo_part_{n // args.limit + 1:04}.m3u8").write_text(render_m3u(batch), encoding="utf-8")
    # Export each standard size only when enough independently media-decoded
    # candidates exist; never pad packages with fabricated or unverified URLs.
    standard_package_counts = {}
    if not incomplete:
        for package_size in (500, 1000, 2000):
            full_packages = len(verified) // package_size
            standard_package_counts[str(package_size)] = full_packages
            for index in range(full_packages):
                batch = verified[index * package_size:(index + 1) * package_size]
                (args.out / f"ibo_{package_size}_part_{index + 1:04}.m3u").write_text(render_m3u(batch), encoding="utf-8")
    else:
        standard_package_counts = {"500": 0, "1000": 0, "2000": 0}
    protected_hash_after = hashlib.sha256(LIVE.read_bytes()).hexdigest()
    if protected_hash_before != protected_hash_after:
        raise RuntimeError("Protected main playlist SHA-256 changed during scan")
    report = {"protected_playlist_sha256_before": protected_hash_before,
              "protected_playlist_sha256_after": protected_hash_after,
              "protected_playlist_unchanged": True,
              "configured_sources": len(sources), "fetched_sources": len(audit),
              "failed_sources": failures, "source_audit": audit, "source_recovery_audit": recovery_audit, "unique_candidates": len(items),
              "manifest_reachable": sum(x["network_status"] == "HLS_MANIFEST_REACHABLE" for x in items),
              "media_decoded": len(verified), "all_regions_media_decoded": sum(item.get("media_decoded") is True for item in items), "tr_az_export_eligible": len(verified), "ffmpeg_failure_categories": dict(sorted(av_diagnostics.items())), "unknown_or_failed": sum(x["network_status"] != "HLS_MANIFEST_REACHABLE" for x in items),
              "historical": history_report, "historical_loss_guard": protected_history,
              "historical_raw_records_preserved": len(history),
              "archive_restore_verified": bool(archived_items) and restored == archived_items,
              "device_verified": False, "approved": False,
              "verification_complete": verification_complete,
              "verification_unfinished": sum(item["verification_status"] != "CHECKED" for item in items),
              "max_seconds": args.max_seconds, "budget_exhausted": time.monotonic() >= deadline,
              "checkpoint": str(checkpoint_path), "checkpoint_encrypted": True,
              "standard_full_packages": standard_package_counts, "batch_count": (len(verified) + args.limit - 1) // args.limit if not incomplete else 0,
              "status": "INCOMPLETE_VERIFICATION" if not verification_complete else ("PARTIAL_SOURCE_FAILURE" if failures else ("NO_CANDIDATES" if not items else ("NO_MEDIA_DECODED" if not verified else "COMPLETE_SOURCE_FETCH")))}
    (args.out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "source_audit"}, ensure_ascii=False))
    if not verification_complete:
        raise SystemExit("Verification incomplete; encrypted inventory and checkpoint preserved, no packages exported")
    if failures:
        raise SystemExit("Partial source coverage; results preserved but run not successful")
    if not items:
        raise SystemExit("No candidates; report preserved, no packages exported")
    if not verified:
        raise SystemExit("No media-decoded candidates; inventory and report preserved, no packages exported")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only Turkish/world M3U source-level reachability and #60/#72 loss evidence.

Never fetches a media stream, never emits source URLs or access tokens, and
never treats a playlist header or historical VIDEO_DECODED flag as live playback.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

from source_availability_audit import probe as source_header_probe
from compare_historical_playback import load as load_aggregate

OLD_RUN = 40743765437
NEW_RUN = 40948768782


def safe_probing_result(source, checker):
    try:
        outcome = checker(source["url"])
        if not isinstance(outcome, dict) or not isinstance(outcome.get("status"), str):
            outcome = {"status": "INVALID_AUDIT_RESPONSE"}
    except Exception as exc:
        outcome = {"status": "FETCH_ERROR", "error": type(exc).__name__}
    # Whitelist metadata fields: never leak endpoint URL, query or token.
    return {"source_id": source["id"], "scope": source.get("scope", "candidate"),
            "source_url_sha256": hashlib.sha256(source["url"].encode()).hexdigest(),
            "status": outcome["status"],
            **({"http_status": outcome["http_status"]}
               if type(outcome.get("http_status")) is int else {}),
            **({"error_type": outcome.get("error", "")[:80]}
               if outcome.get("status") == "FETCH_ERROR" else {})}


def audit_endpoints(sources, checker=source_header_probe, workers=8):
    if not isinstance(sources, list) or not sources or not 1 <= workers <= 16:
        raise ValueError("Invalid configured sources or parallelism")
    if len({s["id"] for s in sources}) != len(sources) or any(
        not isinstance(s, dict) or not isinstance(s.get("id"), str)
        or not isinstance(s.get("url"), str) or s.get("kind", "m3u") != "m3u"
        for s in sources
    ):
        raise ValueError("Invalid or duplicated M3U source")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(lambda s: safe_probing_result(s, checker), sources))
    available = sum(item["status"] == "HTTP_OK" for item in results)
    statuses = dict(sorted(Counter(item["status"] for item in results).items()))
    return {"schema": 1, "kind": "READ_ONLY_SOURCE_HEADERS_NOT_STREAM_PLAYBACK",
            "configured_sources": len(sources), "source_headers_reachable": available,
            "source_headers_unreachable": len(sources) - available,
            "status": ("SOURCE_HEADERS_REACHABLE" if available == len(sources)
                       else "PARTIAL_SOURCE_HEADERS" if available
                       else "NO_SOURCE_HEADERS_REACHABLE"),
            "status_counts": statuses, "sources": results,
            "media_streams_probed": 0, "playback_verified": False,
            "protected_playlist_modified": False}


def compare_original_runs(old_path, new_path, baseline_path):
    old, old_by_hash = load_aggregate(str(old_path))
    new, new_by_hash = load_aggregate(str(new_path))
    baseline = [json.loads(line) for line in
                Path(baseline_path).read_text(encoding="utf-8").splitlines() if line]
    historical = {row["url_sha256"] for row in baseline}
    old_only = old_by_hash.keys() - new_by_hash.keys()
    decoded_missing = {sha for sha in old_only
                       if old_by_hash[sha].get("playback") == "VIDEO_DECODED"}
    if (len(old_by_hash) != 27047 or len(new_by_hash) != 13518 or
            len(baseline) != len(historical) or len(historical) != 4955 or
            decoded_missing != historical):
        raise ValueError("Original #60/#72 true historical loss baseline differs")
    by_source_old = Counter(str(row.get("source") or "UNKNOWN")
                            for row in old_by_hash.values())
    by_source_new = Counter(str(row.get("source") or "UNKNOWN")
                            for row in new_by_hash.values())
    losses = Counter(str(old_by_hash[sha].get("source") or "UNKNOWN")
                     for sha in old_only)
    breakdown = [{
        "source_id": source, "old_tested": by_source_old[source],
        "new_tested": by_source_new[source],
        "old_only_url_identities": losses[source],
        "status": "NO_LIVE_STREAM_RETEST",
    } for source in sorted(by_source_old.keys() | by_source_new.keys())]
    return {"schema": 1, "kind": "REAL_RUN60_RUN72_HASH_EVIDENCE_NOT_LIVE",
            "old_run_id": OLD_RUN, "new_run_id": NEW_RUN,
            "old_unique_tested": len(old_by_hash), "new_unique_tested": len(new_by_hash),
            "common_url_identities": len(old_by_hash.keys() & new_by_hash.keys()),
            "old_only_url_identities": len(old_only),
            "new_only_url_identities": len(new_by_hash.keys() - old_by_hash.keys()),
            "previously_video_decoded_not_retested": len(decoded_missing),
            "original_history_baseline_exact_membership": True,
            "source_breakdown": breakdown,
            "currently_dead_urls_proven": None, "present_day_stream_playback_retested": False,
            "no_stream_urls_emitted": True}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sources", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--historical-old", type=Path)
    p.add_argument("--historical-new", type=Path)
    p.add_argument("--baseline", type=Path)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.output.resolve() == args.sources.resolve():
        p.error("Refusing to overwrite an existing source file/report")
    config = json.loads(args.sources.read_text(encoding="utf-8"))
    result = audit_endpoints(config["sources"], workers=args.workers)
    selected = [args.historical_old, args.historical_new, args.baseline]
    if any(v is not None for v in selected):
        if not all(v is not None for v in selected):
            p.error("Historical loss evidence requires both real aggregates and immutable baseline")
        result["historical_loss"] = compare_original_runs(*selected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("M3U source headers reachable:", result["source_headers_reachable"], "/",
          result["configured_sources"], "historical identity comparison:",
          result.get("historical_loss", {}).get("previously_video_decoded_not_retested", "NOT_LOADED"))


if __name__ == "__main__":
    main()

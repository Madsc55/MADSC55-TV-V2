"""Offline, fail-closed import of already recorded #17/#18/#20 HTTP evidence.

No channel search. Requires the real encrypted worldwide checkpoint and key.
Does not promote a one-segment sample into scanner-level AV acceptance.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
from scan_checkpoint import _read_progress_rows, checkpoint_row, save_progress

OUTCOMES = {"AV_SAMPLE_VERIFIED": 1, "RETRY_HTTP_503": 6, "REVIEW_HTTP_404": 8}

def reconcile(rows, report):
    if (report.get("tasks") != [17, 18, 20]
            or report.get("unique_urls_attempted") != 15
            or report.get("attempts_this_batch") != 17
            or report.get("latest_outcomes") != OUTCOMES
            or len(report.get("observations", [])) != 15):
        raise ValueError("Unexpected bounded report")
    lookup = {r["url_sha256"]: (url, r) for url, r in rows.items()}
    if len(lookup) != len(rows):
        raise ValueError("Ambiguous hash identity")
    merged, seen, applied = dict(rows), set(), 0
    for item in report["observations"]:
        sha = item["url_sha256"]
        if sha in seen or sha not in lookup:
            raise ValueError("Duplicate or unknown hash; abort all")
        seen.add(sha)
        url, old = lookup[sha]
        latest = item["attempts"][-1]
        dt = datetime.fromisoformat(latest["finished_at_utc"].replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("Unzoned timestamp")
        when = dt.timestamp()
        kind = item["latest_disposition"]
        if kind not in OUTCOMES:
            raise ValueError("Unexpected disposition")
        if kind == "AV_SAMPLE_VERIFIED":
            if (latest.get("outcome") != "DECODED_AV_SAMPLE"
                    or latest.get("video_frame_decoded") is not True
                    or latest.get("audio_frame_decoded") is not True
                    or not all(latest.get(k) for k in
                               ("segment_sha256", "video_frame_md5", "audio_frame_md5"))):
                raise ValueError("Unproven sample")
        else:
            expected = 404 if kind == "REVIEW_HTTP_404" else 503
            if (latest.get("outcome") != "HTTP_ERROR"
                    or expected not in [latest.get(k) for k in
                        ("manifest_http_status", "variant_http_status", "segment_http_status")]):
                raise ValueError("Unproven HTTP status")
        count = item["recovery_attempts_after_batch"]
        if type(count) is not int or not 0 <= count <= 3:
            raise ValueError("Invalid retry count")
        if when <= old["checked_at"]:
            continue
        diag = dict(old["diagnostics"])
        diag["bounded_retry_import"] = {
            "source_run_id": report["source_run_id"],
            "url_sha256": sha, "disposition": kind}
        # A single segment proves only a sample; preserve prior full AV evidence.
        result = old["result"] if kind == "AV_SAMPLE_VERIFIED" else None
        merged[url] = checkpoint_row(
            url, result, diag, checked_at=when, recovery_attempts=count)
        applied += 1
    return merged, applied

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()
    if args.checkpoint.name != "ibo-scan-progress.enc" or args.report.is_symlink():
        p.error("Invalid evidence path")
    secret = os.environ.get("V2_ARCHIVE_PASSPHRASE")
    if not secret:
        p.error("V2_ARCHIVE_PASSPHRASE is required")
    rows = _read_progress_rows(args.checkpoint, secret, worldwide=True)
    if not rows:
        p.error("Existing authenticated checkpoint required")
    report = json.loads(args.report.read_text(encoding="utf-8"))
    merged, count = reconcile(rows, report)
    if args.apply and count:
        save_progress(args.checkpoint, secret, worldwide=True, rows=merged)
    print(json.dumps({"existing_rows": len(rows), "eligible_updates": count,
                      "applied": count if args.apply else 0, "dry_run": not args.apply}))

if __name__ == "__main__":
    main()

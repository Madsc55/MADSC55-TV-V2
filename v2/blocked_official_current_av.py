#!/usr/bin/env python3
"""Real, bounded FFprobe + FFmpeg recheck of exact official-channel alternatives.

Only pre-approved public M3U feeds and exact TVG-ID plus channel-name matching.
No plaintext stream URLs in public reports or logs; RSA-sealed evidence only.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

from blocked_official_source_handoff import CONFIG, PUBLIC_KEY, SOURCES, TARGETS, audit
from final_batch_acceptance import probe
from stage3_sealed_export import seal_rows

HEX = re.compile(r"[0-9a-f]{64}\Z")
STATUSES = {"VIDEO_AUDIO_DECODED", "VIDEO_AUDIO_STREAMS_ONLY", "VIDEO_ONLY",
            "AUDIO_ONLY", "NO_AV", "UNVERIFIED", "UNSAFE_OR_UNRESOLVED_HOST",
            "PROBE_UNCONFIRMED"}
# A single second attempt is allowed only for potentially transient probe failures.
# Authentication/HTTP 403/404, unsafe hosts and codec/AV observations never retry.
TRANSIENT_RECHECK = frozenset({
    "PROBE_FAILED_NETWORK_TIMEOUT",
    "PROBE_FAILED_DNS_RESOLUTION_ERROR",
    "PROBE_UNCONFIRMED",
})


def scan(config, *, reader=None, prober=probe, workers=4):
    if not 1 <= workers <= 8:
        raise ValueError("Invalid AV worker count")
    source, candidates = audit(config) if reader is None else audit(config, reader=reader)
    if len(candidates) > 500 or len({x["url_sha256"] for x in candidates}) != len(candidates):
        raise ValueError("Invalid exact candidate inventory")

    def checked(evidence, digest):
        if (not isinstance(evidence, dict) or evidence.get("url_sha256") != digest
                or any(type(evidence.get(x)) is not bool for x in ("video", "audio", "decoded"))):
            raise ValueError("Invalid real AV evidence")
        status = evidence.get("status")
        if (not isinstance(status, str) or status not in STATUSES and
                not re.fullmatch(r"PROBE_FAILED_[A-Z_]{2,70}", status)):
            raise ValueError("Unknown AV probe status")
        if evidence["decoded"] and (status != "VIDEO_AUDIO_DECODED" or
                                    not evidence["video"] or not evidence["audio"]):
            raise ValueError("False decoded video/audio claim")
        return status

    def run(item):
        digest, url = item["url_sha256"], item["url"]
        if hashlib.sha256(url.encode()).hexdigest() != digest:
            raise ValueError("Candidate URL SHA mismatch")
        evidence = prober((digest, url))
        status = checked(evidence, digest)
        retried = status in TRANSIENT_RECHECK
        if retried:
            # Bounded same-batch retry; never attempt to bypass 403/404 or unsafe DNS.
            second = prober((digest, url))
            checked(second, digest)
            evidence = second
        return evidence, retried, retried and evidence["decoded"]

    with ThreadPoolExecutor(max_workers=workers) as executor:
        checks = list(executor.map(run, candidates))
    private, public, pages = [], [], set()
    for item, (evidence, retried, retry_recovered) in zip(candidates, checks):
        if evidence["decoded"]:
            pages.update(item["matched_blocked_pages"])
        row = {"url_sha256": item["url_sha256"],
               "matched_blocked_pages": item["matched_blocked_pages"],
               "source_ids": item["source_ids"], "status": evidence["status"],
               "video": evidence["video"], "audio": evidence["audio"],
               "decoded": evidence["decoded"], "ibo_device_verified": False,
               "transient_retry_attempted": retried,
               "transient_retry_recovered": retry_recovered}
        public.append(row)
        private.append({**row, "url": item["url"]})
    report = {
        "schema": 1, "kind": "V2_BLOCKED_OFFICIAL_REAL_FFPROBE_FFMPEG_AV",
        "source_count": len(SOURCES),
        "source_valid_count": source["configured_sources_valid"],
        "source_status": source["source_status"],
        "exact_target_page_count": len(TARGETS),
        "pages_with_exact_source_candidates": source["blocked_page_count_with_candidate"],
        "pages_without_exact_source_candidates": source["blocked_page_ids_without_exact_candidate"],
        "candidate_url_count": len(public), "candidate_urls_probed": len(public),
        "candidate_urls_not_probed": 0,
        "transient_retry_attempt_count": sum(x[1] for x in checks),
        "transient_retry_av_recovered_count": sum(x[2] for x in checks),
        "current_real_video_audio_decoded_count": sum(x["decoded"] for x in public),
        "current_real_video_audio_decoded_pages": sorted(pages),
        "current_real_video_audio_unverified_count": sum(not x["decoded"] for x in public),
        "av_status_counts": dict(sorted(Counter(x["status"] for x in public).items())),
        "candidates": public,
        "all_candidates_current_av_verified": bool(public) and all(x["decoded"] for x in public),
        "source_inventory_complete": source["configured_sources_valid"] == len(SOURCES),
        "external_official_http_access_errors_resolved": False,
        "spoken_language_verified": False, "ibo_device_verified": False,
        "protected_playlist_modified": False, "plaintext_url_in_public_report": False,
    }
    return report, private


def validate(report_path, sealed_path, *, require_complete=False):
    path, sealed = Path(report_path), Path(sealed_path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    envelope = json.loads(sealed.read_text(encoding="utf-8"))
    if (doc.get("schema") != 1 or
            doc.get("kind") != "V2_BLOCKED_OFFICIAL_REAL_FFPROBE_FFMPEG_AV" or
            any(doc.get(x) is not False for x in (
                "ibo_device_verified", "spoken_language_verified",
                "protected_playlist_modified", "plaintext_url_in_public_report",
                "external_official_http_access_errors_resolved"))):
        raise ValueError("Invalid protected AV report")
    if "://" in path.read_text(encoding="utf-8"):
        raise ValueError("Plaintext URL in public AV report")
    rows = doc.get("candidates")
    if (not isinstance(rows, list) or not rows or
            doc.get("candidate_url_count") != len(rows) or
            doc.get("candidate_urls_probed") != len(rows) or
            doc.get("candidate_urls_not_probed") != 0 or
            len({x.get("url_sha256") for x in rows}) != len(rows)):
        raise ValueError("Missing or duplicated AV evidence")
    for row in rows:
        if (not isinstance(row.get("url_sha256"), str) or
                not HEX.fullmatch(row["url_sha256"]) or
                any(x in row for x in ("url", "stream_url", "href")) or
                row.get("ibo_device_verified") is not False or
                any(type(row.get(x)) is not bool for x in ("video", "audio", "decoded")) or
                row["decoded"] and (not row["video"] or not row["audio"] or
                                    row.get("status") != "VIDEO_AUDIO_DECODED") or
                any(type(row.get(x)) is not bool for x in
                    ("transient_retry_attempted", "transient_retry_recovered")) or
                row["transient_retry_recovered"] and
                    (not row["transient_retry_attempted"] or not row["decoded"])):
            raise ValueError("False or malformed candidate proof")
    if (doc.get("current_real_video_audio_decoded_count") != sum(x["decoded"] for x in rows)
            or doc.get("current_real_video_audio_unverified_count") != sum(not x["decoded"] for x in rows)
            or doc.get("av_status_counts") != dict(sorted(Counter(x["status"] for x in rows).items()))
            or doc.get("transient_retry_attempt_count") != sum(x["transient_retry_attempted"] for x in rows)
            or doc.get("transient_retry_av_recovered_count") != sum(x["transient_retry_recovered"] for x in rows)):
        raise ValueError("Inconsistent AV aggregates")
    if (envelope.get("schema") != 1 or
            envelope.get("kind") != "RSA_OAEP_SHA256_AES256_GCM_ZLIB" or
            envelope.get("records_encrypted") != len(rows) or
            any(not isinstance(envelope.get(x), str) or not envelope[x]
                for x in ("nonce", "wrapped_key", "ciphertext"))):
        raise ValueError("Incomplete RSA-sealed stream evidence")
    complete = (doc.get("source_inventory_complete") is True and
                doc.get("source_valid_count") == len(SOURCES) and
                doc.get("pages_with_exact_source_candidates") == len(TARGETS))
    if require_complete and not complete:
        raise ValueError("Incomplete six-feed or five-channel source coverage")
    return {"real_av_probed": len(rows),
            "current_video_audio_decoded": doc["current_real_video_audio_decoded_count"],
            "current_video_audio_unverified": doc["current_real_video_audio_unverified_count"],
            "channel_pages_with_real_av": len(doc["current_real_video_audio_decoded_pages"]),
            "source_coverage_complete": complete, "ibo_device_verified": False,
            "transient_retry_attempt_count": doc["transient_retry_attempt_count"],
            "transient_retry_av_recovered_count": doc["transient_retry_av_recovered_count"]}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--probe-all", action="store_true")
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--require-complete", action="store_true")
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--sealed", type=Path, required=True)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    if args.probe_all == args.validate_only:
        p.error("Choose exactly one scan or validation mode")
    if args.validate_only:
        print("BLOCKED_OFFICIAL_REAL_AV_VALIDATION",
              json.dumps(validate(args.report, args.sealed, require_complete=args.require_complete),
                         sort_keys=True))
        return
    if (args.report.exists() or args.report.is_symlink() or
            args.sealed.exists() or args.sealed.is_symlink() or
            args.report.resolve() == args.sealed.resolve()):
        p.error("Refuse overwriting or overlapping evidence")
    report, private = scan(json.loads(CONFIG.read_text(encoding="utf-8")),
                           workers=args.workers)
    if not private:
        raise SystemExit("No exact candidates: no empty AV archive")
    seal_rows(private, PUBLIC_KEY, args.sealed)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("BLOCKED_OFFICIAL_REAL_AV", json.dumps({
        "source_count": report["source_count"],
        "source_valid_count": report["source_valid_count"],
        "candidate_url_count": report["candidate_url_count"],
        "candidate_urls_probed": report["candidate_urls_probed"],
        "current_real_video_audio_decoded_count": report["current_real_video_audio_decoded_count"],
        "current_real_video_audio_decoded_pages": report["current_real_video_audio_decoded_pages"],
        "current_real_video_audio_unverified_count": report["current_real_video_audio_unverified_count"],
        "transient_retry_attempt_count": report["transient_retry_attempt_count"],
        "transient_retry_av_recovered_count": report["transient_retry_av_recovered_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Merge TWO authenticated V2 FFmpeg AV batches into a PRIVATE IBO test M3U.

No automatic publication, production M3U change, source-address logging,
geo/DRM bypass, or device success claim. Both RSA sealed ZIP artifacts must
be downloaded separately and opened using the user's LOCAL private key.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from discover import ROOT, entries
from av_verified_sealed_ibo_export import select as select_api, esc, validate_destination
from traz_api_source_batch import public_stream

REPORTS = ROOT / "v2/reports"
API_REPORT = REPORTS / "ci/traz-api-av-acceptance.json"
API_SEALED = REPORTS / "ci/traz-api-av-evidence.sealed"
TARGET_REPORT = REPORTS / "ci/traz-missing-target-real-av.json"
TARGET_SEALED = REPORTS / "ci/traz-missing-target-av.sealed"
DEFAULT_OUT = REPORTS / "private-combined-traz-ibo-device-test.m3u8"


def checked_target(target, rows):
    """Check exact public FFmpeg proofs against every decrypted URL hash."""
    if (not isinstance(target, dict) or target.get("schema") != 1 or
            target.get("kind") != "V2_TR_AZ_MISSING_M3U_REAL_AV_READONLY" or
            target.get("policy") != "PUBLIC_SHA_ONLY_RSA_AES_SEALED_STREAM_URLS" or
            target.get("protected_playlist_modified") is not False or
            target.get("ibo_device_verified") is not False or
            target.get("old_historical_orphan_50_auto_recovered") is not False):
        raise ValueError("Invalid protected target AV report")
    public = target.get("results")
    if (not isinstance(public, list) or not isinstance(rows, list) or
            len(public) != target.get("candidate_hashes") or
            len(rows) != target.get("matched_current_source_hashes") or
            target.get("ffmpeg_probed") != len(rows)):
        raise ValueError("Incomplete or unbounded targeted AV evidence")
    expected = {}
    for item in public:
        if not isinstance(item, dict) or "url" in item:
            raise ValueError("Plaintext URL or invalid public result")
        digest = item.get("url_sha256")
        if (not isinstance(digest, str) or len(digest) != 64 or
                any(c not in "0123456789abcdef" for c in digest) or digest in expected or
                not isinstance(item.get("exact_channel_id"), str)):
            raise ValueError("Invalid or duplicate targeted URL hash")
        if item.get("decoded") is True and (item.get("status") != "VIDEO_AUDIO_DECODED"
                or item.get("video") is not True or item.get("audio") is not True):
            raise ValueError("False FFmpeg video and audio evidence")
        expected[digest] = item
    accepted, matched = [], set()
    for record in rows:
        if not isinstance(record, dict):
            raise ValueError("Invalid encrypted URL record")
        url, digest = record.get("url"), record.get("url_sha256")
        if (not isinstance(url, str) or any(ord(c) < 32 for c in url) or
                not public_stream(url) or
                hashlib.sha256(url.encode("utf-8")).hexdigest() != digest or
                digest in matched or digest not in expected):
            raise ValueError("Encrypted target URL hash mismatch")
        matched.add(digest)
        proof = expected[digest]
        if (proof.get("exact_channel_id") != record.get("channel_id") or
                proof.get("status") != record.get("ffmpeg_status") or
                proof.get("decoded") is not record.get("av_decoded")):
            raise ValueError("Encrypted target identity or AV evidence mismatch")
        if proof.get("decoded") is True:
            accepted.append((proof["exact_channel_id"], url))
    if matched != {h for h, item in expected.items()
                   if item.get("status") != "NOT_FOUND_IN_CURRENT_SOURCE"}:
        raise ValueError("Encrypted target inventory incomplete or inconsistent")
    if len(accepted) != target.get("real_video_audio_decoded_hashes"):
        raise ValueError("Target FFmpeg acceptance count mismatch")
    return accepted


def validated_shortterm_hashes(report, api):
    """Two short AV samples only prioritize test order; never prove 24h uptime."""
    if report is None:
        return set()
    if (not isinstance(report, dict) or report.get("schema") != 1
            or report.get("kind") != "TR_AZ_REAL_FFMPEG_HLS_CODEC_SHORT_TERM"
            or report.get("policy") != "PUBLIC_SHA_ONLY_NO_PLAYLIST_PROMOTION"
            or report.get("protected_playlist_modified") is not False
            or report.get("ibo_device_verified") is not False
            or report.get("short_interval_does_not_prove_24h_uptime") is not True):
        raise ValueError("Untrusted HLS short-term evidence")
    known = {r["url_sha256"]: sorted(r.get("channel_ids") or [])
             for r in api.get("streams",[]) if r.get("decoded") is True}
    if (len(known) != api.get("video_audio_decoded")
            or report.get("prior_av_verified_streams") != len(known)):
        raise ValueError("Short-term AV is not tied to this API acceptance run")
    rows = report.get("streams")
    if not isinstance(rows,list) or len(rows) != len(known):
        raise ValueError("Incomplete short-term AV evidence")
    seen = set()
    repeated = set()
    for row in rows:
        if not isinstance(row,dict) or "url" in row:
            raise ValueError("Plaintext or malformed stability row")
        digest = row.get("url_sha256")
        if (digest not in known or digest in seen
                or sorted(row.get("exact_channel_ids") or []) != known[digest]):
            raise ValueError("Cross-run AV URL/identity mismatch")
        seen.add(digest)
        if row.get("both_samples_decode") is True:
            if (row.get("av_round_1") != "VIDEO_AUDIO_DECODED"
                    or row.get("av_round_2") != "VIDEO_AUDIO_DECODED"):
                raise ValueError("False repeated FFmpeg video/audio evidence")
            repeated.add(digest)
    if (seen != set(known) or
            len(repeated) != report.get("both_short_av_samples_decoded")):
        raise ValueError("Incomplete repeated AV report")
    return repeated


def make_combined(api, api_rows, target, target_rows, shortterm=None):
    if (api.get("unprobed") != 0 or
            api.get("probed") != api.get("unique_url_candidates") or
            api.get("protected_playlist_modified") is not False):
        raise ValueError("API FFmpeg evidence coverage incomplete")
    repeated = validated_shortterm_hashes(shortterm, api)
    first_text, first_summary = select_api(api, api_rows)
    if api.get("video_audio_decoded") != sum(
            x.get("decoded") is True for x in api.get("streams", [])):
        raise ValueError("API dual AV results count mismatch")
    first = [(row.get("tvg_id"), row.get("url")) for row in entries(first_text)]
    if len(first) != first_summary["verified_entries"]:
        raise ValueError("Invalid API M3U parse or URL count")
    second = checked_target(target, target_rows)
    seen_url = {}
    by_id = {}
    unique_added = 0
    for source, rows in (("api", first), ("new", second)):
        for cid, url in rows:
            if (not isinstance(cid, str) or not cid or any(ord(c)<32 for c in cid)
                    or not isinstance(url, str) or not public_stream(url)
                    or any(ord(c)<32 for c in url)):
                raise ValueError("Unsafe exact identity or URL")
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            prev = seen_url.get(digest)
            if prev is not None:
                if prev != cid:
                    raise ValueError("Same URL claimed by different channel identity")
                continue
            seen_url[digest] = cid
            if source == "new":
                unique_added += 1
            by_id.setdefault(cid, []).append((url, source))
    if not by_id:
        raise ValueError("Refusing empty or fabricated device test list")
    lines = ["#EXTM3U"]
    for cid in sorted(by_id):
        # Prefer two short FFmpeg AV samples as the primary; keep all one-time
        # verified alternatives for device testing, without a 24h uptime claim.
        ordered = sorted(by_id[cid], key=lambda pair: (
            hashlib.sha256(pair[0].encode("utf-8")).hexdigest() not in repeated,
            pair[1] != "api"))
        for n, (url, source) in enumerate(ordered):
            digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
            group = ("TEST - IKI KISA AV ORNEGI, CIHAZ BEKLIYOR"
                     if n == 0 and digest in repeated else
                     "TEST - AV KANITLI, IBO CIHAZ BEKLIYOR" if n == 0 else
                     "TEST - ALTERNATIF AV, IBO CIHAZ BEKLIYOR")
            display = esc(cid) + (" [ALT]" if n else "")
            lines.extend(['#EXTINF:-1 tvg-id="' + esc(cid) +
                          '" group-title="' + group + '",' + display, url])
    summary = {
        "policy": "PRIVATE_ONLY_TWO_RSA_VERIFIED_BATCHES_NO_MAIN_WRITES",
        "device_test_entries": len(seen_url),
        "primary_exact_channel_ids": len(by_id),
        "alternative_av_stream_addresses": len(seen_url) - len(by_id),
        "prior_api_verified_entries": len(first),
        "new_target_verified_entries": len(second),
        "target_new_nonduplicate_addresses": unique_added,
        "duplicate_addresses_deduplicated": len(first) + len(second) - len(seen_url),
        "ibo_device_verified": False,
        "spoken_language_verified": False,
        "sweden_access_verified": False,
        "long_term_uptime_verified": False,
        "protected_playlist_modified": False,
        "unverified_streams_exported": 0,
        "shortterm_two_sample_hashes": len(repeated),
        "long_term_reliability_claimed": False,
    }
    return "\n".join(lines) + "\n", summary


def check_envelope(report_path, sealed_path, label):
    for path in (report_path, sealed_path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 20_000_000:
            raise ValueError("Missing or unsafe " + label + " evidence file")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    evidence = report.get("encrypted_evidence" if label == "API" else
                          "rsa_sealed_matches")
    if not isinstance(evidence, dict):
        raise ValueError("Missing " + label + " RSA manifest")
    raw = sealed_path.read_bytes()
    number = evidence.get("records") if label == "API" else evidence.get("records_encrypted")
    if evidence.get("sha256") != hashlib.sha256(raw).hexdigest() or number is None:
        raise ValueError("Missing " + label + " RSA digest or count")
    count = evidence["records"] if label == "API" else evidence["records_encrypted"]
    required = report.get("unique_url_candidates") if label == "API" else report.get("matched_current_source_hashes")
    if count != required or evidence.get("sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("RSA envelope count or checksum mismatch")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-key", required=True, type=Path)
    p.add_argument("--api-report", type=Path, default=API_REPORT)
    p.add_argument("--api-sealed", type=Path, default=API_SEALED)
    p.add_argument("--target-report", type=Path, default=TARGET_REPORT)
    p.add_argument("--target-sealed", type=Path, default=TARGET_SEALED)
    p.add_argument("--shortterm-report", type=Path, default=None,
                   help="Optional public hash-only two-sample FFmpeg evidence")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()
    validate_destination(args.out)
    if args.private_key.is_symlink() or not args.private_key.is_file():
        raise SystemExit("A local, non-symlink RSA private key is required")
    api = check_envelope(args.api_report, args.api_sealed, "API")
    target = check_envelope(args.target_report, args.target_sealed, "TARGET")
    from stage3_sealed_export import open_rows
    shortterm = None
    if args.shortterm_report is not None:
        path = args.shortterm_report
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 20_000_000:
            raise SystemExit("Unsafe two-sample evidence path")
        shortterm = json.loads(path.read_text(encoding="utf-8"))
    text, summary = make_combined(
        api, open_rows(args.api_sealed, args.private_key),
        target, open_rows(args.target_sealed, args.private_key), shortterm=shortterm)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(args.out, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(text)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

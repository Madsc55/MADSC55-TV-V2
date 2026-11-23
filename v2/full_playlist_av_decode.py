#!/usr/bin/env python3
"""SHA-bound read-only decoded A/V sampling of every canonical URL.

Network resources are downloaded through the existing pinned-public-IP sampler.
FFmpeg only receives local MPEG-TS bytes through stdin with a pipe-only
protocol allowlist: playlist URLs and HLS subresources never reach FFmpeg.
No channel deletion, category mutation or working/dead status is authorized.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from discover import ROOT
from full_playlist_url_audit import (
    MAX_SHARDS, SHARD_SIZE, POLICY as PRIOR_POLICY,
    index_playlist, write_json_atomic
)
from shared_url_safe_probe import (
    SafeFetchError, bounded_get, sample_transport_stream, program_table
)

PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
POLICY = "READ_ONLY_LOCAL_FFMPEG_AV_DECODE_V1_NO_CHANNEL_MUTATIONS"
SOURCE_RUN_ID = 45232887355
MAX_SAMPLE = 3_000_000
WORKERS = 4
PROCESS_TIMEOUT = 9


def decoded_frame(sample, stream_type, executable, runner=subprocess.run):
    """True only after FFmpeg emits a decoded frame checksum from local bytes."""
    assert stream_type in ("v", "a")
    cmd = [
        executable, "-nostdin", "-hide_banner", "-loglevel", "error",
        "-threads", "1", "-filter_threads", "1",
        "-protocol_whitelist", "pipe",
        "-f", "mpegts", "-i", "pipe:0",
        "-map", "0:" + stream_type + ":0",
        "-frames:" + stream_type, "1",
        "-f", "framemd5", "pipe:1",
    ]
    try:
        out = runner(
            cmd, input=sample, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=PROCESS_TIMEOUT, check=False
        )
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    if out.returncode:
        return False
    # FFmpeg's framemd5 line has 6 CSV fields. Comments/header never count.
    return any(
        len(line.split(b",")) == 6 and all(part.strip() for part in line.split(b","))
        for line in out.stdout.splitlines()
        if line.strip() and not line.lstrip().startswith(b"#")
    )


def decode_url(url):
    try:
        data = sample_transport_stream(
            url, fetch=lambda target, size: bounded_get(
                target, min(size, MAX_SAMPLE), timeout=6
            ))
    except SafeFetchError as exc:
        return {
            "status": str(exc), "sample_bytes": 0,
            "decoded_video": False, "decoded_audio": False,
            "broadcaster_identity_verified": False
        }
    except Exception:
        # Error details may contain signed URL tokens: never log them.
        return {
            "status": "UNEXPECTED_FETCH_ERROR", "sample_bytes": 0,
            "decoded_video": False, "decoded_audio": False,
            "broadcaster_identity_verified": False
        }

    programs = program_table(data)
    executable = shutil.which("ffmpeg")
    if not executable:
        return {
            "status": "DECODER_UNAVAILABLE", "sample_bytes": len(data),
            "decoded_video": False, "decoded_audio": False,
            "broadcaster_identity_verified": False,
            "mpegts_program_count": len(programs)
        }
    video = decoded_frame(data, "v", executable)
    audio = decoded_frame(data, "a", executable)
    status = (
        "VIDEO_AND_AUDIO_DECODED" if video and audio
        else "VIDEO_ONLY_DECODED" if video
        else "AUDIO_ONLY_DECODED" if audio
        else "NO_DECODED_FRAME_IN_SAMPLE"
    )
    return {
        "status": status,
        "sample_bytes": len(data),
        "decoded_video": video,
        "decoded_audio": audio,
        "mpegts_program_count": len(programs),
        "broadcaster_identity_verified": False,
    }


def validate_prior(text, shard, previous):
    """Accept only the exact SHA- and URL-bound previous completed shard."""
    records, ordered = index_playlist(text)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    selected = ordered[shard * SHARD_SIZE:(shard + 1) * SHARD_SIZE]
    hashes = {digest for digest, _ in selected}
    if (
        not isinstance(previous, dict)
        or previous.get("policy") != PRIOR_POLICY
        or previous.get("playlist_sha256") != sha
        or previous.get("playlist_records") != records
        or previous.get("unique_url_count") != len(ordered)
        or previous.get("shard") != shard
        or previous.get("shard_size") != SHARD_SIZE
        or previous.get("complete") is not True
        or not isinstance(previous.get("results"), list)
    ):
        raise ValueError("Previous shard has an incorrect playlist or scope")
    old = {x.get("url_sha256"): x for x in previous["results"]
           if isinstance(x, dict)}
    if (
        len(old) != len(previous["results"])
        or set(old) != hashes
        or len(old) != len(selected)
    ):
        raise ValueError("Previous URL hashes are incomplete or duplicated")
    return records, ordered, selected, old, sha


def batch(text, shard, previous, probe=decode_url, checkpoint=None):
    if type(shard) is not int or not 0 <= shard < MAX_SHARDS:
        raise ValueError("Invalid shard")
    records, ordered, selected, old, sha = validate_prior(text, shard, previous)
    payload = {
        "schema": 1, "policy": POLICY, "source_run_id": SOURCE_RUN_ID,
        "playlist_sha256": sha,
        "shard": shard, "shard_size": SHARD_SIZE,
        "channel_records": records, "unique_url_count": len(ordered),
        "expected_url_count": len(selected),
        "attempts": [], "complete": False
    }
    if checkpoint:
        write_json_atomic(checkpoint, payload)

    # The unresolved URLs that concerned the user go first within each shard;
    # previous metadata-success URLs are still subsequently decoded.
    selected = sorted(selected, key=lambda item: (
        old[item[0]]["evidence"]["status"] in (
            "ONE_VIDEO_SERVICE_OBSERVED",
            "MULTIPLE_VIDEO_SERVICE_PIDS_OBSERVED",
        ), item[0]
    ))

    def task(item):
        digest, channel = item
        old_evidence = old[digest]["evidence"]
        outcome = probe(channel["url"])
        # No URL, token, full remote response or FFmpeg stderr in reports.
        return {
            "url_sha256": digest,
            "previous_status": old_evidence["status"],
            "channel_records": channel["records"],
            "decode": outcome,
            "safe_to_remove_or_merge": False,
            "verified_broadcaster_identity": False,
        }

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        pending = [pool.submit(task, item) for item in selected]
        for future in as_completed(pending):
            payload["attempts"].append(future.result())
            if checkpoint and len(payload["attempts"]) % 20 == 0:
                write_json_atomic(checkpoint, payload)

    payload["attempts"].sort(key=lambda row: row["url_sha256"])
    payload["complete"] = len(payload["attempts"]) == len(selected)
    payload["decode_status_counts"] = dict(sorted(
        Counter(x["decode"]["status"] for x in payload["attempts"]).items()
    ))
    if checkpoint:
        write_json_atomic(checkpoint, payload)
    return payload


def consolidate(text, shards):
    """Summarize all shards only if every URL has exactly one A/V attempt."""
    records, ordered = index_playlist(text)
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    expected = {digest for digest, _ in ordered}
    seen, seen_shards, issues = set(), set(), []
    counts = Counter()
    old_counts = Counter()
    both = video = audio = 0
    for report in shards:
        if not isinstance(report, dict) or (
            report.get("policy") != POLICY
            or report.get("source_run_id") != SOURCE_RUN_ID
            or report.get("playlist_sha256") != sha
            or report.get("channel_records") != records
            or report.get("unique_url_count") != len(ordered)
            or report.get("shard_size") != SHARD_SIZE
        ):
            issues.append("STALE_OR_INVALID_SHARD")
            continue
        idx = report.get("shard")
        if type(idx) is not int or idx not in range(MAX_SHARDS) or idx in seen_shards:
            issues.append("DUPLICATE_OR_INVALID_SHARD")
            continue
        seen_shards.add(idx)
        target = {digest for digest, _ in
                  ordered[idx * SHARD_SIZE:(idx + 1) * SHARD_SIZE]}
        items = report.get("attempts")
        if not isinstance(items, list):
            issues.append("MISSING_RESULTS")
            continue
        hashes = [x.get("url_sha256") for x in items]
        if (report.get("complete") is not True
                or len(hashes) != len(target)
                or len(hashes) != len(set(hashes))
                or set(hashes) != target):
            issues.append("INCOMPLETE_SHARD")
            continue
        seen.update(hashes)
        for item in items:
            d = item["decode"]
            counts[d["status"]] += 1
            old_counts[item["previous_status"]] += 1
            both += d.get("decoded_video") is True and d.get("decoded_audio") is True
            video += d.get("decoded_video") is True
            audio += d.get("decoded_audio") is True

    if seen_shards != set(range(MAX_SHARDS)):
        issues.append("MISSING_SHARDS")
    if seen != expected:
        issues.append("MISSING_URL_ATTEMPTS")

    return {
        "schema": 1, "policy": POLICY,
        "source_run_id": SOURCE_RUN_ID, "playlist_sha256": sha,
        "playlist_channel_records": records,
        "unique_urls": len(expected),
        "attempted_urls": len(seen),
        "missing_urls": len(expected - seen),
        "shards_reported": len(seen_shards),
        "shards_expected": MAX_SHARDS,
        "decoded_video_urls": video,
        "decoded_audio_urls": audio,
        "decoded_video_and_audio_urls": both,
        "decode_status_counts": dict(sorted(counts.items())),
        "previous_metadata_status_counts": dict(sorted(old_counts.items())),
        "broadcaster_identity_verified": False,
        "no_channels_mutated": True,
        "complete": not issues,
        "issues": sorted(set(issues)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int)
    ap.add_argument("--previous-report", type=Path)
    ap.add_argument("--merge-dir", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    original = PLAYLIST.read_bytes()
    text = original.decode("utf-8-sig")
    if args.merge_dir:
        data = [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(args.merge_dir.rglob("decode-*.json"))]
        output = consolidate(text, data)
    else:
        if args.shard is None or args.previous_report is None:
            ap.error("--shard and --previous-report are required")
        prior = json.loads(args.previous_report.read_text(encoding="utf-8"))
        output = batch(text, args.shard, prior, checkpoint=args.output)
    write_json_atomic(args.output, output)
    if PLAYLIST.read_bytes() != original:
        raise SystemExit("Canonical playlist mutated during read-only scan")
    print(json.dumps({
        "complete": output["complete"],
        "shard": output.get("shard"),
        "attempts": len(output.get("attempts", [])),
        "status_counts": output.get("decode_status_counts", {}),
        "missing_urls": output.get("missing_urls", 0),
    }, ensure_ascii=False, sort_keys=True))
    if not output["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

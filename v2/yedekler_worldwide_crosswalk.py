#!/usr/bin/env python3
"""Read-only SHA-256 crosswalk of the original 18,074 YEDEKLER inventory.

Downloads one exact, historical worldwide evidence artifact. Never probes streams,
writes playlists, or promotes historical evidence to a fresh verification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

SOURCE_RUN_ID = 42216075104
SOURCE_RUN_HEAD_SHA = "062cf6ae9783803bb45b06efd4e877bcb6333f8e"
SOURCE_ARTIFACT_ID = 13524765368
SOURCE_ARTIFACT_NAME = "v2-grouped-av-evidence-42216075104"
SOURCE_ARTIFACT_DIGEST = "sha256:6bec426291330c6b4b305e2871b721a25c44583f892c14d893472cdc3e80f87d"
WORLDWIDE_REPORT_SHA256 = "41d96419250fc466786753b7d889503d0d4fc83fceb562d47eaf614a99624f0d"
HISTORICAL_CROSSWALK_SHA256 = "a108f9009a8f32d65920ec61e85c9a023f9e7aa169ba2aa858eceda2cc0551fe"
HISTORICAL_ARCHIVE_BLOB_SHA1 = "57d55f3a339099e741b33ecbb55fc0ef809d1d61"
EXPECTED_ARCHIVE_SHA256 = "d72ac1e6bf27982862e23e06957222a9abaf7b03f0fab01edc2147144b50be5c"
EXPECTED_ARCHIVE_TOTAL = 18074
EXPECTED_BATCH_SIZE = 2500
EXPECTED_MAIN_INVENTORY = {
    "YEDEKLER": 1792, "ANA": 15574, "TURK": 424,
    "YABANCI": 284, "OTHER": 838, "TOTAL": 18912,
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _entries(raw, parse):
    _, blocks = parse(raw)
    rows = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 2:
            raise ValueError("Malformed archive record")
        url = lines[-1].strip()
        if not url.startswith(("http://", "https://")):
            raise ValueError("Archive record has a non-HTTP URL")
        rows.append((block, url, digest(url.encode("utf-8"))))
    return rows


def build_crosswalk(archive_raw, main_raw, state, worldwide, historical,
                    *, expected_archive_sha256=None, expected_archive_total=None,
                    expected_batch_size=2500, expected_main_inventory=None,
                    expected_worldwide_count=35327, expected_worldwide_av_count=13884):
    try:
        from .ibo_single_playlist_transfer import parse, category, inventory
    except ImportError:
        from ibo_single_playlist_transfer import parse, category, inventory

    archive_sha = digest(archive_raw)
    if expected_archive_sha256 and archive_sha != expected_archive_sha256:
        raise ValueError("Historical 18,074 archive SHA-256 mismatch")
    if state.get("source_sha256") != archive_sha:
        raise ValueError("Batch state does not bind to the historical archive")
    if type(state.get("total")) is not int:
        raise ValueError("Invalid historical archive total")
    if expected_archive_total is not None and state["total"] != expected_archive_total:
        raise ValueError("Historical archive total mismatch")

    archive_rows = _entries(archive_raw, parse)
    if len(archive_rows) != state["total"]:
        raise ValueError("Historical archive record count mismatch")
    archive_hashes = [row[2] for row in archive_rows]
    if len(set(archive_hashes)) != len(archive_hashes):
        raise ValueError("Duplicate URL hash in historical archive")

    statuses = state.get("status")
    if not isinstance(statuses, dict) or len(statuses) != expected_batch_size:
        raise ValueError("Incomplete first-batch status map")
    expected_ordinals = {str(i) for i in range(1, expected_batch_size + 1)}
    if set(statuses) != expected_ordinals:
        raise ValueError("First-batch status ordinals are incomplete")
    if any(value not in {"TEST", "TURK", "YABANCI"} for value in statuses.values()):
        raise ValueError("Unknown first-batch status")
    state_counts = {name: sum(value == name for value in statuses.values())
                    for name in ("TEST", "TURK", "YABANCI")}
    if sum(state_counts.values()) != expected_batch_size:
        raise ValueError("First-batch status count mismatch")

    _, main_blocks = parse(main_raw)
    main_rows = []
    main_by_hash = {}
    for block in main_blocks:
        lines = block.splitlines()
        if len(lines) < 2:
            raise ValueError("Malformed canonical playlist record")
        url = lines[-1].strip()
        url_hash = digest(url.encode("utf-8"))
        if url_hash in main_by_hash:
            raise ValueError("Duplicate URL hash in canonical playlist")
        main_by_hash[url_hash] = block
        main_rows.append((block, url_hash, category(lines[0])))
    main_counts = inventory(main_raw)
    if expected_main_inventory is not None and main_counts != expected_main_inventory:
        raise ValueError("Canonical main playlist inventory changed")
    if len(main_rows) != main_counts["TOTAL"]:
        raise ValueError("Canonical playlist record count mismatch")

    expected_active = []
    for ordinal, (_, _, url_hash) in enumerate(archive_rows, 1):
        block = main_by_hash.get(url_hash)
        if block is None:
            raise ValueError("Historical archive URL missing from canonical main playlist")
        actual_category = category(block.splitlines()[0])
        if ordinal <= expected_batch_size:
            status = statuses[str(ordinal)]
            expected_category = {"TEST": "YEDEKLER", "TURK": "TURK",
                                 "YABANCI": "YABANCI"}[status]
            if status == "TEST":
                expected_active.append(url_hash)
        else:
            status = "ANA"
            expected_category = "ANA"
        if actual_category != expected_category:
            raise ValueError("Canonical category disagrees with immutable batch state at ordinal %d" % ordinal)

    actual_active = [url_hash for _, url_hash, group in main_rows if group == "YEDEKLER"]
    actual_active_set = set(actual_active)
    if actual_active_set != set(expected_active) or len(actual_active) != len(expected_active):
        raise ValueError("Current YEDEKLER does not match the first-batch TEST identity set")

    candidates = worldwide.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("Worldwide candidate list missing")
    if len(candidates) != worldwide.get("unique_url_candidates"):
        raise ValueError("Worldwide candidate count mismatch")
    candidate_by_hash = {}
    for item in candidates:
        if not isinstance(item, dict):
            raise ValueError("Invalid worldwide candidate")
        url_hash = item.get("url_sha256")
        if not isinstance(url_hash, str) or len(url_hash) != 64:
            raise ValueError("Invalid worldwide URL hash")
        if url_hash in candidate_by_hash:
            raise ValueError("Duplicate worldwide URL hash")
        candidate_by_hash[url_hash] = item
    if (worldwide.get("audio_video_decoded") != expected_worldwide_av_count
            or len(candidates) != expected_worldwide_count):
        raise ValueError("Unexpected historical worldwide report scope/counts")

    hist_matches = historical.get("historical_match_url_sha256")
    hist_decoded = historical.get("historical_decoded_url_sha256")
    if not isinstance(hist_matches, list) or not isinstance(hist_decoded, list):
        raise ValueError("Historical AV crosswalk hash lists missing")
    hist_match_set, hist_decoded_set = set(hist_matches), set(hist_decoded)
    if len(hist_match_set) != len(hist_matches) or len(hist_decoded_set) != len(hist_decoded):
        raise ValueError("Duplicate hash in historical crosswalk")
    if not hist_decoded_set <= hist_match_set:
        raise ValueError("Historical AV hashes are not a subset of exact matches")

    rows = []
    counts = {
        "archive_total": len(archive_rows),
        "worldwide_exact_hash_matches": 0,
        "worldwide_not_found": 0,
        "source_run_av_decoded": 0,
        "prior_run_hash_only_matches": 0,
        "matched_but_not_av_decoded": 0,
        "historical_exact_hash_matches": 0,
        "historical_av_decoded_matches": 0,
        "current_yedekler_total": len(actual_active),
        "current_yedekler_worldwide_matches": 0,
        "current_yedekler_source_run_av_decoded": 0,
        "current_yedekler_prior_run_hash_only": 0,
        "current_yedekler_not_in_worldwide_report": 0,
    }
    for ordinal, (_, _, url_hash) in enumerate(archive_rows, 1):
        item = candidate_by_hash.get(url_hash)
        source_run_av = bool(
            item
            and item.get("evidence_origin") == "CURRENT_RUN_FFPROBE_FFMPEG"
            and item.get("status") == "VIDEO_AUDIO_DECODED"
            and item.get("decoded") is True
            and item.get("audio") is True
            and item.get("video") is True
        )
        prior_only = bool(item and item.get("evidence_origin") == "PRIOR_RUN_HASH_ONLY_NOT_FRESH")
        hist_match = url_hash in hist_match_set
        hist_av = url_hash in hist_decoded_set
        if item:
            counts["worldwide_exact_hash_matches"] += 1
            if source_run_av:
                counts["source_run_av_decoded"] += 1
            elif prior_only:
                counts["prior_run_hash_only_matches"] += 1
            else:
                counts["matched_but_not_av_decoded"] += 1
        else:
            counts["worldwide_not_found"] += 1
        if hist_match:
            counts["historical_exact_hash_matches"] += 1
        if hist_av:
            counts["historical_av_decoded_matches"] += 1
        if url_hash in actual_active_set:
            if item:
                counts["current_yedekler_worldwide_matches"] += 1
                if source_run_av:
                    counts["current_yedekler_source_run_av_decoded"] += 1
                if prior_only:
                    counts["current_yedekler_prior_run_hash_only"] += 1
            else:
                counts["current_yedekler_not_in_worldwide_report"] += 1
        rows.append({
            "ordinal": ordinal,
            "url_sha256": url_hash,
            "current_category": category(main_by_hash[url_hash].splitlines()[0]),
            "first_batch_status": statuses.get(str(ordinal)) if ordinal <= expected_batch_size else "ANA",
            "worldwide_status": item.get("status") if item else "NOT_IN_WORLDWIDE_REPORT",
            "worldwide_evidence_origin": item.get("evidence_origin") if item else None,
            "source_run_av_decoded": source_run_av,
            "historical_exact_hash_match": hist_match,
            "historical_av_decoded": hist_av,
        })
    if counts["worldwide_exact_hash_matches"] + counts["worldwide_not_found"] != len(archive_rows):
        raise ValueError("Crosswalk count reconciliation failed")
    summary = {
        "schema_version": 1,
        "policy": "READ_ONLY_HASH_ONLY_NO_STREAM_PROBES_NO_PLAYLIST_WRITES",
        "source_run_id": SOURCE_RUN_ID,
        "source_run_head_sha": SOURCE_RUN_HEAD_SHA,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_name": SOURCE_ARTIFACT_NAME,
        "source_artifact_digest": SOURCE_ARTIFACT_DIGEST,
        "worldwide_report_file_sha256": WORLDWIDE_REPORT_SHA256,
        "worldwide_report_canonical_sha256": digest(json.dumps(worldwide, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "historical_crosswalk_file_sha256": HISTORICAL_CROSSWALK_SHA256,
        "historical_crosswalk_canonical_sha256": digest(json.dumps(historical, ensure_ascii=False,
            sort_keys=True, separators=(",", ":")).encode("utf-8")),
        "historical_archive_sha256": archive_sha,
        "canonical_playlist_sha256": digest(main_raw),
        "batch_state_counts": state_counts,
        "main_inventory": main_counts,
        "counts": counts,
        "worldwide_report_summary": {
            "unique_url_candidates": len(candidates),
            "audio_video_decoded": worldwide["audio_video_decoded"],
            "spoken_language_verified": worldwide.get("spoken_language_verified"),
            "ibo_player_verified": worldwide.get("ibo_player_verified"),
            "protected_main_playlist_modified": worldwide.get("protected_main_playlist_modified"),
        },
        "historical_crosswalk_summary": {
            "exact_hash_matches": len(hist_match_set),
            "av_decoded_hashes": len(hist_decoded_set),
            "ibo_device_verified": historical.get("ibo_device_verified"),
            "protected_playlist_modified": historical.get("protected_playlist_modified"),
        },
        "new_scan_started": False,
        "playlist_written": False,
        "raw_urls_in_report": False,
    }
    return summary, {"schema_version": 1, "entries": rows}


def _gh_json(repo, endpoint):
    result = subprocess.run(["gh", "api", endpoint], capture_output=True,
                            text=True, timeout=30, check=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--archive-blob", type=Path)
    parser.add_argument("--playlist", type=Path,
                        default=Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"))
    parser.add_argument("--state", type=Path, default=Path("v2/yedekler_batch/state.json"))
    args = parser.parse_args()
    if args.output_dir.exists():
        raise SystemExit("Refusing to overwrite existing output directory")
    repo = os.environ.get("GITHUB_REPOSITORY", "Madsc55/MADSC55-TV-V2")
    if not os.environ.get("GH_TOKEN"):
        raise SystemExit("GH_TOKEN is required for exact historical artifact retrieval")
    run = _gh_json(repo, f"repos/{repo}/actions/runs/{SOURCE_RUN_ID}")
    if (run.get("head_sha") != SOURCE_RUN_HEAD_SHA or run.get("conclusion") != "success"
            or run.get("status") != "completed"):
        raise SystemExit("Historical source run identity/status mismatch")
    artifacts = _gh_json(repo, f"repos/{repo}/actions/runs/{SOURCE_RUN_ID}/artifacts?per_page=100")
    matches = [x for x in artifacts.get("artifacts", [])
               if x.get("id") == SOURCE_ARTIFACT_ID and x.get("name") == SOURCE_ARTIFACT_NAME]
    if len(matches) != 1 or matches[0].get("expired") or matches[0].get("digest") != SOURCE_ARTIFACT_DIGEST:
        raise SystemExit("Exact historical source artifact is missing, expired or changed")
    if args.artifact_dir is None:
        with tempfile.TemporaryDirectory(prefix="v2-stage5-worldwide-") as directory:
            artifact_dir = Path(directory)
            subprocess.run(["gh", "run", "download", str(SOURCE_RUN_ID), "--repo", repo,
                            "--name", SOURCE_ARTIFACT_NAME, "--dir", str(artifact_dir)],
                           check=True, timeout=120)
            _run_with_inputs(args, artifact_dir)
    else:
        _run_with_inputs(args, args.artifact_dir)


def _run_with_inputs(args, artifact_dir):
    try:
        from .ibo_single_playlist_transfer import sha
    except ImportError:
        from ibo_single_playlist_transfer import sha
    report_path = artifact_dir / "final-worldwide-acceptance.json"
    historical_path = artifact_dir / "historical-worldwide-av-crosswalk.json"
    if not report_path.is_file() or not historical_path.is_file():
        raise SystemExit("Exact worldwide evidence files missing from source artifact")
    report_raw, historical_raw = report_path.read_bytes(), historical_path.read_bytes()
    if digest(report_raw) != WORLDWIDE_REPORT_SHA256:
        raise SystemExit("Worldwide source report SHA-256 mismatch")
    if digest(historical_raw) != HISTORICAL_CROSSWALK_SHA256:
        raise SystemExit("Historical crosswalk SHA-256 mismatch")
    if args.archive_blob is None:
        result = subprocess.run(["git", "cat-file", "blob", HISTORICAL_ARCHIVE_BLOB_SHA1],
                                capture_output=True, check=True, timeout=30)
        archive_raw = result.stdout
    else:
        archive_raw = args.archive_blob.read_bytes()
    summary, crosswalk = build_crosswalk(
        archive_raw, args.playlist.read_bytes(),
        json.loads(args.state.read_text(encoding="utf-8")),
        json.loads(report_raw), json.loads(historical_raw),
        expected_archive_sha256=EXPECTED_ARCHIVE_SHA256,
        expected_archive_total=EXPECTED_ARCHIVE_TOTAL,
        expected_batch_size=EXPECTED_BATCH_SIZE,
        expected_main_inventory=EXPECTED_MAIN_INVENTORY,
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    (args.output_dir / "crosswalk.json").write_text(
        json.dumps(crosswalk, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8")
    print(json.dumps({"counts": summary["counts"], "batch_state_counts": summary["batch_state_counts"],
                      "main_inventory": summary["main_inventory"],
                      "source_run_id": SOURCE_RUN_ID, "new_scan_started": False,
                      "playlist_written": False}, sort_keys=True))


if __name__ == "__main__":
    main()

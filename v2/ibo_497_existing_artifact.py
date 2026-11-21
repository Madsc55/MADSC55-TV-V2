#!/usr/bin/env python3
"""#497: import one exact historical Actions artifact; never probe or write a playlist."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from ibo_497_audit_adapter import convert
from ibo_test_result_reconcile import digest, reconcile
from ibo_single_playlist_transfer import category, parse

SOURCE_RUN_ID = 44640007709
SOURCE_HEAD_SHA = "1e8bd6d46762366f151e1270cc767f598c8e63e8"
SOURCE_ARTIFACT_ID = 14587983768
SOURCE_ARTIFACT_NAME = "yedekler-av-audit"
SOURCE_REPORT_NAME = "yedekler_av_audit.json"
SOURCE_PLAYLIST_SHA256 = "eee260cce3926caff18238f9583958b40475e362ce7650fb7fac51a66a84ee1c"
SOURCE_REPORT_FILE_SHA256 = "30de600eca7d8e3140f423bb3fc248dc2f57df6ff031b0bf97276a9a861dba2c"
CANONICAL_PLAYLIST = "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def yedekler_blocks(raw):
    return [block for block in parse(raw)[1]
            if category(block.split("\n", 1)[0]) == "YEDEKLER"]


def build_preview(source_raw, current_raw, audit, run_id, report_file_sha256):
    """Bind the original audit to its source playlist, then map it only if current YEDEKLER blocks are byte-identical."""
    if run_id != SOURCE_RUN_ID:
        raise ValueError("Unexpected source Actions run")
    if digest(source_raw) != SOURCE_PLAYLIST_SHA256:
        raise ValueError("Historical source playlist SHA-256 mismatch")
    source_evidence, canonical_evidence_sha = convert(source_raw, audit, run_id)
    source_blocks = yedekler_blocks(source_raw)
    current_blocks = yedekler_blocks(current_raw)
    if len(source_blocks) != 1792 or len(current_blocks) != 1792:
        raise ValueError("Expected exactly 1792 source and current YEDEKLER blocks")
    if source_blocks != current_blocks:
        raise ValueError("Current YEDEKLER records/order differ from the historical evidence source")
    # Other playlist categories may legitimately have changed since the audit.
    # Rebind only after proving every YEDEKLER EXTINF+URL block is byte-identical and ordered.
    source_evidence["playlist_sha256"] = digest(current_raw)
    canonical = json.dumps(source_evidence, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    preview, manifest = reconcile(current_raw, source_evidence,
                                  digest(current_raw), digest(canonical))
    if preview != current_raw:
        raise ValueError("Preview unexpectedly changes the canonical playlist")
    if manifest["counts"] != {"verified": 1107, "uncertain": 685}:
        raise ValueError("Unexpected verified/uncertain totals")
    manifest.update({
        "source_run_id": run_id,
        "source_head_sha": SOURCE_HEAD_SHA,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_name": SOURCE_ARTIFACT_NAME,
        "source_report_file_sha256": report_file_sha256,
        "source_report_canonical_sha256": canonical_evidence_sha,
        "source_playlist_sha256": SOURCE_PLAYLIST_SHA256,
        "current_playlist_sha256": digest(current_raw),
        "source_yedekler_count": len(source_blocks),
        "current_yedekler_count": len(current_blocks),
        "ordered_yedekler_blocks_identical": True,
        "preview_only": True,
        "new_scan_started": False,
        "canonical_playlist_written": False,
    })
    return preview, manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--playlist", type=Path, default=Path(CANONICAL_PLAYLIST))
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    if a.playlist.name != CANONICAL_PLAYLIST:
        p.error("Only canonical main playlist is supported")
    if a.output_dir.exists():
        p.error("Output directory must not exist (no overwrite)")
    if not os.environ.get("GH_TOKEN"):
        raise ValueError("GH_TOKEN required for authenticated artifact retrieval")
    repo = os.environ.get("GITHUB_REPOSITORY", "Madsc55/MADSC55-TV-V2")

    run = json.loads(gh("run", "view", str(SOURCE_RUN_ID), "--repo", repo,
                        "--json", "status,conclusion,headSha,event,workflowName"))
    if (run.get("status") != "completed" or run.get("conclusion") != "success" or
            run.get("headSha") != SOURCE_HEAD_SHA or run.get("event") != "workflow_dispatch" or
            run.get("workflowName") != "V2 Full Decoder Verification (manual, read-only)"):
        raise ValueError("Historical source run identity/status mismatch")

    artifacts = json.loads(gh("api", f"repos/{repo}/actions/runs/{SOURCE_RUN_ID}/artifacts"))
    matches = [x for x in artifacts.get("artifacts", [])
               if x.get("id") == SOURCE_ARTIFACT_ID and
               x.get("name") == SOURCE_ARTIFACT_NAME and not x.get("expired")]
    if len(matches) != 1:
        raise ValueError("Exact original artifact missing, expired, or ambiguous")

    with tempfile.TemporaryDirectory(prefix="v2-497-source-") as d:
        gh("run", "download", str(SOURCE_RUN_ID), "--repo", repo,
           "--name", SOURCE_ARTIFACT_NAME, "--dir", d)
        report_path = Path(d) / SOURCE_REPORT_NAME
        if report_path.is_symlink() or not report_path.is_file():
            raise ValueError("Exact historical report file missing")
        report_bytes = report_path.read_bytes()
        report_sha = digest(report_bytes)
        if report_sha != SOURCE_REPORT_FILE_SHA256:
            raise ValueError("Downloaded original report SHA-256 mismatch")
        audit = json.loads(report_bytes)
        source_raw = subprocess.run(
            ["git", "show", f"{SOURCE_HEAD_SHA}:{CANONICAL_PLAYLIST}"],
            check=True, capture_output=True).stdout
        current_raw = a.playlist.read_bytes()
        preview, manifest = build_preview(
            source_raw, current_raw, audit, SOURCE_RUN_ID, report_sha)

    a.output_dir.mkdir(parents=True, exist_ok=False)
    (a.output_dir / "preview.m3u8").write_bytes(preview)
    (a.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"preview_only": True, "new_scan_started": False,
                      "counts": manifest["counts"],
                      "ordered_yedekler_blocks_identical": True}))


if __name__ == "__main__":
    main()

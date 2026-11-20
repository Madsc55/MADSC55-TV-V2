#!/usr/bin/env python3
"""#497: consume an EXISTING Actions artifact, never invoke a stream scan.

Run inside a checked-out repository with GH_TOKEN and gh CLI. Produces only
a preview and manifest. Production publication remains a separate gated step.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from ibo_test_result_reconcile import digest, reconcile
from ibo_single_playlist_transfer import category, parse


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run-id", required=True, type=int, help="Already completed run")
    p.add_argument("--artifact", required=True, help="Exact existing artifact name")
    p.add_argument("--playlist", type=Path, default=Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"))
    p.add_argument("--output-dir", type=Path, required=True)
    a = p.parse_args()
    if a.run_id < 1 or not re.fullmatch(r"[a-zA-Z0-9_.-]+", a.artifact):
        p.error("Invalid run ID or artifact name")
    if a.playlist.name != "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8":
        p.error("Only canonical main playlist is supported")
    if a.output_dir.exists():
        p.error("Output directory must not exist (no overwrite)")
    raw = a.playlist.read_bytes()
    before = [b for b in parse(raw)[1] if category(b.split("\n", 1)[0]) == "YEDEKLER"]
    if len(before) != 1792:
        raise ValueError(f"Expected 1792 YEDEKLER entries; found {len(before)}")
    if not os.environ.get("GH_TOKEN"):
        raise ValueError("GH_TOKEN required for authenticated artifact retrieval")
    repo = os.environ.get("GITHUB_REPOSITORY", "Madsc55/MADSC55-TV-V2")
    run = json.loads(gh("run", "view", str(a.run_id), "--repo", repo,
                        "--json", "status,conclusion"))
    if run.get("status") != "completed":
        raise ValueError("Source run not completed")
    with tempfile.TemporaryDirectory(prefix="v2-497-") as d:
        gh("run", "download", str(a.run_id), "--repo", repo,
           "--name", a.artifact, "--dir", d)
        report_path = Path(d) / "report.json"
        if report_path.is_symlink() or not report_path.is_file():
            raise ValueError("Missing exact report.json (no guessing)")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        canonical = json.dumps(report, sort_keys=True, ensure_ascii=False,
                               separators=(",", ":")).encode("utf-8")
        result, manifest = reconcile(raw, report, digest(raw), digest(canonical))
    manifest["source_run_id"] = a.run_id
    manifest["artifact_name"] = a.artifact
    manifest["report_sha256"] = digest(canonical)
    manifest["preview_only"] = True
    a.output_dir.mkdir(parents=True, exist_ok=False)
    (a.output_dir / "preview.m3u8").write_bytes(result)
    (a.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"preview_only": True, "counts": manifest["counts"]}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""MADSC55 V2 read-only master orchestrator."""
import argparse
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description="MADSC55 V2 read-only master")
    parser.add_argument("--run", action="store_true", help="Run Turkish TV discovery and health audit")
    args = parser.parse_args()
    if not args.run:
        parser.print_help()
        return 0
    if not PLAYLIST.is_file():
        print("ERROR: Protected playlist not found", file=sys.stderr)
        return 2
    before = sha256(PLAYLIST)
    scripts = ["v2/turkish_tv_health.py", "v2/assets_health.py", "v2/logo_attribution.py", "v2/epg_integrity.py"]
    code = 0
    for script in scripts:
        print(f"RUN: {script}", flush=True)
        proc = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT, check=False)
        if proc.returncode:
            print(f"FAILED: {script} (exit {proc.returncode})", file=sys.stderr)
            code = 1
    after = sha256(PLAYLIST)
    if before != after:
        print("CRITICAL: protected playlist changed during run!", file=sys.stderr)
        return 3
    print("Protected playlist SHA-256 unchanged:", after, flush=True)
    return code

if __name__ == "__main__":
    raise SystemExit(main())

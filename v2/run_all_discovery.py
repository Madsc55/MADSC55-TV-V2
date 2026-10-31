#!/usr/bin/env python3
"""One-command V2 discovery coordinator; fail closed before network activity.

Runs public source availability, forge reference search, then encrypted discovery.
Never modifies IBO playlist or exports candidates to YEDEKLER. Playback and
device verification remain separate because they are not yet implemented.
"""
import argparse
import pathlib
import subprocess
import sys
from archive_acceptance_gate import check
from encrypted_archive import _cipher

ROOT = pathlib.Path(__file__).resolve().parent
def plan(archive, previous_report=None):
    steps = [
        [sys.executable, str(ROOT / "source_availability_audit.py"), "--audit-public-sources"],
        [sys.executable, str(ROOT / "github_source_discovery.py")],
        [sys.executable, str(ROOT / "run_forge_source_discovery.py"), "--scan-public-forges"],
        [sys.executable, str(ROOT / "run_live_page_discovery.py"), "--scan-approved-live-pages"],
        [sys.executable, str(ROOT / "run_webpage_playlist_discovery.py"), "--scan-approved-index-pages"],
        [sys.executable, str(ROOT / "discover.py"), "--encrypted-archive", str(archive)],
    ]
    if previous_report:
        steps[-1].extend(["--previous-report", str(previous_report)])
    return steps

def preflight(archive):
    if not archive or archive.is_symlink():
        raise RuntimeError("A private, non-symlink encrypted archive path is required")
    check()
    _cipher()
    if archive.exists():
        import stat
        mode = archive.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise RuntimeError("Archive must be a private regular file")
    return True

def execute(steps, runner=subprocess.run):
    for index, command in enumerate(steps, 1):
        result = runner(command, check=False, cwd=str(ROOT.parent))
        if result.returncode != 0:
            raise RuntimeError("Discovery stage " + str(index) + " failed; subsequent stages refused")
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-all", action="store_true", required=True,
                        help="Explicit opt-in to the complete currently implemented source scan")
    parser.add_argument("--encrypted-archive", type=pathlib.Path, required=True)
    parser.add_argument("--previous-report", type=pathlib.Path)
    args = parser.parse_args()
    preflight(args.encrypted_archive)
    execute(plan(args.encrypted_archive, args.previous_report))
    print("Source discovery finished; playback and IBO device testing NOT verified.")
if __name__ == "__main__":
    main()

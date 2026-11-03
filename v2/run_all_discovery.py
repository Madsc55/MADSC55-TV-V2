#!/usr/bin/env python3
"""One-command V2 discovery coordinator; fail closed before network activity.

Runs six bounded discovery stages and archives approved candidate sources.
Never modifies IBO playlist or exports candidates to YEDEKLER. Playback and
device verification remain separate because they are not yet implemented.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
from archive_acceptance_gate import check
from encrypted_archive import _cipher
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent
def plan(archive, previous_report=None, include_youtube=True):
    steps = [
        [sys.executable, str(ROOT / "source_availability_audit.py"), "--audit-public-sources"],
        [sys.executable, str(ROOT / "github_source_discovery.py")],
        [sys.executable, str(ROOT / "run_forge_source_discovery.py"), "--scan-public-forges"],
        [sys.executable, str(ROOT / "run_live_page_discovery.py"), "--scan-approved-live-pages"],
        [sys.executable, str(ROOT / "run_webpage_playlist_discovery.py"), "--scan-approved-index-pages"],
        [sys.executable, str(ROOT / "document_platform_discovery.py"), "--scan-public-documents"],
        [sys.executable, str(ROOT / "discover.py"), "--encrypted-archive", str(archive)],
    ]
    if include_youtube:
        steps.insert(-1, [sys.executable, str(ROOT / "youtube_discovery.py")])
    if previous_report:
        steps[-1].extend(["--previous-report", str(previous_report)])
    return steps

def validate_source_inventory(config_path=None):
    """Validate source inventory before any network-based discovery stage."""
    config_path = config_path or ROOT / "config" / "sources.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if data.get("policy") != "discovery-only; never modify live playlist":
        raise RuntimeError("Unsafe source inventory policy")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RuntimeError("No configured discovery sources")
    ids, urls = set(), set()
    for item in sources:
        if not isinstance(item, dict):
            raise RuntimeError("Invalid source entry")
        source_id, url = item.get("id"), item.get("url")
        if not isinstance(source_id, str) or not source_id.strip() or source_id in ids:
            raise RuntimeError("Invalid or duplicate source ID")
        if not isinstance(url, str) or url in urls:
            raise RuntimeError("Invalid or duplicate source URL")
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username
                or parsed.password or parsed.fragment or parsed.port not in (None, 443)
                or item.get("kind") != "m3u"
                or item.get("scope") not in ("TR", "AZ", "SE", "world", "candidate")):
            raise RuntimeError("Unsafe or malformed source entry: " + source_id)
        ids.add(source_id)
        urls.add(url)
    return len(sources)

def preflight(archive, include_youtube=True):
    if not archive or archive.is_symlink():
        raise RuntimeError("A private, non-symlink encrypted archive path is required")
    validate_source_inventory()
    check()
    _cipher()
    if archive.exists():
        import stat
        mode = archive.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise RuntimeError("Archive must be a private regular file")
    if include_youtube and shutil.which("yt-dlp") is None:
        raise RuntimeError("Full discovery requires yt-dlp; explicitly skip YouTube for partial coverage")
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
    parser.add_argument("--skip-youtube", action="store_true", help="Skip YouTube advisory scan; coverage is partial")
    args = parser.parse_args()
    include_youtube = not args.skip_youtube
    preflight(args.encrypted_archive, include_youtube)
    execute(plan(args.encrypted_archive, args.previous_report, include_youtube))
    print("Source discovery stages finished; check each report for PARTIAL coverage.")
    print("Playback and IBO device testing NOT verified.")
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Offline regression runner for the smart backup archive; no network or playlist writes."""
import argparse
import subprocess
import sys

MODULES = (
    "v2.test_backup_smart_archive",
    "v2.test_backup_evidence_adapter",
    "v2.test_backup_text_evidence",
    "v2.test_backup_archive_offline",
    "v2.test_backup_text_sampler",
    "v2.test_backup_text_batch",
    "v2.test_backup_playback_import",
    "v2.test_backup_archive_integration",
    "v2.test_backup_speech_evidence",
    "v2.test_backup_text_hint_import",
    "v2.test_spoken_language_sample_review",
    "v2.test_safe_hls_prefetch",
    "v2.test_single_channel_evidence_review",
)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verbose",action="store_true")
    args=parser.parse_args()
    cmd=[sys.executable,"-m","unittest"]
    if args.verbose:
        cmd.append("-v")
    cmd.extend(MODULES)
    completed=subprocess.run(cmd,check=False)
    raise SystemExit(completed.returncode)

if __name__=="__main__":
    main()

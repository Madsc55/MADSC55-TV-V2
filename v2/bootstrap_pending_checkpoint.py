#!/usr/bin/env python3
"""Restore old failed real-scan observations to a sealed resumable checkpoint."""
import argparse
import json
import os
from pathlib import Path

from scan_checkpoint import bootstrap_from_pending_inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observed-at", required=True)
    args = parser.parse_args()
    secret = os.environ.get("V2_ARCHIVE_PASSPHRASE", "")
    if len(secret) < 16:
        parser.error("Archive key is unavailable")
    summary = bootstrap_from_pending_inventory(
        args.inventory, args.report, args.output, secret,
        observed_at=args.observed_at)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

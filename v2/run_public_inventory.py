#!/usr/bin/env python3
"""Public read-only inventory preflight: no backup approval or stream probing needed."""
import argparse
import json
from pathlib import Path
from source_availability_audit import CONFIG, REPORT, audit

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-source-inventory", action="store_true", required=True)
    args = parser.parse_args()
    sources = json.loads(CONFIG.read_text(encoding="utf-8"))["sources"]
    report = audit(sources)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Source inventory checked:", report["source_count"],
          "reachable:", report["reachable_source_count"],
          "unreachable:", report["unreachable_source_count"])
    if report["unreachable_source_count"] or not report["source_count"]:
        raise SystemExit("Source inventory partially unavailable; inspect source IDs")
if __name__ == "__main__":
    main()

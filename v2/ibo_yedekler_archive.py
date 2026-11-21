#!/usr/bin/env python3
"""Read-only archival snapshot of ONLY the YEDEKLER group of the protected IBO playlist."""
import argparse
import hashlib
import json
import re
from pathlib import Path

GROUP = re.compile(r'group-title\s*=\s*"([^"]*)"', re.I)
TARGET = "YEDEKLER"


def inventory(source):
    raw = Path(source).read_bytes()
    lines = raw.decode("utf-8-sig", errors="replace").splitlines(keepends=True)
    header = lines[0] if lines and lines[0].lstrip().startswith("#EXTM3U") else "#EXTM3U\n"
    records = []
    block = []
    ordinal = 0
    for line in lines[1:]:
        if line.startswith("#EXTINF:"):
            if block:
                block = []
            block = [line]
        elif block:
            block.append(line)
            if line.strip() and not line.startswith("#"):
                ordinal += 1
                match = GROUP.search(block[0])
                if match and match.group(1).strip().upper() == TARGET:
                    records.append({"ordinal": ordinal, "raw": "".join(block),
                                    "name": block[0].rsplit(",", 1)[-1].strip(),
                                    "url_sha256": hashlib.sha256(line.strip().encode()).hexdigest()})
                block = []
    return raw, header, records


def snapshot(source, destination, expected_count=None):
    if expected_count is not None and (type(expected_count) is not int or expected_count < 1):
        raise ValueError("Expected count must be positive")
    src, dst = Path(source), Path(destination)
    if src.resolve() == dst.resolve() or dst.exists():
        raise ValueError("Refusing overwrite of source or existing snapshot")
    raw, header, records = inventory(src)
    if not records:
        raise ValueError("No YEDEKLER records; refusing empty archive")
    if expected_count is not None and len(records) != expected_count:
        raise ValueError(f"Expected {expected_count} YEDEKLER records, found {len(records)}; no archive created")
    dst.mkdir(parents=True, exist_ok=False)
    archive = header + "".join(row["raw"] for row in records)
    archive_path = dst / "YEDEKLER_ARCHIVE.m3u8"
    archive_path.write_bytes(archive.encode("utf-8"))
    manifest = {"schema": 1, "mode": "READ_ONLY_INITIAL_ARCHIVE",
                "source": src.name, "source_sha256": hashlib.sha256(raw).hexdigest(),
                "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                "archived_count": len(records), "expected_count": expected_count,
                "count_matches_expected": expected_count is None or len(records) == expected_count,
                "other_categories_modified": False, "source_modified": False,
                "records": [{"ordinal": x["ordinal"], "name": x["name"],
                             "url_sha256": x["url_sha256"], "classification": "UNREVIEWED"}
                            for x in records]}
    (dst / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-count", type=int, help="Optional strict YEDEKLER count guard")
    args = parser.parse_args()
    result = snapshot(args.source, args.output_dir, args.expected_count)
    print(json.dumps({"archived_count": result["archived_count"],
                      "source_sha256": result["source_sha256"],
                      "archive_sha256": result["archive_sha256"]}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read-only duplicate URL guard for new IPTV discovery candidates.

Compares exact URL strings (including query parameters) against the protected
main IBO playlist AND the archived YEDEKLER entries. Never downloads streams.
"""
import argparse
import hashlib
import json
from pathlib import Path


def urls(path):
    for line in Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines():
        value = line.strip()
        if value and not value.startswith("#"):
            yield value


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def inspect(main, archive, candidates):
    existing = {sha(url) for source in (main, archive) for url in urls(source)}
    accepted, duplicates = [], []
    seen = set()
    for url in urls(candidates):
        digest = sha(url)
        item = {"url_sha256": digest}
        if digest in existing or digest in seen:
            duplicates.append(item)
        else:
            accepted.append(item)
            seen.add(digest)
    return {"existing_unique_urls": len(existing),
            "accepted_count": len(accepted), "duplicate_count": len(duplicates),
            "accepted": accepted, "duplicates": duplicates,
            "mode": "READ_ONLY_PREVIEW", "source_modified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    output = Path(args.report)
    if output.exists():
        parser.error("Report exists; refusing overwrite")
    result = inspect(args.main, args.archive, args.candidates)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("existing_unique_urls", "accepted_count", "duplicate_count")}))


if __name__ == "__main__":
    main()

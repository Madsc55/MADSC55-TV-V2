#!/usr/bin/env python3
"""Offline historical URL recovery; never performs network scans or changes playlists."""
import argparse
import copy
import json
from pathlib import Path
from urllib.parse import urlsplit
import ipaddress

def read_records(path):
    with Path(path).open(encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError(f"{path}:{number}: expected JSON object")
            yield record

def validate_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return False
    except ValueError:
        return False
    try:
        address = ipaddress.ip_address(parsed.hostname)
        if not address.is_global:
            return False
    except ValueError:
        host = parsed.hostname.lower().rstrip(".")
        if host in ("localhost", "localhost.localdomain") or host.endswith(".localhost"):
            return False
        # Reject non-canonical numeric IPv4 forms (127.1, 2130706433,
        # 0177.0.0.1, 0x7f000001) that resolvers may map to private IPs.
        labels = host.split(".")
        if (not host or len(host) > 253 or len(labels) < 2
                or any(not label or len(label) > 63 or label.startswith("-")
                       or label.endswith("-") or not label.isascii()
                       or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label)
                       for label in labels)):
            return False
        if all(label.isdecimal() or (label.startswith("0x") and len(label) > 2
                  and all(c in "0123456789abcdef" for c in label[2:])) for label in labels):
            return False
    # Refuse ambiguous authorities, control characters and URL fragments.
    # Fragments are client-side only and must not enter recovery artifacts.
    if any(ord(c) < 33 or ord(c) == 127 for c in value) or parsed.fragment:
        return False
    if not parsed.netloc or parsed.hostname.startswith("-") or parsed.hostname.endswith("-"):
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    if port is not None and not 1 <= port <= 65535:
        return False
    return True

def recover(old_records, current_records):
    current_rows = list(current_records)
    historical_rows = list(old_records)
    if any(not isinstance(row, dict) for row in current_rows + historical_rows):
        raise ValueError("Historical recovery requires object records")
    current = {row["url"] for row in current_rows if validate_url(row.get("url"))}
    recovered, indexed = [], {}
    missing_url = 0
    duplicate_historical_urls = 0
    duplicate_source_associations = 0
    for row in historical_rows:
        url = row.get("url")
        if not validate_url(url):
            missing_url += 1
            continue
        if url in current:
            continue
        if url in indexed:
            duplicate_historical_urls += 1
            candidate = recovered[indexed[url]]
            candidate["historical_records"].append(copy.deepcopy(row))
            sources = candidate.get("source_ids", [])
            sources = list(sources) if isinstance(sources, list) else ([sources] if isinstance(sources, str) and sources else [])
            candidate["source_ids"] = sources
            for field in ("source_ids", "source_id", "source"):
                values = row.get(field)
                values = values if isinstance(values, list) else [values]
                for source in values:
                    if isinstance(source, str) and source and source not in sources:
                        sources.append(source)
                        duplicate_source_associations += 1
            continue
        indexed[url] = len(recovered)
        candidate = dict(row, recovery_status="HISTORICAL_NOT_REVERIFIED",
                         source_status="HISTORICAL_ARTIFACT")
        candidate["historical_records"] = [copy.deepcopy(row)]
        # Keep original historical status as provenance, never as current playback acceptance.
        if "status" in row:
            candidate["historical_status"] = row["status"]
        candidate["status"] = "HISTORICAL_NOT_REVERIFIED"
        # Historical success flags are not proof of current video+audio decoding.
        for flag in ("av_verified", "device_verified", "video_verified", "audio_verified",
                     "playback_verified", "ibo_device_verified"):
            candidate[flag] = False
        sources = candidate.get("source_ids", [])
        sources = list(sources) if isinstance(sources, list) else ([sources] if isinstance(sources, str) and sources else [])
        for field in ("source_id", "source"):
            value = candidate.get(field)
            if isinstance(value, str) and value and value not in sources:
                sources.append(value)
        candidate["source_ids"] = list(dict.fromkeys(
            x for x in sources if isinstance(x, str) and x))
        recovered.append(candidate)
    return recovered, {"historical_missing_real_url": missing_url,
                       "recoverable_real_urls": len(recovered),
                       "current_urls_excluded": len(current),
                       "duplicate_historical_urls": duplicate_historical_urls,
                       "additional_source_associations_preserved": duplicate_source_associations,
                       "device_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.report.exists():
        parser.error("Refusing to overwrite an existing recovery artifact")
    rows, report = recover(read_records(args.historical), read_records(args.current))
    if not rows:
        raise SystemExit("No real historical URLs recovered; refusing empty candidate export")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))

if __name__ == "__main__":
    main()

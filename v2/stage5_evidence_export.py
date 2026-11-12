#!/usr/bin/env python3
"""Stage 5 evidence-gated IBO export. No synthetic or HTTP-only acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

def entries(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines or lines[0].strip() != "#EXTM3U":
        raise ValueError("Invalid M3U header")
    result, pending = [], None
    for line in lines[1:]:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            if pending is not None:
                raise ValueError("Missing stream URL")
            pending = line
        elif line and not line.startswith("#"):
            if pending is None or urlsplit(line).scheme not in ("https", "http"):
                raise ValueError("Malformed M3U entry")
            result.append((pending, line))
            pending = None
    if pending is not None:
        raise ValueError("Dangling EXTINF")
    return result

def run(args):
    source = entries(args.source)
    protected = args.protected.read_bytes()
    before = hashlib.sha256(protected).hexdigest()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    if not isinstance(evidence, list):
        raise ValueError("Evidence must be a JSON array")
    approved = {}
    for row in evidence:
        if not isinstance(row, dict):
            raise ValueError("Invalid evidence row")
        url = row.get("url")
        if not isinstance(url, str):
            raise ValueError("Evidence URL missing")
        if (row.get("video_verified") is not True or row.get("audio_verified") is not True
            or row.get("ibo_playback_verified") is not True
            or not isinstance(row.get("evidence_ref"), str) or not row["evidence_ref"].strip()
            or not isinstance(row.get("channel_id"), str) or not row["channel_id"].strip()):
            continue
        if url in approved:
            raise ValueError("Duplicate evidence URL")
        approved[url] = row
    selected, ids, urls = [], set(), set()
    for extinf, url in source:
        if url not in approved:
            continue
        channel_id = approved[url]["channel_id"]
        if url in urls or channel_id in ids:
            continue
        urls.add(url)
        ids.add(channel_id)
        selected.append((extinf, url))
    if len(selected) < args.target:
        raise ValueError(f"INSUFFICIENT_REAL_EVIDENCE: {len(selected)}/{args.target}")
    selected = selected[:args.target]
    if args.output.resolve() == args.protected.resolve() or args.output.resolve() == args.source.resolve():
        raise ValueError("Refusing to overwrite protected/source playlist")
    output = "#EXTM3U\n" + "".join(f"{meta}\n{url}\n" for meta, url in selected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    if len(entries(args.output)) != args.target:
        raise ValueError("Output M3U integrity check failed")
    if hashlib.sha256(args.protected.read_bytes()).hexdigest() != before:
        raise ValueError("Protected playlist changed")
    print(json.dumps({"status": "EVIDENCE_GATED_EXPORT", "target": args.target,
        "exported": len(selected), "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "protected_sha256_unchanged": True, "output": str(args.output)}, ensure_ascii=False))

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    p.add_argument("--protected", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--target", type=int, choices=[1000, 2000], required=True)
    run(p.parse_args())

#!/usr/bin/env python3
"""Offline IBO packaging gate. Never publishes or discovers streams."""
import argparse
import hashlib
import json
import pathlib
import re
import urllib.parse

def parse(text):
    if not text.lstrip("\ufeff").startswith("#EXTM3U"):
        raise ValueError("missing EXTM3U header")
    pending = None
    records = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            if pending is not None:
                raise ValueError("unpaired EXTINF")
            if "," not in line:
                raise ValueError("missing channel name")
            pending = (line, line.rsplit(",", 1)[1].strip())
            if not pending[1]:
                raise ValueError("empty channel name")
        elif line and not line.startswith("#"):
            if pending is None:
                raise ValueError("URL without EXTINF")
            parts = urllib.parse.urlsplit(line)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                raise ValueError("invalid stream URL")
            records.append((pending[0], line))
            pending = None
    if pending:
        raise ValueError("trailing EXTINF without URL")
    return records

def validate(records):
    if not records:
        raise ValueError("empty playlist")
    exact = set()
    for extinf, url in records:
        pair = (extinf, url)
        if pair in exact:
            raise ValueError("duplicate identical record")
        exact.add(pair)
    return True

def package(text, target, evidence):
    if type(target) is not int or target not in (1000, 2000):
        raise ValueError("unsupported IBO package target")
    if not isinstance(evidence, dict):
        raise ValueError("invalid evidence mapping")
    records = parse(text)
    validate(records)
    if len(records) < target:
        raise ValueError(f"insufficient real records: {len(records)} < {target}")
    if len(evidence) < target:
        raise ValueError("insufficient evidence records")
    selected = records[:target]
    for extinf, url in selected:
        key = hashlib.sha256((extinf + "\n" + url).encode()).hexdigest()
        proof = evidence.get(key)
        if not isinstance(proof, dict) or proof.get("status") != "AV_VERIFIED" or not proof.get("video") or not proof.get("audio"):
            raise ValueError("missing real video/audio evidence for selected record")
    result = "#EXTM3U\n" + "".join(a + "\n" + b + "\n" for a,b in selected)
    return result, {"target":target,"records":len(selected),"sha256":hashlib.sha256(result.encode()).hexdigest(),"status":"EVIDENCE_GATED"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--playlist",type=pathlib.Path,required=True)
    ap.add_argument("--evidence",type=pathlib.Path,required=True)
    ap.add_argument("--target",type=int,choices=[1000,2000],required=True)
    ap.add_argument("--output",type=pathlib.Path,required=True)
    args=ap.parse_args()
    if args.output.resolve() == args.playlist.resolve() or args.output.exists():
        raise SystemExit("refusing to overwrite existing playlist/output")
    text=args.playlist.read_text(encoding="utf-8-sig")
    evidence=json.loads(args.evidence.read_text(encoding="utf-8"))
    content,report=package(text,args.target,evidence)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(content,encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Stage 5 evidence-gated IBO export. No synthetic or HTTP-only acceptance."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from secure_archive import atomic_write

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

MAX_PROOF_BYTES = 256 * 1024 * 1024

def media_has_audio_video(path):
    """Require decoded video AND audio frames, not just ffprobe stream metadata."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type",
             "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30, check=True)
        payload = json.loads(result.stdout)
        streams = payload.get("streams", []) if isinstance(payload, dict) else []
        if not isinstance(streams, list):
            return False
        kinds = {item.get("codec_type") for item in streams if isinstance(item, dict)}
        if not {"video", "audio"} <= kinds:
            return False
        for selector in ("v:0", "a:0"):
            decoded = subprocess.run(
                ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-xerror",
                 "-i", str(path), "-map", "0:" + selector,
                 "-frames:" + selector[0], "1", "-f", "framemd5", "-"],
                capture_output=True, text=True, timeout=30, check=False)
            # An actual decoded frame appears as a six-field framemd5 CSV line.
            frames = [line for line in decoded.stdout.splitlines()
                      if line.strip() and not line.lstrip().startswith("#")
                      and len(line.split(",")) == 6
                      and all(field.strip() for field in line.split(","))]
            if decoded.returncode != 0 or not frames:
                return False
        return True
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, AttributeError):
        return False

def run(args):
    if type(args.target) is not int or args.target not in (1000, 2000):
        raise ValueError("Unsupported real IBO target")
    source = entries(args.source)
    protected = args.protected.read_bytes()
    before = hashlib.sha256(protected).hexdigest()
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    if not isinstance(evidence, list):
        raise ValueError("Evidence must be a JSON array")
    approved = {}
    used_proof_digests = set()
    evidence_dir = args.evidence.resolve().parent
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
        # A bare boolean or an invented reference is not playback evidence.
        proof = row.get("evidence_file")
        digest = row.get("evidence_sha256")
        if not isinstance(proof, str) or not proof or not isinstance(digest, str) or len(digest) != 64:
            continue
        proof_path = (evidence_dir / proof).resolve()
        if not proof_path.is_relative_to(evidence_dir) or not proof_path.is_file():
            continue
        # Hash in bounded chunks; never read untrusted proof media into memory.
        if proof_path.stat().st_size > MAX_PROOF_BYTES:
            continue
        checksum = hashlib.sha256()
        with proof_path.open("rb") as media:
            for chunk in iter(lambda: media.read(1024 * 1024), b""):
                checksum.update(chunk)
        if checksum.hexdigest() != digest.lower() or digest.lower() in used_proof_digests:
            continue
        if not media_has_audio_video(proof_path):
            continue
        if url in approved:
            raise ValueError("Duplicate evidence URL")
        used_proof_digests.add(digest.lower())
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
    if args.output.resolve() in {args.protected.resolve(), args.source.resolve(), args.evidence.resolve()}:
        raise ValueError("Refusing to overwrite protected/source playlist")
    output = "#EXTM3U\n" + "".join(f"{meta}\n{url}\n" for meta, url in selected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(args.output, output.encode("utf-8"))
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

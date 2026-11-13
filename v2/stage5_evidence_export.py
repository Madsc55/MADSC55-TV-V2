#!/usr/bin/env python3
"""Stage 5 evidence-gated IBO export. No synthetic or HTTP-only acceptance."""
import argparse
import hashlib
import json
import os
import re
import subprocess
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

def media_has_audio_video(path):
    """Demand decoded video AND decoded audio packets from a LOCAL proof clip.

    Stream metadata alone is not playback evidence. Restrict FFmpeg protocols so
    a malicious proof container cannot reference a remote stream during audit.
    """
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
             "-show_entries", "stream=codec_type", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=30, check=True)
        streams = json.loads(result.stdout).get("streams", [])
        if not isinstance(streams, list) or not all(isinstance(x, dict) for x in streams):
            return False
        kinds = {item.get("codec_type") for item in streams}
        if not {"video", "audio"} <= kinds:
            return False
        decoded = subprocess.run(
            ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error",
             "-protocol_whitelist", "file,pipe", "-i", str(path),
             "-map", "0:v:0", "-map", "0:a:0", "-t", "2",
             "-f", "framemd5", "-"],
            capture_output=True, text=True, timeout=30, check=True)
        # Explicit map order: output stream 0=video, 1=audio. Require at
        # least one decoded frame/sample per stream, not a zero-frame success.
        rows = [line.strip() for line in decoded.stdout.splitlines()
                if line.strip() and not line.startswith("#")]
        return (any(re.match(r"^0\s*,", line) for line in rows)
                and any(re.match(r"^1\s*,", line) for line in rows))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError):
        return False


def proof_digest(path):
    """Hash bounded local proof without loading private media into RAM."""
    if path.stat().st_size <= 0 or path.stat().st_size > 512 * 1024 * 1024:
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_private_destination(path, source, protected):
    """Never overwrite existing files or publish private evidence in tracked paths."""
    target = path.resolve()
    root = Path(__file__).resolve().parents[1]
    reports = (root / "v2/reports").resolve()
    if (path.exists() or path.is_symlink()
            or path.name.startswith("private-") is False
            or path.suffix != ".m3u8"
            or target in (source.resolve(), protected.resolve())
            or (root in target.parents and reports not in target.parents)):
        raise ValueError("Output must be a new private .m3u8 in an isolated location")

def run(args):
    if type(args.target) is not int or not 1 <= args.target <= 2000:
        raise ValueError("Invalid package target")
    valid_private_destination(args.output, args.source, args.protected)
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
        if (not isinstance(proof, str) or not proof
                or not isinstance(digest, str)
                or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None):
            continue
        requested_proof = evidence_dir / proof
        proof_path = requested_proof.resolve()
        if (requested_proof.is_symlink() or not proof_path.is_relative_to(evidence_dir)
                or not proof_path.is_file()):
            continue
        checked_digest = proof_digest(proof_path)
        if checked_digest != digest.lower():
            continue
        # One identical proof clip cannot certify distinct channels.
        # Preserve fail-closed duplicate URL detection in the next block.
        if checked_digest in used_proof_digests and url not in approved:
            continue
        if not media_has_audio_video(proof_path):
            continue
        if url in approved:
            raise ValueError("Duplicate evidence URL")
        used_proof_digests.add(checked_digest)
        approved[url] = row
    selected, ids, urls = [], set(), set()
    for extinf, url in source:
        if url not in approved:
            continue
        channel_id = approved[url]["channel_id"]
        source_id = re.search(r'(?:^|\s)tvg-id="([^"]+)"', extinf)
        # A proof for another broadcaster must not authorize this M3U row.
        if source_id is None or source_id.group(1) != channel_id:
            continue
        if url in urls or channel_id in ids:
            continue
        urls.add(url)
        ids.add(channel_id)
        selected.append((extinf, url))
    if len(selected) < args.target:
        raise ValueError(f"INSUFFICIENT_REAL_EVIDENCE: {len(selected)}/{args.target}")
    selected = selected[:args.target]
    output = "#EXTM3U\n" + "".join(f"{meta}\n{url}\n" for meta, url in selected)
    if hashlib.sha256(args.protected.read_bytes()).hexdigest() != before:
        raise ValueError("Protected playlist changed before export")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(args.output, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(output)
        if len(entries(args.output)) != args.target:
            raise ValueError("Output M3U integrity check failed")
        if hashlib.sha256(args.protected.read_bytes()).hexdigest() != before:
            raise ValueError("Protected playlist changed")
    except Exception:
        args.output.unlink(missing_ok=True)
        raise
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

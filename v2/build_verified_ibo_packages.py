#!/usr/bin/env python3
"""Fail-closed offline IBO package builder. Never touches the protected playlist."""
import argparse
import json
import pathlib
import sys
import urllib.parse

def eligible(row):
    if row.get("status") != "AV_VERIFIED" and row.get("http_hls_status") != "AV_VERIFIED":
        return False
    # Require explicit, independently recorded audio and video proof.
    if row.get("video_proven") is not True or row.get("audio_proven") is not True:
        return False
    # Require independently recorded, traceable A/V evidence metadata.
    proof = row.get("av_evidence")
    if not isinstance(proof, dict):
        return False
    if proof.get("url") != row.get("url") or proof.get("video") is not True or proof.get("audio") is not True:
        return False
    digest = proof.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
        return False
    if not isinstance(proof.get("captured_at"), str) or not proof.get("captured_at", "").strip():
        return False
    if row.get("fixture") is True or proof.get("fixture") is True:
        return False
    url = row.get("url", "")
    p = urllib.parse.urlsplit(url) if isinstance(url, str) else urllib.parse.urlsplit("")
    return p.scheme in ("https", "http") and bool(p.hostname) and not (p.username or p.password)

def make(inventory, outdir):
    rows = [json.loads(line) for line in inventory.read_text(encoding="utf-8").splitlines() if line.strip()]
    accepted = []
    seen_urls = set()
    seen_ids = set()
    for row in rows:
        if not eligible(row):
            continue
        url = row["url"]
        identity = row.get("tvg_id") or row.get("channel_id")
        if url in seen_urls or not isinstance(identity, str) or not identity.strip() or identity in seen_ids:
            continue
        seen_urls.add(url)
        seen_ids.add(identity)
        accepted.append(row)
    result = {"verified_unique_channels": len(accepted), "mock_data_used": False, "packages": {}}
    for target in (1000, 2000):
        if len(accepted) < target:
            result["packages"][str(target)] = "BLOCKED_INSUFFICIENT_AV_EVIDENCE"
            continue
        lines = ["#EXTM3U"]
        for row in accepted[:target]:
            name = str(row.get("name") or row.get("tvg_id")).replace("\n", " ").replace("\r", " ").replace(",", " ")
            identity = str(row.get("tvg_id") or row["channel_id"]).replace('"', " ").replace("\\n", " ").replace("\\r", " ")
            group = str(row.get("group", "")).replace('"', "").replace("\n", " ")
            lines += [f'#EXTINF:-1 tvg-id="{identity}" group-title="{group}",{name}', row["url"]]
        payload = "\n".join(lines) + "\n"
        # Validate the generated playlist before publishing it.
        actual = payload.splitlines()
        if actual[0] != "#EXTM3U" or len(actual) != 1 + target * 2:
            raise ValueError("Invalid M3U header or entry count")
        if len(set(actual[2::2])) != target:
            raise ValueError("Duplicate M3U URLs")
        if not all(line.startswith("#EXTINF:-1 ") and line.count(",") == 1 for line in actual[1::2]):
            raise ValueError("Malformed EXTINF records")
        outdir.mkdir(parents=True, exist_ok=True)
        destination = outdir / f"IBO_AV_VERIFIED_{target}.m3u8"
        destination.write_text(payload, encoding="utf-8")
        result["packages"][str(target)] = str(destination)
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", type=pathlib.Path, required=True)
    ap.add_argument("--outdir", type=pathlib.Path, required=True)
    args = ap.parse_args()
    result = make(args.inventory, args.outdir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if any(value.startswith("BLOCKED") for value in result["packages"].values()):
        sys.exit(2)

if __name__ == "__main__":
    main()

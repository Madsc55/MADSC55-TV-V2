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
            identity = row.get("tvg_id") or row["channel_id"]
            group = str(row.get("group", "")).replace('"', "").replace("\n", " ")
            lines += [f'#EXTINF:-1 tvg-id="{identity}" group-title="{group}",{name}', row["url"]]
        payload = "\n".join(lines) + "\n"
        # Validate the generated playlist before publishing it.
        actual = payload.splitlines()
        assert actual[0] == "#EXTM3U" and len(actual) == 1 + target * 2
        assert len(set(actual[2::2])) == target
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

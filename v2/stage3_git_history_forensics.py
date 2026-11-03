#!/usr/bin/env python3
"""Offline exact-SHA recovery from reachable Git history in the SAME V2 repo.

Never accesses IPTV services or exports credential-bearing URLs to public logs,
reports, Git commits or unencrypted Actions artifacts. A private AES-GCM archive
is created only when V2_ARCHIVE_KEY_HEX is configured and real matches exist.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from discover import entries
from historical_inventory_guard import reconcile, preserve_to_new_archive, verify_historical_baseline
from historical_url_recovery import validate_url

SOURCE_EXTENSIONS = (".m3u", ".m3u8", ".json", ".jsonl", ".txt", ".csv")
MAX_FILE = 32_000_000
MAX_BLOBS = 12000
URL_FIELDS = {"url", "stream_url", "stream", "hls_url", "playback_url", "link", "src"}


def git(args, *, input_bytes=None):
    proc = subprocess.run(["git", *args], input=input_bytes, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=False)
    if proc.returncode:
        raise RuntimeError("Local V2 Git history command failed: " + args[0])
    return proc.stdout


def candidate_blobs():
    """Find distinct Git file blobs across all fetched V2 refs and commits."""
    raw = git(["rev-list", "--objects", "--all"]).decode("utf-8", "replace")
    objects = {}
    for line in raw.splitlines():
        parts = line.split(" ", 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            continue
        path = parts[1]
        if not path.lower().endswith(SOURCE_EXTENSIONS):
            continue
        if parts[0] not in objects:
            objects[parts[0]] = path
    if len(objects) > MAX_BLOBS:
        raise ValueError("V2 Git history text blob audit limit exceeded; not exhaustive")
    ids = list(objects)
    if not ids:
        return [], 0
    details = git(["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                  input_bytes=("\n".join(ids)+"\n").encode()).decode().splitlines()
    eligible, skipped_oversize = [], 0
    for line in details:
        fields = line.split()
        if len(fields) != 3:
            raise ValueError("Git blob metadata incomplete")
        sha, kind, size = fields
        if kind != "blob":
            continue
        if int(size) > MAX_FILE:
            skipped_oversize += 1
            continue
        eligible.append((sha, objects[sha]))
    return eligible, skipped_oversize


def iter_url_entries(path, data):
    text = data.decode("utf-8-sig", "replace")
    if path.lower().endswith((".m3u", ".m3u8")):
        for entry in entries(text):
            yield entry
        return
    if path.lower().endswith((".json", ".jsonl")):
        documents = []
        if path.lower().endswith(".jsonl"):
            for line in text.splitlines():
                if line.strip():
                    try:
                        documents.append(json.loads(line))
                    except (ValueError, TypeError):
                        continue
        else:
            try:
                documents.append(json.loads(text))
            except (ValueError, TypeError):
                return
        stack = documents
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
            elif isinstance(node, dict):
                for key, val in node.items():
                    if key.casefold() in URL_FIELDS and isinstance(val, str) and validate_url(val):
                        yield {"url": val, "name": "", "tvg_id": "", "group": ""}
                    if isinstance(val, (dict, list)):
                        stack.append(val)
        return
    for raw in text.splitlines():
        value = raw.strip()
        if validate_url(value):
            yield {"url": value, "name": "", "tvg_id": "", "group": ""}


def audit(index, *, encrypted_output=None, sealed_output=None, seal_public_key=None):
    raw = Path(index).read_bytes()
    if hashlib.sha256(raw).hexdigest() != "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27":
        raise ValueError("Original 4955 immutable #60 history index mismatch")
    history = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]
    if len(history) != 4955:
        raise ValueError("Original historical row count mismatch")
    identity_hash = verify_historical_baseline(history, history)
    if identity_hash != "e84cf1273ae54fc89de5d7edc3a46b4db78b91ddd7d6953dabdde30a6c3e0c83":
        raise ValueError("Original 4955 identities mismatch")
    hashes = {r["url_sha256"] for r in history}
    blobs, oversize = candidate_blobs()
    found = {}
    parsed_urls = 0
    for sha, path in blobs:
        content = git(["cat-file", "blob", sha])
        for entry in iter_url_entries(path, content):
            url = entry["url"]
            parsed_urls += 1
            key = hashlib.sha256(url.encode("utf-8")).hexdigest()
            if key not in hashes:
                continue
            source = "v2-git-blob-" + sha[:12]
            if key not in found:
                found[key] = {"url": url, "url_sha256": key, "source": source,
                              "source_ids": [source], "name": entry.get("name", ""),
                              "tvg_id": entry.get("tvg_id", ""), "group": entry.get("group", "")}
            elif source not in found[key]["source_ids"]:
                found[key]["source_ids"].append(source)
    matches = list(found.values())
    if sealed_output is not None:
        if seal_public_key is None:
            raise ValueError("Missing public key for confidential recovered URL transport")
        from stage3_sealed_export import seal_rows
        seal_rows(matches, seal_public_key, sealed_output)
    if encrypted_output is not None:
        if not matches:
            encrypted_state = "NO_MATCHES"
        else:
            protected, candidates, proof = reconcile(history, matches, 4955)
            if (proof["historical_unique_identities"] != 4955 or
                    len(candidates) != len(matches)):
                raise ValueError("URL recovery lost historical identities")
            if not preserve_to_new_archive(encrypted_output, protected, candidates):
                raise ValueError("Encrypted URL evidence archival failed")
            encrypted_state = "ENCRYPTED_ONLY"
    else:
        encrypted_state = "NOT_REQUESTED"
    return {
        "schema": 1,
        "policy": "EXACT_SHA256_OFFLINE_V2_GIT_HISTORY_NO_PUBLIC_STREAM_URLS",
        "original_historical_sha256_identities": 4955,
        "distinct_git_text_blobs_checked": len(blobs),
        "git_blobs_skipped_oversize": oversize,
        "url_like_entries_tested": parsed_urls,
        "exact_historical_url_matches": len(matches),
        "historical_hashes_not_matched": 4955 - len(matches),
        "matched_historical_sha256": sorted(found),
        "encrypted_recovery_artifact": encrypted_state,
        "confidential_rsa_aes_transit_sealed": sealed_output is not None,
        "real_stream_playback_reverified": 0,
        "device_verified": False,
        "channel_playlist_modified": False,
        "live_channel_discovery_performed": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Offline V2 Git-history real URL evidence recovery")
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--encrypted-output", type=Path)
    parser.add_argument("--sealed-output", type=Path)
    parser.add_argument("--seal-public-key", type=Path)
    args = parser.parse_args()
    outputs = [args.report] + ([args.encrypted_output] if args.encrypted_output else []) + ([args.sealed_output] if args.sealed_output else [])
    if any(x.exists() or x.is_symlink() or x.resolve() == args.index.resolve() for x in outputs):
        parser.error("Refusing overwrite of existing output or history input")
    if len(set(x.resolve() for x in outputs)) != len(outputs):
        parser.error("Overlapping output paths")
    result = audit(args.index, encrypted_output=args.encrypted_output,
                   sealed_output=args.sealed_output, seal_public_key=args.seal_public_key)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print("V2 Git history offline scan: %d distinct blobs; %d exact real URL identities recovered; %d still hash-only." %
          (result["distinct_git_text_blobs_checked"], result["exact_historical_url_matches"],
           result["historical_hashes_not_matched"]))


if __name__ == "__main__":
    main()

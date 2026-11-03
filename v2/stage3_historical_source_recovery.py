#!/usr/bin/env python3
"""Read-only Oct-28 original 25 GitHub source snapshots vs real #60 4955 hashes.

Queries historical GitHub commits at the exact original source-discovery time;
does NOT discover new feeds, probe playback, or alter protected M3U files.
Public output contains hashes and provenance only; never stream URLs/tokens.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from discover import entries
from historical_local_match import validate_index
from historical_url_recovery import validate_url
from historical_inventory_guard import reconcile, preserve_to_new_archive

CUTOFF = "2026-10-28T18:18:09Z"
MAX_BYTES = 32_000_000
MAX_SOURCES = 40


def _read(url, api=False):
    headers = {"User-Agent": "MADSC55-TV-V2-Stage3-historical-evidence/1"}
    token = os.environ.get("GH_TOKEN", "")
    if api and token:
        headers["Authorization"] = "Bearer " + token
        headers["Accept"] = "application/vnd.github+json"
    with urlopen(Request(url, headers=headers), timeout=35) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Historical source exceeds bounded size")
    return data


def historical_commit(repo, path):
    url = ("https://api.github.com/repos/" + quote(repo, safe="/") +
           "/commits?" + urlencode({"path": path, "until": CUTOFF, "per_page": "1"}))
    raw = json.loads(_read(url, api=True))
    if not isinstance(raw, list) or not raw:
        raise ValueError("No historical source revision at cutoff")
    commit = raw[0].get("sha")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid original source commit")
    return commit


def match_feed(hashes, text, source_name):
    """Match exactly; never match by name, logo, TVG ID or fuzzy URL."""
    matched = {}
    parsed = 0
    for entry in entries(text):
        url = entry.get("url")
        if not validate_url(url):
            continue
        parsed += 1
        identity = hashlib.sha256(url.encode("utf-8")).hexdigest()
        if identity not in hashes or identity in matched:
            continue
        matched[identity] = {
            "url": url, "url_sha256": identity,
            "source": source_name,
            "name": entry.get("name", ""),
            "tvg_id": entry.get("tvg_id", ""),
            "logo": entry.get("logo", ""),
            "group": entry.get("group", ""),
        }
    return matched, parsed


def audit(history, original_source_snapshot):
    hashes = validate_index(history, 4955)
    sources = original_source_snapshot.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= MAX_SOURCES:
        raise ValueError("Original #60 source discovery snapshot incomplete")
    all_matches, audits, errors = {}, [], []
    for index, source in enumerate(sources):
        name = "github-auto-" + str(index)
        repo, path = source.get("repository"), source.get("path")
        if (not isinstance(repo, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo)
                or any(part in (".", "..") for part in repo.split("/"))):
            raise ValueError("Invalid original GitHub repository")
        if not isinstance(path, str) or not path or len(path) > 512 or ".." in path.split("/"):
            raise ValueError("Invalid original source file path")
        item = {"source_label": name, "repository": repo, "path": path,
                "original_entries": source.get("entries"), "matched_hashes": 0}
        try:
            revision = historical_commit(repo, path)
            uri = ("https://raw.githubusercontent.com/" + quote(repo, safe="/") +
                   "/" + revision + "/" + quote(path, safe="/"))
            feed = _read(uri).decode("utf-8-sig", errors="replace")
            matches, parsed = match_feed(hashes, feed, name)
            item.update(status="HISTORICAL_FILE_READ", original_commit=revision,
                        parsed_valid_urls=parsed, matched_hashes=len(matches))
            for identity, row in matches.items():
                if identity in all_matches:
                    old = all_matches[identity]
                    old["source_ids"] = list(dict.fromkeys(old["source_ids"] + [name]))
                else:
                    all_matches[identity] = dict(row, source_ids=[name])
        except Exception as exc:
            # No exception text: failing HTTP paths can contain tokens.
            item.update(status="UNAVAILABLE_OR_INACCESSIBLE", error_type=type(exc).__name__)
            errors.append(name)
        audits.append(item)
    result = {
        "schema": 1,
        "policy": "READ_ONLY_HISTORIC_GITHUB_COMMITS_NO_LIVE_MEDIA_CHECK",
        "cutoff": CUTOFF,
        "real_4955_original_identities": 4955,
        "historical_source_files_attempted": len(sources),
        "historical_source_files_read": len(sources) - len(errors),
        "source_files_unavailable": len(errors),
        "exact_original_url_hashes_recovered": len(all_matches),
        "original_url_hashes_still_unmatched": 4955 - len(all_matches),
        "matched_hashes": sorted(all_matches),
        "source_audit": audits,
        "region_claim_verified": False,
        "device_playback_verified": False,
        "main_playlist_modified": False,
        "new_channel_discovery": False,
        "plaintext_urls_logged": False,
    }
    return result, list(all_matches.values())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--original-discovery", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--private-archive", type=Path)
    args = parser.parse_args()
    targets = [args.report] + ([args.private_archive] if args.private_archive else [])
    if len({str(x.resolve()) for x in [args.index, args.original_discovery, *targets]}) != 2 + len(targets):
        parser.error("Input and output paths must be distinct")
    if any(p.exists() or p.is_symlink() for p in targets):
        parser.error("Refusing overwrite")
    history = [json.loads(line) for line in args.index.read_text(encoding="utf-8").splitlines() if line]
    source_snapshot = json.loads(args.original_discovery.read_text(encoding="utf-8"))
    report, matches = audit(history, source_snapshot)
    if args.private_archive:
        if not os.environ.get("V2_ARCHIVE_KEY_HEX"):
            raise ValueError("Private archive requires V2_ARCHIVE_KEY_HEX")
        protected, indexed, proof = reconcile(history, matches, 4955)
        if proof["historical_unique_identities"] != 4955:
            raise ValueError("Original history lost during archive creation")
        report["encrypted_matched_urls_verified"] = preserve_to_new_archive(
            args.private_archive, protected, indexed)
    else:
        report["encrypted_matched_urls_verified"] = False
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print("Historical GitHub sources checked:", report["historical_source_files_read"],
          "of", report["historical_source_files_attempted"],
          "exact URL hash matches:", report["exact_original_url_hashes_recovered"],
          "remaining unmatched:", report["original_url_hashes_still_unmatched"])


if __name__ == "__main__":
    main()

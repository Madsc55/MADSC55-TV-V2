#!/usr/bin/env python3
"""Read-only exact-name watchlist within unified V2 M3U channel discovery."""
import hashlib
import re
from discover import entries

NAMES = ("Güneş TV", "Rec TV", "Gopik TV")

def canonical(value):
    value = str(value).strip().casefold()
    value = value.translate(str.maketrans("çğıöşü", "cgiosu"))
    return re.sub(r"[\s._-]+", " ", value).strip()

def report(loaded, main_text, names=NAMES):
    """Reports real metadata occurrence hashes, never live URLs or AV proof."""
    lookup = {canonical(name): name for name in names}
    if len(lookup) != len(names):
        raise ValueError("Duplicate watchlist channel identity")
    existing = {canonical(row["name"]) for row in entries(main_text)}
    candidates = {name: {"sources": set(), "hashes": set()}
                  for name in names}
    for source_id, text in loaded:
        for row in entries(text):
            original = lookup.get(canonical(row["name"]))
            if original is None:
                continue
            candidates[original]["sources"].add(source_id)
            candidates[original]["hashes"].add(
                hashlib.sha256(row["url"].encode("utf-8")).hexdigest())
    return {
        "schema": 1, "kind": "EXACT_CHANNEL_NAME_METADATA_WATCHLIST",
        "channels": [
            {
                "name": name,
                "status": ("EXACT_METADATA_CANDIDATE_NOT_AV_VERIFIED"
                           if candidates[name]["hashes"] else "NO_EXACT_SOURCE_METADATA"),
                "matched_source_ids": sorted(candidates[name]["sources"]),
                "unique_candidate_url_sha256": sorted(candidates[name]["hashes"]),
                "already_in_scanned_development_snapshot": canonical(name) in existing,
            }
            for name in names
        ],
        "av_verified": False, "spoken_language_verified": False,
        "ibo_device_verified": False,
        "playlist_modified": False,
    }

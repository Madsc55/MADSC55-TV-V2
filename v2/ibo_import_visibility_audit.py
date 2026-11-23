#!/usr/bin/env python3
"""Read-only reconciliation of canonical M3U counts and reported IBO Player counts.

Never rewrites the playlist, removes duplicates or claims to know the player's
import logic. Does not fetch remote URLs. Full URL/token values stay out of reports.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from playlist_parts_manager import PLAYLIST, split_records, category
from channel_command_engine import key, record_url, record_name

SUFFIX = re.compile(r"\s*\((\d+)\)\s*$")


def audit(data: bytes, observed=None) -> dict:
    observed = observed or {}
    if not isinstance(observed, dict):
        raise ValueError("observed must be a category/count object")
    normalized = {}
    for name, count in observed.items():
        if not isinstance(name, str) or type(count) is not int or count < 0:
            raise ValueError("reported player count must be a nonnegative integer")
        normalized[key(name)] = count

    header, records = split_records(data)
    by_group = {}
    urls_by_group = defaultdict(set)
    global_urls = defaultdict(list)
    metadata_by_group = defaultdict(list)
    malformed = []
    for index, record in enumerate(records, 1):
        try:
            label = category(record)
            ident = key(label)
            url = record_url(record)
        except (ValueError, UnicodeError) as exc:
            malformed.append({"position": index, "error": str(exc).split(":")[0]})
            continue
        suffix = SUFFIX.search(label)
        declared = int(suffix.group(1)) if suffix else None
        info = by_group.setdefault(ident, {
            "label": SUFFIX.sub("", label).strip(),
            "entries": 0,
            "declared_counts": set(),
        })
        info["entries"] += 1
        if declared is not None:
            info["declared_counts"].add(declared)
        urls_by_group[ident].add(url)
        global_urls[url].append(ident)
        # Header metadata is a *possible* importer-identity hint, not proof
        # that IBO Player merges or excludes this record.
        header_text = record.splitlines()[0].decode("utf-8")
        def attr(name):
            match = re.search(r'(?<![a-z-])' + re.escape(name) +
                              r'="([^"]*)"', header_text, re.I)
            return match.group(1).strip() if match else ""
        metadata_by_group[ident].append({
            "name": record_name(record),
            "tvg_name": attr("tvg-name"),
            "tvg_id": attr("tvg-id"),
            "tvg_logo": attr("tvg-logo"),
        })

    def collision_summary(records, field):
        # Empty metadata is not a collision; separate EPG IDs can legitimately
        # be shared by SD/HD versions, hence report-only behavior.
        index = defaultdict(list)
        for row in records:
            value = row[field].casefold()
            if value:
                index[value].append(row["name"])
        duplicates = [names for names in index.values() if len(names) > 1]
        duplicates.sort(key=lambda names: (-len(names), names[0].casefold()))
        return {
            "groups": len(duplicates),
            "extra_records": sum(len(names) - 1 for names in duplicates),
            "examples": [names[:12] for names in duplicates[:10]],
        }

    categories = {}
    for ident, info in by_group.items():
        count = info["entries"]
        counts = sorted(info["declared_counts"])
        shown = normalized.get(ident)
        categories[ident] = {
            "label": info["label"],
            "file_records": count,
            "distinct_urls_inside_category": len(urls_by_group[ident]),
            "repeated_urls_inside_category": count - len(urls_by_group[ident]),
            "declared_counts": counts,
            "header_matches_records": counts == [count] if counts else None,
            "reported_in_player": shown,
            "unaccounted_player_records": count - shown if shown is not None else None,
            "metadata_repeated_tvg_name": collision_summary(metadata_by_group[ident], "tvg_name"),
            "metadata_repeated_tvg_id": collision_summary(metadata_by_group[ident], "tvg_id"),
            "metadata_repeated_display_name": collision_summary(metadata_by_group[ident], "name"),
        }

    shared = sum(len(groups) > 1 for groups in global_urls.values())
    cross = sum(len(set(groups)) > 1 for groups in global_urls.values())
    return {
        "source": "canonical M3U bytes",
        "total_file_records": len(records),
        "category_count": len(categories),
        "categories": categories,
        "shared_url_groups_anywhere": shared,
        "cross_category_url_groups": cross,
        "malformed_records": malformed,
        "player_count_cause_verified": False,
        "metadata_repeats_are_ibo_parser_proof": False,
        "note": (
            "Player counts are user-reported observations, not a direct IBO API reading. "
            "Repeated URL, hidden categories, stale import or an IBO parser rule are "
            "unverified hypotheses; no channel was modified."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--playlist", type=Path, default=PLAYLIST)
    parser.add_argument("--observed-json", default="{}",
                        help="JSON object of category names to IBO Player counts")
    args = parser.parse_args()
    before = args.playlist.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    result = audit(before, json.loads(args.observed_json))
    if hashlib.sha256(args.playlist.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Unexpected playlist modification during read-only audit")
    result["source_sha256"] = digest
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

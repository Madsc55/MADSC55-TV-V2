#!/usr/bin/env python3
"""Reviewable, no-deletion commands for the ONE canonical MADSC55 IBO playlist.

Everything is offline and SHA-locked. It never probes streams or publishes to main.
A GitHub PR must be reviewed and pass required CI before the result is merged.
"""
import argparse
from collections import Counter, OrderedDict
import hashlib
import json
from pathlib import Path
import re
import sys

from playlist_parts_manager import (
    ROOT, PLAYLIST, PARTS, MANIFEST, MAX_BYTES, split_records, category, checksum, logical,
)

GROUP = re.compile(rb'(group-title\s*=\s*")([^"]*)(")', re.I)
STATUS_PATH = ROOT / "v2/playlists/channel_status.json"
AUTHORIZED = ROOT / "v2/ibo_authorized_change.json"
VALID_ACTIONS = {"move", "copy", "reorder", "archive", "remove", "mark", "recount"}
VALID_STATUSES = {"working", "broken", "unchecked", "unavailable"}
COUNT_SUFFIX = re.compile(r"\s*\(\d+\)\s*$")


def key(label):
    """Identify an existing category despite emoji and stale display counts."""
    label = COUNT_SUFFIX.sub("", label).strip()
    label = re.sub(r"^[^\w]+", "", label).strip()
    return label.casefold()


def record_url(record):
    lines = record.splitlines()
    urls = [line.strip().decode("utf-8") for line in lines[1:]
            if line.strip().startswith((b"http://", b"https://"))]
    if len(urls) != 1:
        raise ValueError("Channel must have exactly one HTTP(S) URL")
    return urls[0]


def record_name(record):
    head = record.split(b"\n", 1)[0].decode("utf-8").rstrip("\r")
    if "," not in head:
        raise ValueError("Channel has no display name")
    return head.rsplit(",", 1)[1].strip()


def record_tvg_name(record):
    head = record.split(b"\n", 1)[0].decode("utf-8")
    found = re.search(r'tvg-name="([^"]+)"', head, re.I)
    return found.group(1).strip() if found else None


def set_label(record, label):
    head, sep, tail = record.partition(b"\n")
    found = GROUP.search(head)
    if not found:
        raise ValueError("Channel lacks group-title")
    encoded = label.encode("utf-8")
    return (head[:found.start(2)] + encoded + head[found.end(2):]
            + sep + tail)


def grouped(data):
    header, records = split_records(data)
    buckets = OrderedDict()
    labels = {}
    closed = set()
    previous = None
    for record in records:
        label = category(record)
        ident = key(label)
        if ident != previous:
            if ident in closed:
                raise ValueError("Category sections must be contiguous")
            if previous is not None:
                closed.add(previous)
        buckets.setdefault(ident, []).append(record)
        labels.setdefault(ident, COUNT_SUFFIX.sub("", label).strip())
        previous = ident
    if len(buckets) < 2:
        raise ValueError("Expected existing canonical category structure")
    return header, buckets, labels


def lookup_category(query, buckets):
    if not isinstance(query, str) or not query.strip():
        raise ValueError("An existing category name is required")
    ident = key(query)
    if ident not in buckets:
        raise ValueError("Unknown category: " + query)
    return ident


def resolve_selectors(buckets, command):
    choices = command.get("channels")
    window = command.get("range")
    if window is not None:
        if choices is not None:
            raise ValueError("Specify either range or channels, not both")
        if not isinstance(window, dict) or set(window) != {"start", "end"}:
            raise ValueError("Range must contain start and end")
        first, last = window["start"], window["end"]
        if (type(first) is not int or type(last) is not int
                or first < 1 or last < first or last - first + 1 > 2500):
            raise ValueError("Range must select 1..2500 consecutive channels")
        if not isinstance(command.get("source"), str):
            raise ValueError("Range requires an existing source category")
        choices = [{"position": ordinal} for ordinal in range(first, last + 1)]
    if not isinstance(choices, list) or not choices or len(choices) > 2500:
        raise ValueError("Select between 1 and 2,500 channels")
    selected = []
    seen = set()
    fallback = command.get("source")
    for item in choices:
        selector = {"name": item} if isinstance(item, str) else item
        if not isinstance(selector, dict):
            raise ValueError("Bad channel selector")
        src = selector.get("category", fallback)
        filters = [name for name in ("name", "position", "url") if name in selector]
        if len(filters) != 1:
            raise ValueError("Select by exactly one of name, position or URL")
        field = filters[0]
        if field == "position":
            if src is None or type(selector[field]) is not int or selector[field] < 1:
                raise ValueError("Ordinal requires category and positive integer")
            src_key = lookup_category(src, buckets)
            ordinal = selector[field]
            matches = [(src_key, ordinal, buckets[src_key][ordinal - 1])] if ordinal <= len(buckets[src_key]) else []
        else:
            if src is not None:
                src_key = lookup_category(src, buckets)
                candidates = [(src_key, n, record) for n, record in enumerate(buckets[src_key], 1)]
            else:
                candidates = [(group, n, record)
                              for group, records in buckets.items()
                              for n, record in enumerate(records, 1)]
            matches = []
        if field == "name":
            phrase = selector[field]
            if not isinstance(phrase, str) or not phrase.strip():
                raise ValueError("Invalid channel name")
            matches = [part for part in candidates
                       if phrase.casefold().strip() in
                       (record_name(part[2]).casefold(), (record_tvg_name(part[2]) or "").casefold())]
        else:
            matches = [part for part in candidates if record_url(part[2]) == selector[field]]
        if len(matches) != 1:
            raise ValueError("Channel selection must match exactly one record: " + repr(selector))
        group, number, record = matches[0]
        ident = (group, number)
        if ident in seen:
            raise ValueError("Duplicate channel selection")
        seen.add(ident)
        selected.append((group, number, record))
    return selected


def _retag_and_recount(buckets, labels):
    counts = {group: len(records) for group, records in buckets.items()}
    if any(not count for count in counts.values()):
        raise ValueError("Empty categories are forbidden: keep category inventory")
    out = []
    for group, records in buckets.items():
        label = labels[group] + " (" + str(counts[group]) + ")"
        out.extend(set_label(record, label) for record in records)
    return out, counts


def operate(data, command, statuses=None):
    """Return (new_playlist_bytes, new_statuses, report). No I/O or writes."""
    if not isinstance(command, dict):
        raise ValueError("Command must be a JSON object")
    if command.get("expected_sha256") != checksum(data):
        raise ValueError("Playlist SHA changed; refuse stale operation")
    action = command.get("action")
    if action not in VALID_ACTIONS:
        raise ValueError("Unsupported command")
    header, buckets, labels = grouped(data)
    before = {labels[k]: len(v) for k, v in buckets.items()}
    selected = [] if action == "recount" else resolve_selectors(buckets, command)
    after_statuses = dict(statuses or {})
    if action == "mark":
        status = command.get("status")
        if status not in VALID_STATUSES:
            raise ValueError("Use a supported working/broken/unavailable/unchecked status")
        for _, _, record in selected:
            after_statuses[hashlib.sha256(record_url(record).encode("utf-8")).hexdigest()] = {
                "status": status, "channel": record_name(record),
            }
        return data, after_statuses, {
            "action": action, "selected": [record_name(r) for _, _, r in selected],
            "before": before, "after": before, "deleted": 0,
        }
    if action != "recount":
        target = command.get("target", "ANA ARŞİV" if action in {"archive", "remove"} else None)
        if action == "reorder":
            source_groups = {group for group, _, _ in selected}
            if len(source_groups) != 1:
                raise ValueError("Reordering requires exactly one source category")
            target_id = source_groups.pop()
        else:
            target_id = lookup_category(target, buckets)
        if action in {"archive", "remove"} and target_id not in {
            key("ANA ARŞİV"), key("TÜRK ARŞİVİ"), key("YABANCI ARŞİVİ")
        }:
            raise ValueError("Archive destination must be an existing archive")
        if action in {"move", "archive", "remove", "reorder"}:
            for group, ordinal, _ in sorted(selected, key=lambda p: (p[0], -p[1])):
                buckets[group].pop(ordinal - 1)
            if action != "reorder" and any(group == target_id for group, _, _ in selected):
                raise ValueError("Use reorder for channels already in target category")
            insert = [set_label(record, labels[target_id]) for _, _, record in selected]
        elif action == "copy":
            if not key(labels[target_id]).startswith(key("FAVORİLER")):
                raise ValueError("Copy is restricted to existing FAVORİLER categories")
            target_records = buckets[target_id]
            insert = []
            for group, _, record in selected:
                url = record_url(record)
                existing = [i for i, r in enumerate(target_records) if record_url(r) == url]
                if len(existing) > 1:
                    raise ValueError("Duplicate target favorite URL")
                if existing:
                    insert.append(target_records.pop(existing[0]))
                else:
                    insert.append(set_label(record, labels[target_id]))
        position = command.get("position", len(buckets[target_id]) + 1)
        if type(position) is not int or not 1 <= position <= len(buckets[target_id]) + 1:
            raise ValueError("Target position is out of range")
        buckets[target_id][position - 1:position - 1] = insert
        if action == "remove" and command.get("status") is not None:
            if command["status"] not in VALID_STATUSES:
                raise ValueError("Unrecognized stream status")
            for _, _, record in selected:
                after_statuses[hashlib.sha256(record_url(record).encode("utf-8")).hexdigest()] = {
                    "status": command["status"], "channel": record_name(record),
                }
    rebuilt, after = _retag_and_recount(buckets, labels)
    output = header + b"".join(rebuilt)
    old_records = split_records(data)[1]
    new_records = split_records(output)[1]
    old_urls, new_urls = Counter(map(record_url, old_records)), Counter(map(record_url, new_records))
    if action == "copy":
        if any(new_urls[url] < n for url, n in old_urls.items()):
            raise ValueError("Copy lost an original URL")
    elif old_urls != new_urls:
        raise ValueError("An operation lost or added a channel URL")
    if not output.startswith(header):
        raise ValueError("Playlist header changed")
    return output, after_statuses, {
        "action": action, "selected": [record_name(r) for _, _, r in selected],
        "before": before, "after": {labels[k]: v for k, v in after.items()},
        "before_total": len(old_records), "after_total": len(new_records), "deleted": 0,
    }


def parts_for(data, old_sha):
    """Prepare replacements for the current parts; does not touch disk."""
    header, records = split_records(data)
    entries, payloads = [], {}
    buffer, size, previous = [], 0, None
    chunks = []
    for record in records:
        group = category(record)
        if len(record) > MAX_BYTES:
            raise ValueError("Oversized channel record")
        if buffer and (group != previous or size + len(record) > MAX_BYTES):
            chunks.append((previous, b"".join(buffer), len(buffer)))
            buffer, size = [], 0
        buffer.append(record)
        size += len(record)
        previous = group
    if buffer:
        chunks.append((previous, b"".join(buffer), len(buffer)))
    for i, (group, payload, n) in enumerate(chunks):
        name = f"{i:04d}.m3u"
        payloads[name] = payload
        entries.append({"file": name, "group": logical(group), "records": n,
                        "sha256": checksum(payload)})
    manifest = {"version": 1, "header_hex": header.hex(), "source_sha256": old_sha,
                "total_records": len(records), "entries": entries}
    return payloads, manifest


def run_cli():
    parser = argparse.ArgumentParser(description="Review a no-deletion playlist command")
    parser.add_argument("--request", type=Path, required=True, help="JSON command file")
    parser.add_argument("--apply", action="store_true", help="write a reviewable local PR diff")
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    old = PLAYLIST.read_bytes()
    status = json.loads(STATUS_PATH.read_text(encoding="utf-8")) if STATUS_PATH.exists() else {}
    if not isinstance(status, dict):
        raise ValueError("Bad status index")
    updated, new_status, report = operate(old, request, status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.apply:
        return
    request_text = request.get("request", "")
    if not isinstance(request_text, str) or len(request_text.strip()) < 12:
        raise ValueError("Original user authorization must be recorded (12+ chars)")
    if updated != old:
        payloads, manifest = parts_for(updated, checksum(old))
        if sum(e["records"] for e in manifest["entries"]) != len(split_records(updated)[1]):
            raise ValueError("Parts count mismatch")
        PARTS.mkdir(parents=True, exist_ok=True)
        for name, payload in payloads.items():
            (PARTS / name).write_bytes(payload)
        for part in PARTS.glob("*.m3u"):
            if part.name not in payloads:
                part.unlink()
        MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        PLAYLIST.write_bytes(updated)
        authorized = {
            "base_sha256": checksum(old), "result_sha256": checksum(updated),
            "operation": {"recount": "category", "archive": "move", "remove": "move", "reorder": "reorder"}.get(
                request["action"], request["action"]),
            "request": request_text,
            "channels": report["selected"][:2000] or ["All category count labels"],
        }
        AUTHORIZED.write_text(json.dumps(authorized, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
    if new_status != status:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATUS_PATH.write_text(json.dumps(new_status, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")


if __name__ == "__main__":
    run_cli()

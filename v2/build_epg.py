#!/usr/bin/env python3
"""Independent XMLTV guide builder. Never writes to the protected playlist."""
import copy
import gzip
import io
import json
import pathlib
import re
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from epg_integrity import parse_xmltv_time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
OUT = ROOT / "madsc-epg.xml"

def norm(value):
    value = (value or "").casefold().replace("ı", "i")
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", "", value)
    return re.sub(r"(?:1080p|720p|2160p|4k|uhd|fhd|hd|sd|hevc|h265|h264|yedek|backup|live|canli|turkiye|tr)+$", "", value)

def attr(line, key):
    match = re.search(r'\b' + re.escape(key) + r'="([^"]*)"', line)
    return match.group(1) if match else ""

def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-EPG/2"})
    with urllib.request.urlopen(req, timeout=90) as response:
        data = response.read(120_000_001)
    if len(data) > 120_000_000:
        raise ValueError("compressed feed too large")
    if data[:2] == b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            data = stream.read(120_000_001)
    if len(data) > 120_000_000:
        raise ValueError("expanded feed too large")
    # Reject entity declarations before XML parsing, including gzipped feeds.
    # This guide builder must not be a weaker entry point than epg_integrity.
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("XMLTV DTD and ENTITY declarations are not allowed")
    return ET.fromstring(data)

def ingest_xmltv_feed(root, channels, schedules, ambiguous_ids):
    """Merge declarations only when a channel ID belongs to one feed.

    Two unrelated publishers can reuse the same XMLTV ID. Never concatenate
    their programme schedules or use an undeclared programme channel as proof
    of a broadcaster identity. Ambiguous IDs are removed after all feeds.
    """
    declarations = Counter(node.get("id") for node in root.findall("channel")
                           if node.get("id"))
    collisions = {cid for cid, n in declarations.items()
                  if n != 1 or cid in channels}
    ambiguous_ids.update(collisions)
    for cid in collisions:
        channels.pop(cid, None)
        schedules.pop(cid, None)
    unique = {cid for cid, n in declarations.items()
              if n == 1 and cid not in ambiguous_ids}
    for channel in root.findall("channel"):
        cid = channel.get("id")
        if cid in unique and cid not in channels:
            channels[cid] = channel
    accepted = rejected = 0
    for programme in root.findall("programme"):
        cid = programme.get("channel")
        if cid in unique:
            schedules[cid].append(programme)
            accepted += 1
        else:
            rejected += 1
    return {"accepted_programmes": accepted, "rejected_programmes": rejected,
            "conflicting_ids": len(collisions)}


def select_epg_source(tvgid, tvgname, display, names, schedules):
    """Only exact IDs or unambiguous name matches may supply programmes."""
    if tvgid and tvgid in schedules:
        return tvgid, False
    candidates = set()
    for label in (tvgid, tvgname, display):
        key = norm(label)
        if key:
            candidates.update(names.get(key, ()))
    candidates.intersection_update(schedules)
    if len(candidates) == 1:
        return next(iter(candidates)), False
    return None, len(candidates) > 1


def programme_in_window(programme, start_limit, end_limit):
    """Require valid XMLTV timezone and positive programme duration before export."""
    try:
        start = parse_xmltv_time(programme.get("start", ""))
        stop = parse_xmltv_time(programme.get("stop", ""))
    except (ValueError, TypeError, AttributeError):
        return False
    return stop > start and start_limit <= start <= end_limit


def main():
    entries = []
    for line in PLAYLIST.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("#EXTINF"):
            entries.append((attr(line, "tvg-id"), attr(line, "tvg-name") or line.rsplit(",", 1)[-1], line.rsplit(",", 1)[-1]))
    sources = json.loads((ROOT / "v2/epg_sources.json").read_text())["sources"]
    feed_channels = {}
    schedules = defaultdict(list)
    results = []
    ambiguous_ids = set()
    for url in sources:
        try:
            root = download(url)
            if root.tag != "tv":
                raise ValueError("not XMLTV")
            counts = ingest_xmltv_feed(root, feed_channels, schedules, ambiguous_ids)
            results.append({"source": url, "status": "ok", **counts})
        except Exception as exc:
            # Avoid printing signed feed URLs or confidential query tokens.
            results.append({"source": url.split("?")[0], "status": "failed",
                            "error_type": type(exc).__name__})
    # The first feed's observations become untrusted if another feed later
    # claims the same ID; exclude both before all matching and exports.
    for cid in ambiguous_ids:
        feed_channels.pop(cid, None)
        schedules.pop(cid, None)
    if not schedules:
        raise SystemExit("No unambiguous EPG source provided programmes: " + json.dumps(results))
    names = defaultdict(set)
    for cid, ch in feed_channels.items():
        if cid not in schedules:
            continue
        for label in [cid] + [x.text or "" for x in ch.findall("display-name")]:
            key = norm(label)
            if key:
                names[key].add(cid)
    mapping = defaultdict(set)
    matched = 0
    ambiguous = 0
    for index, (tvgid, tvgname, display) in enumerate(entries):
        source_id, is_ambiguous = select_epg_source(tvgid, tvgname, display, names, schedules)
        if is_ambiguous:
            ambiguous += 1
        if not source_id:
            continue
        target = tvgid or "madsc-v2-" + str(index)
        mapping[source_id].add(target)
        matched += 1
    result = ET.Element("tv", {"generator-info-name": "MADSC55-TV-V2"})
    used = set()
    for index, (tvgid, tvgname, display) in enumerate(entries):
        target = tvgid or "madsc-v2-" + str(index)
        if target not in used and any(target in targets for targets in mapping.values()):
            channel = ET.SubElement(result, "channel", {"id": target})
            ET.SubElement(channel, "display-name").text = tvgname or display
            used.add(target)
    now = datetime.now(timezone.utc)
    start_limit, end_limit = now - timedelta(hours=12), now + timedelta(days=4)
    seen = set()
    written = 0
    for cid, targets in mapping.items():
        for prog in schedules[cid]:
            if not programme_in_window(prog, start_limit, end_limit):
                continue
            for target in targets:
                key = (target, prog.get("start"), prog.get("stop"), prog.findtext("title"))
                if key in seen:
                    continue
                seen.add(key)
                node = copy.deepcopy(prog)
                node.set("channel", target)
                result.append(node)
                written += 1
    if written == 0:
        raise SystemExit("No matching programmes in current date window: " + json.dumps(results))
    temp = ROOT / "madsc-epg.xml.tmp"
    ET.ElementTree(result).write(temp, encoding="utf-8", xml_declaration=True)
    ET.parse(temp)
    temp.replace(OUT)
    report = {"playlist_entries": len(entries), "matched_entries": matched,
              "ambiguous_entries_skipped": ambiguous,
              "conflicting_xmltv_channel_ids_rejected": len(ambiguous_ids),
              "channels": len(used),
              "programmes": written, "epg_bytes": OUT.stat().st_size, "sources": results}
    (ROOT / "v2/epg-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()

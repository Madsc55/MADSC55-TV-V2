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
    return ET.fromstring(data)

def main():
    entries = []
    for line in PLAYLIST.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("#EXTINF"):
            entries.append((attr(line, "tvg-id"), attr(line, "tvg-name") or line.rsplit(",", 1)[-1], line.rsplit(",", 1)[-1]))
    sources = json.loads((ROOT / "v2/epg_sources.json").read_text())["sources"]
    feed_channels = {}
    schedules = defaultdict(list)
    results = []
    for url in sources:
        try:
            root = download(url)
            if root.tag != "tv":
                raise ValueError("not XMLTV")
            for channel in root.findall("channel"):
                cid = channel.get("id")
                if cid and cid not in feed_channels:
                    feed_channels[cid] = channel
            count = 0
            for programme in root.findall("programme"):
                cid = programme.get("channel")
                if cid:
                    schedules[cid].append(programme)
                    count += 1
            results.append({"source": url, "status": "ok", "programmes": count})
        except Exception as exc:
            results.append({"source": url, "status": "failed", "reason": str(exc)[:180]})
    if not schedules:
        raise SystemExit("No EPG source provided programmes: " + json.dumps(results))
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
    for index, (tvgid, tvgname, display) in enumerate(entries):
        candidates = set()
        if tvgid in schedules:
            candidates.add(tvgid)
        if not candidates:
            for label in (tvgid, tvgname, display):
                candidates.update(names.get(norm(label), set()))
        if not candidates:
            continue
        source_id = max(candidates, key=lambda cid: (len(schedules[cid]), cid))
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
            stamp = prog.get("start", "")
            try:
                dt = datetime.strptime(stamp[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
                tz = re.search(r"([+-])(\d{2})(\d{2})$", stamp.strip())
                if tz:
                    shift = timedelta(hours=int(tz.group(2)), minutes=int(tz.group(3)))
                    dt += -shift if tz.group(1) == "+" else shift
                if not start_limit <= dt <= end_limit:
                    continue
            except ValueError:
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
    report = {"playlist_entries": len(entries), "matched_entries": matched, "channels": len(used), "programmes": written, "epg_bytes": OUT.stat().st_size, "sources": results}
    (ROOT / "v2/epg-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build V2 XMLTV independently from public guide sources; never edit playlist."""
import gzip
import json
import pathlib
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
OUT = ROOT / "madsc-epg.xml"
MAX_SOURCE_BYTES = 35_000_000

def load(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"MADSC55-TV-V2/1.0"}), timeout=40) as response:
        raw = response.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("oversized source")
    if url.endswith(".gz") or raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return ET.fromstring(raw)

def main():
    import re
    playlist = PLAYLIST.read_text(encoding="utf-8-sig")
    ids = set(re.findall(r'tvg-id="([^"]+)"', playlist))
    if not ids:
        raise SystemExit("Playlist has no tvg-id values")
    sources = json.loads((ROOT / "v2/epg_sources.json").read_text())["sources"]
    root = ET.Element("tv", {"generator-info-name":"MADSC55-TV-V2"})
    channels = {}
    programmes = []
    seen = set()
    ok, errors = 0, []
    for url in sources:
        try:
            feed = load(url)
            if feed.tag != "tv":
                raise ValueError("not XMLTV")
            for channel in feed.findall("channel"):
                cid = channel.get("id", "")
                if cid in ids and cid not in channels:
                    channels[cid] = channel
            for programme in feed.findall("programme"):
                cid = programme.get("channel", "")
                if cid not in ids:
                    continue
                key = (cid, programme.get("start"), programme.get("stop"))
                if key in seen:
                    continue
                seen.add(key)
                programmes.append(programme)
            ok += 1
        except Exception as exc:
            errors.append({"source":url,"error":type(exc).__name__})
    if ok == 0 or not programmes:
        raise SystemExit("No usable EPG; refusing to replace existing guide")
    for channel in channels.values():
        root.append(channel)
    for programme in programmes:
        if programme.get("channel") in channels:
            root.append(programme)
    if not root.findall("programme"):
        raise SystemExit("No programmes with channel metadata")
    tmp = OUT.with_suffix(".xml.tmp")
    ET.ElementTree(root).write(tmp, encoding="utf-8", xml_declaration=True)
    ET.parse(tmp)
    tmp.replace(OUT)
    report = {"successful_sources":ok,"failed_sources":errors,"channels":len(channels),"programmes":len(root.findall("programme"))}
    (ROOT / "v2/epg-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))

if __name__ == "__main__":
    main()

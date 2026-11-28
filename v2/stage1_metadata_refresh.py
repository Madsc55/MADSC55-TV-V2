#!/usr/bin/env python3
"""Read-only live metadata refresh. Outputs current XMLTV and exact evidence, never M3U.

Directory entries are hints. Empty fields can receive a proposal only after
an independent publisher page corroborates the exact stream URL and name.
The original playlist remains SHA-bound to the running foreign audit.
"""
import argparse
import gzip
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from v2.playlist_parts_manager import split_records, category
from v2.channel_command_engine import record_url
from v2.package2_evidence import assets, https_asset
from v2.shared_url_safe_probe import vetted_target, PinnedHTTPS
from v2.build_epg import programme_in_window
from v2.epg_integrity import parse_xmltv_time

ROOT = Path(__file__).resolve().parents[1]
PLAYLIST = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
API = "https://iptv-org.github.io/api/"
# Explicitly configured public feed URLs; never follow feed-supplied links.
FEEDS = (
    "https://iptv-epg.org/files/epg-tr.xml",
    "https://iptv-epg.org/files/epg-de.xml",
    "https://iptv-epg.org/files/epg-fr.xml",
    "https://iptv-epg.org/files/epg-gb.xml",
    "https://iptv-epg.org/files/epg-se.xml",
    "https://iptv-epg.org/files/epg-it.xml",
    "https://iptv-epg.org/files/epg-es.xml",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
)
MAX_PUBLISHER_PAGES = 200

def digest(data):
    return hashlib.sha256(data).hexdigest()

def public_asset(url):
    if not https_asset(url):
        return False
    try:
        p = urlsplit(url)
        return not p.query and not p.fragment and not re.search(r'["<>]', url)
    except ValueError:
        return False

def fetch(url, limit, timeout=12):
    """Pinned public IP HTTPS, no redirects, credentials, query, range or truncation."""
    if not public_asset(url):
        raise ValueError("UNSAFE_ASSET_URL")
    scheme, host, port, ip, path = vetted_target(url)
    if scheme != "https" or port != 443:
        raise ValueError("UNSAFE_ASSET_TRANSPORT")
    connection = PinnedHTTPS(host, port, ip, timeout)
    try:
        connection.request("GET", path, headers={"Accept-Encoding": "identity",
            "User-Agent": "MADSC55-TV-V2-Metadata/1.0"})
        res = connection.getresponse()
        if res.status != 200 or res.getheader("Content-Encoding", "identity").lower() != "identity":
            raise ValueError("ASSET_HTTP_OR_ENCODING")
        length = res.getheader("Content-Length")
        if length is not None and (not length.isdecimal() or int(length) > limit):
            raise ValueError("ASSET_LENGTH_LIMIT")
        data = res.read(limit + 1)
        if not data or len(data) > limit or (length is not None and len(data) != int(length)):
            raise ValueError("ASSET_BODY_LIMIT")
        return data
    finally:
        connection.close()

def attr(head, key):
    matches = re.findall(r'(?<![\w-])' + re.escape(key) + r'="([^"]*)"', head)
    if len(matches) > 1:
        raise ValueError("DUPLICATE_METADATA_FIELD")
    return matches[0] if matches else ""

def playlist_rows(raw):
    _, blocks = split_records(raw)
    result = []
    for pos, block in enumerate(blocks, 1):
        try:
            head = block.splitlines()[0].decode("utf-8")
            result.append({"position":pos, "record_sha256":digest(block),
                "url":record_url(block), "group":category(block),
                "tvg_id":attr(head,"tvg-id"), "logo":attr(head,"tvg-logo")})
        except (ValueError, UnicodeError):
            # Preserve the record and explicitly report it as unparseable.
            result.append({"position":pos,"record_sha256":digest(block),
                "invalid":True})
    return result

def feed_xml(data):
    if data.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            data = stream.read(100_000_001)
    if len(data) > 100_000_000 or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("XMLTV_SIZE_OR_DTD")
    root = ET.fromstring(data)
    if root.tag != "tv":
        raise ValueError("NOT_XMLTV")
    return root

def collect_feed(root, wanted, now):
    """Exact unique declarations, with at least one currently airing programme."""
    counts = Counter(n.get("id") for n in root.findall("channel") if n.get("id") in wanted)
    declared = {cid for cid,n in counts.items() if n == 1}
    schedules = defaultdict(list)
    current = set()
    for p in root.findall("programme"):
        cid = p.get("channel")
        if cid not in declared or not programme_in_window(p, now, now + timedelta(days=4)):
            continue
        start, stop = parse_xmltv_time(p.get("start")), parse_xmltv_time(p.get("stop"))
        if start <= now < stop:
            current.add(cid)
        schedules[cid].append(p)
    return set(counts), {cid:schedules[cid] for cid in current}

def directory_index(channels, streams, logos):
    """Feed-specific, exact URL joins; conflicting or unknown mappings fail closed."""
    by_id = defaultdict(list)
    by_url = defaultdict(set)
    by_logo = defaultdict(list)
    for c in channels:
        if isinstance(c,dict) and isinstance(c.get("id"),str):
            by_id[c["id"]].append(c)
    for s in streams:
        if isinstance(s,dict) and isinstance(s.get("url"),str):
            cid, fid = s.get("channel"), s.get("feed")
            # Unknown or untyped claims must not disappear from ambiguity checks.
            if not isinstance(cid,str) or not cid or (fid is not None and not isinstance(fid,str)):
                by_url[s["url"]].add((None,None))
            else:
                by_url[s["url"]].add((cid,fid or None))
    for item in logos:
        if isinstance(item,dict) and isinstance(item.get("channel"),str):
            by_logo[item["channel"]].append(item)
    return by_id,by_url,by_logo

def directory_match(row, index):
    by_id,by_url,by_logo = index
    claims = by_url.get(row["url"],set())
    if len(claims) != 1:
        return None
    cid,fid = next(iter(claims))
    if cid is None or len(by_id.get(cid,[])) != 1:
        return None
    c = by_id[cid][0]
    if c.get("closed") or c.get("replaced_by") or not public_asset(c.get("website")):
        return None
    expected = cid + ("@" + fid if fid else "")
    if row["tvg_id"] and row["tvg_id"] != expected:
        return None
    labels = {c.get("name")} | {n for n in (c.get("alt_names") or []) if isinstance(n,str)}
    labels = {n.strip() for n in labels if isinstance(n,str) and n.strip()}
    if not labels:
        return None
    logos = {l["url"] for l in by_logo[cid] if l.get("in_use") is True
             and l.get("feed") in (None,"",fid) and public_asset(l.get("url"))}
    return expected,c["website"],labels,logos

class PublisherPage(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.title = False
        self.labels = set()
        self.streams = set()
        self.images = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self.title = True
        if tag == "meta" and a.get("property") == "og:title" and a.get("content"):
            self.labels.add(a["content"].strip())
        if tag in ("a","source","video"):
            value = a.get("href") if tag == "a" else a.get("src")
            if value:
                self.streams.add(urljoin(self.base,value))
        if tag == "img" and a.get("src") and a.get("alt"):
            self.images.add((urljoin(self.base,a["src"]),a["alt"].strip()))
    def handle_endtag(self, tag):
        if tag == "title":
            self.title = False
    def handle_data(self, data):
        if self.title and data.strip():
            self.labels.add(data.strip())

def confirm(row, match, active, read=fetch, decode_logo=None):
    """Never set verified flags on directory metadata alone."""
    expected, site, labels, logo_urls = match
    data = read(site, 2_000_000, 6)
    page = PublisherPage(site)
    page.feed(data.decode("utf-8",errors="strict"))
    if not labels.intersection(page.labels) or row["url"] not in page.streams:
        return {}
    evidence = {"identity_evidence_verified":True,"observed_channel_id":expected}
    if not row["tvg_id"] and expected in active:
        evidence["epg"] = {"verified":True,"channel_id":expected,
                           "tvg_id":expected,"source_url":active[expected][0]}
    if not row["logo"] and decode_logo is not None:
        official = {url for url,alt in page.images if alt in labels and url in logo_urls
                    and urlsplit(url).hostname == urlsplit(site).hostname}
        if len(official) == 1:
            url = next(iter(official))
            try:
                payload = read(url, 4_000_000, 6)
                decode_logo(payload)
                evidence["logo"] = {"official_origin_verified":True,"content_verified":True,
                    "channel_id":expected,"url":url,"official_source_url":site,
                    "content_sha256":digest(payload)}
            except Exception:
                # A failed image must not erase separately verified EPG.
                pass
    values = assets(expected,evidence)
    changes = {key:val for key,val in values.items() if val is not None}
    if not changes:
        return {}
    return {"position":row["position"],"record_sha256":row["record_sha256"],
            "url_sha256":digest(row["url"].encode()),"changes":changes,
            "channel_id":expected,"publisher_page":site,
            "publisher_page_sha256":digest(data),"evidence":evidence}

def image_decode(data):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 4_000_000
    with Image.open(io.BytesIO(data)) as im:
        if im.format not in {"PNG","JPEG","GIF","WEBP"} or im.width * im.height > 4_000_000:
            raise ValueError("UNSUPPORTED_LOGO")
        im.verify()
    with Image.open(io.BytesIO(data)) as im:
        im.load()

def build_guide(active, rows, proposals):
    existing = {r.get("tvg_id") for r in rows if r.get("tvg_id") in active}
    new = {p["changes"]["tvg_id"] for p in proposals if p["changes"].get("tvg_id")}
    root = ET.Element("tv",{"generator-info-name":"MADSC55-TV-V2 exact metadata refresh"})
    ids = sorted(existing | new)
    for cid in ids:
        c = ET.SubElement(root,"channel",{"id":cid})
        ET.SubElement(c,"display-name").text = cid
    seen = set()
    for cid in ids:
        for p in active[cid][1]:
            key = (cid,p.get("start"),p.get("stop"),p.findtext("title"))
            if key in seen:
                continue
            seen.add(key)
            node = ET.SubElement(root,"programme",{"channel":cid,"start":p.get("start"),"stop":p.get("stop")})
            for name in ("title","sub-title","desc","category","episode-num"):
                for item in p.findall(name):
                    val = "".join(item.itertext()).strip()
                    if val:
                        ET.SubElement(node,name).text = val[:16000]
    return root, len(existing), len(new), len(seen)

def run(output):
    raw = PLAYLIST.read_bytes()
    rows = playlist_rows(raw)
    valid = [r for r in rows if not r.get("invalid")]
    now = datetime.now(timezone.utc)
    sources = []
    candidates = []
    try:
        metadata = []
        for name in ("channels","streams","logos"):
            payload = fetch(API + name + ".json",25_000_000)
            obj = json.loads(payload)
            if not isinstance(obj,list):
                raise ValueError("BAD_DIRECTORY")
            metadata.append(obj)
            sources.append({"source":API+name+".json","sha256":digest(payload),"status":"ok"})
        index = directory_index(*metadata)
        for row in valid:
            if not row["tvg_id"] or not row["logo"]:
                match = directory_match(row,index)
                if match is not None:
                    candidates.append((row,match))
    except Exception as exc:
        sources.append({"source":"iptv-org-directory","status":"failed","error":type(exc).__name__})
        candidates = []
    wanted = {r["tvg_id"] for r in valid if r["tvg_id"]}
    wanted.update(m[0] for _,m in candidates)
    declarations = Counter()
    active = {}
    for url in FEEDS:
        try:
            data = fetch(url,30_000_000,20)
            claimed, fresh = collect_feed(feed_xml(data),wanted,now)
            declarations.update(claimed)
            for cid,progs in fresh.items():
                active[cid] = (url,progs)
            sources.append({"source":url,"status":"ok","sha256":digest(data),"fresh_matching_ids":len(fresh)})
        except Exception as exc:
            sources.append({"source":url,"status":"failed","error":type(exc).__name__})
    # Conflicting declarations across feeds are not silently merged.
    active = {cid:val for cid,val in active.items() if declarations[cid] == 1}
    eligible = [(r,m) for r,m in candidates if (not r["tvg_id"] and m[0] in active)
                or (not r["logo"] and m[3])]
    # Deduplicate exact identical publisher checks by stream and channel, without
    # conflating the positions of duplicate playlist records.
    grouped = defaultdict(list)
    for r,m in eligible:
        grouped[(r["url"],m[0],r["tvg_id"],r["logo"])].append((r,m))
    selected = list(grouped.values())[:MAX_PUBLISHER_PAGES]
    def check(group):
        row,match = group[0]
        try:
            p = confirm(row,match,active,decode_logo=image_decode)
            if not p:
                return []
            return [dict(p,position=r["position"],record_sha256=r["record_sha256"]) for r,_ in group]
        except Exception:
            return []
    with ThreadPoolExecutor(max_workers=4) as pool:
        proposals = [p for group in pool.map(check,selected) for p in group]
    proposals.sort(key=lambda p:p["position"])
    guide,existing,new,programmes = build_guide(active,valid,proposals)
    if PLAYLIST.read_bytes() != raw:
        raise RuntimeError("PLAYLIST_CHANGED_DURING_REFRESH")
    report = {"schema":1,"created_utc":now.isoformat(),"playlist_sha256":digest(raw),
              "records":len(rows),"unparseable_records":len(rows)-len(valid),
              "missing_tvg_id":sum(not r["tvg_id"] for r in valid),
              "missing_logo":sum(not r["logo"] for r in valid),
              "directory_exact_candidates":len(candidates),
              "publisher_checks_selected":len(selected),"publisher_checks_pending":len(grouped)-len(selected),
              "existing_exact_current_epg_ids":existing,"proposed_new_epg_ids":new,
              "proposed_tvg_id_records":sum("tvg_id" in p["changes"] for p in proposals),
              "proposed_logo_records":sum("logo" in p["changes"] for p in proposals),
              "programmes":programmes,"sources":sources,
              "playlist_records_modified":0,"published":False,
              "policy":"Exact identity evidence only; no automatic playlist mutation; proposals require reviewed SHA-bound application."}
    output.mkdir(parents=True,exist_ok=False)
    (output/"metadata-report.json").write_text(json.dumps(report,indent=2)+"\n")
    (output/"verified-metadata-proposals.json").write_text(json.dumps({"playlist_sha256":digest(raw),"proposals":proposals},indent=2)+"\n")
    if programmes:
        ET.ElementTree(guide).write(output/"madsc-epg.xml",encoding="utf-8",xml_declaration=True)
    print(json.dumps({k:v for k,v in report.items() if k != "sources"}))
    if not programmes:
        raise SystemExit("No unambiguous currently airing exact-ID guide; no XMLTV published")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args().output)

if __name__ == "__main__":
    main()

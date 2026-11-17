#!/usr/bin/env python3
"""Batch-fill YEDEKLER logos using uniquely identified IPTV-org channels.
Never touch entries outside YEDEKLER; ambiguous matches are skipped.
"""
import concurrent.futures, json, re, urllib.request
from collections import defaultdict
from pathlib import Path

PLAYLIST = Path("MADSC55_TV_IBO_CALISANLAR_TEST.m3u8")
REPORT = Path("backup_logo_report.json")
HEADERS = {"User-Agent": "MADSC55-TV-V2-logo-audit/1.0"}
def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as res:
        return json.load(res)
def norm(s):
    s = s.casefold().replace("ı","i")
    s = re.sub(r"(?i)\b(?:tr|turkey|turkiye|hd|sd|fhd|uhd|4k|1080p|720p|576p|live|canli)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)
def valid(url):
    if not url.startswith("https://"): return False
    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as r:
            return 200 <= r.status < 400 and r.headers.get("Content-Type","").split(";")[0].lower().startswith(("image/","application/octet-stream"))
    except Exception:
        return False

channels = fetch("https://iptv-org.github.io/api/channels.json")
logos = fetch("https://iptv-org.github.io/api/logos.json")
by_id = {c["id"]:c for c in channels if c.get("id")}
by_name = defaultdict(set)
by_name_global = defaultdict(set)
for c in channels:
    if c.get("id") and c.get("name"):
        by_name_global[norm(c["name"])].add(c["id"])
        if c.get("country") == "TR":
            by_name[norm(c["name"])].add(c["id"])
logo_by_id = defaultdict(set)
for item in logos:
    if item.get("channel") and item.get("url") and item["url"].startswith("https://"):
        logo_by_id[item["channel"]].add(item["url"])
original = PLAYLIST.read_text(encoding="utf-8")
lines = original.splitlines(keepends=True)
candidates = {}
ambiguous = 0
missing = 0
for i, line in enumerate(lines):
    if not line.startswith("#EXTINF") or 'group-title="🗂️ YEDEKLER' not in line or re.search(r'tvg-logo="[^"]+"',line): continue
    missing += 1
    name = line.rstrip("\r\n").split(",",1)[-1].strip()
    tvgid = re.search(r'tvg-id="([^"]+)"',line)
    ids = set()
    if tvgid and tvgid.group(1) in by_id: ids.add(tvgid.group(1))
    if not ids:
        ids = by_name.get(norm(name),set())
    if not ids:
        ids = by_name_global.get(norm(name),set())
    if len(ids)!=1:
        ambiguous += 1
        continue
    options = set().union(*(logo_by_id.get(cid,set()) for cid in ids))
    if len(options)==1: candidates[i] = next(iter(options))
    else: ambiguous += 1

urls = sorted(set(candidates.values()))
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
    results = dict(zip(urls, pool.map(valid, urls)))
added=0
for i,url in candidates.items():
    if not results[url]: continue
    line=lines[i]
    lines[i]=line.replace(' group-title=', ' tvg-logo="'+url+'" group-title=',1)
    added+=1
# Reuse independently verified logos already present for the exact same tvg-id.
# Do not infer identity from similar names or channel numbers.
id_logos = defaultdict(set)
for line in lines:
    if not line.startswith("#EXTINF"): continue
    lid = re.search(r'tvg-id="([^"]+)"', line)
    logo = re.search(r'tvg-logo="([^"]+)"', line)
    if lid and lid.group(1) and logo and logo.group(1).startswith("https://"):
        id_logos[lid.group(1)].add(logo.group(1))
reuse_candidates = {}
for i, line in enumerate(lines):
    if not line.startswith("#EXTINF") or 'group-title="🗂️ YEDEKLER' not in line or re.search(r'tvg-logo="[^"]+"',line): continue
    lid = re.search(r'tvg-id="([^"]+)"',line)
    if not lid or not lid.group(1): continue
    options = id_logos.get(lid.group(1),set())
    if len(options)==1: reuse_candidates[i] = next(iter(options))
extra_urls = sorted(set(reuse_candidates.values()))
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
    extra_results = dict(zip(extra_urls, pool.map(valid, extra_urls)))
reused=0
for i,url in reuse_candidates.items():
    if extra_results[url]:
        lines[i]=lines[i].replace(' group-title=', ' tvg-logo="'+url+'" group-title=',1)
        reused+=1
added+=reused
output="".join(lines)
assert len(output.splitlines())==len(original.splitlines())
assert all(a==b for a,b in zip(original.splitlines(),output.splitlines()) if 'group-title="🗂️ YEDEKLER' not in a)
if added: PLAYLIST.write_text(output,encoding="utf-8")
REPORT.write_text(json.dumps({"missing_before":missing,"added":added,"reused_exact_tvg_id":reused,"missing_after":missing-added,"ambiguous_or_unmatched":ambiguous,"invalid_logo_urls":sum(not results[u] for u in urls)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(REPORT.read_text())

#!/usr/bin/env python3
"""Non-destructive logo archive. Never edits the live playlist or its tvg-logo URLs."""
import hashlib
import json
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "v2" / "logos"
DEST.mkdir(parents=True, exist_ok=True)
MANIFEST = DEST / "manifest.json"
text = (ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8").read_text(encoding="utf-8-sig")
urls = sorted(set(re.findall(r'tvg-logo="(https?://[^"]+)"', text)))
previous = {}
if MANIFEST.exists():
    previous = {item["url"]: item for item in json.loads(MANIFEST.read_text(encoding="utf-8"))}
HEADERS = {"User-Agent": "MADSC55-TV-V2-LogoArchive/2.0 (github.com/Madsc55/MADSC55-TV-V2)", "Accept": "image/png,image/jpeg,image/webp,image/svg+xml,image/gif,*/*;q=0.4"}
EXT = {"image/png":".png","image/jpeg":".jpg","image/webp":".webp","image/gif":".gif","image/svg+xml":".svg"}

def variants(url):
    yield url
    if "wikimedia.org" in urllib.parse.urlsplit(url).netloc or "wikipedia.org" in urllib.parse.urlsplit(url).netloc:
        parts = urllib.parse.urlsplit(url)
        path = urllib.parse.unquote(parts.path)
        if "/thumb/" in path:
            tail = path.split("/thumb/",1)[1].split("/")
            if len(tail) >= 4:
                original = "/".join(tail[:-1])
                yield urllib.parse.urlunsplit((parts.scheme,parts.netloc,"/wikipedia/"+original,parts.query,""))
                yield "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + urllib.parse.quote(tail[-2])
        filename = path.rstrip("/").split("/")[-1]
        if filename:
            yield "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + urllib.parse.quote(filename)
            yield "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(filename)
    if url.startswith("http://"):
        yield "https://" + url[7:]

def download(url):
    safe = urllib.parse.quote(url, safe=":/?&=%#@+;,")
    req = urllib.request.Request(safe, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=35) as response:
        mime = response.headers.get("Content-Type","").split(";")[0].lower()
        data = response.read(2_000_001)
    if not data or len(data)>2_000_000:
        raise ValueError("invalid image size")
    if mime not in EXT:
        if data.startswith(b"\x89PNG\r\n\x1a\n"): mime="image/png"
        elif data.startswith(b"\xff\xd8\xff"): mime="image/jpeg"
        elif data.startswith(b"GIF8"): mime="image/gif"
        elif data.startswith(b"RIFF") and data[8:12]==b"WEBP": mime="image/webp"
        elif data.lstrip().startswith((b"<svg",b"<?xml")) and b"<svg" in data[:1024]: mime="image/svg+xml"
        else: raise ValueError("not a supported image")
    return data, EXT[mime]

manifest=[]
for url in urls:
    old = previous.get(url, {})
    old_file = ROOT / old.get("file","") if old.get("file") else None
    if old.get("status")=="saved" and old_file and old_file.is_file() and hashlib.sha256(old_file.read_bytes()).hexdigest()==old.get("sha256"):
        manifest.append(old)
        continue
    last_error="unavailable"
    saved=False
    for candidate in dict.fromkeys(variants(url)):
        for attempt in range(2):
            try:
                raw, ext = download(candidate)
                name = hashlib.sha256(url.encode()).hexdigest()[:20]+ext
                file = DEST / name
                file.write_bytes(raw)
                manifest.append({"url":url,"file":str(file.relative_to(ROOT)),"sha256":hashlib.sha256(raw).hexdigest(),"status":"saved","downloaded_from":candidate})
                saved=True
                break
            except Exception as exc:
                last_error=type(exc).__name__ + ": " + str(exc)[:110]
                if attempt==0: time.sleep(1)
        if saved: break
    if not saved:
        manifest.append({"url":url,"status":"failed","reason":last_error})
MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
count=sum(item["status"]=="saved" for item in manifest)
print(f"Logo sources: {len(urls)} | saved: {count} | failed: {len(urls)-count}")
if count == 0: raise SystemExit("No logos saved")

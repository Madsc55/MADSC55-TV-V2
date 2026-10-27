#!/usr/bin/env python3
"""Backup externally hosted logos without modifying live tvg-logo URLs."""
import hashlib
import json
import pathlib
import re
import urllib.request
import urllib.parse
import time
ROOT = pathlib.Path(__file__).resolve().parents[1]
playlist = (ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8").read_text(encoding="utf-8-sig")
urls = sorted(set(re.findall(r'tvg-logo="(https?://[^"]+)"', playlist)))
dest = ROOT / "v2" / "logos"
dest.mkdir(parents=True, exist_ok=True)
manifest = []
for url in urls:
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    try:
        safe_url = urllib.parse.quote(url, safe=":/?&=%#@+;,")
        req = urllib.request.Request(safe_url, headers={"User-Agent":"Mozilla/5.0 (compatible; MADSC55-TV-V2/1.0)", "Accept":"image/avif,image/webp,image/png,image/jpeg,image/svg+xml,image/*;q=0.8,*/*;q=0.5"})
        with urllib.request.urlopen(req, timeout=30) as response:
            mime = response.headers.get("Content-Type", "").split(";")[0].lower()
            if mime not in {"image/png","image/jpeg","image/webp","image/gif","image/svg+xml"}:
                raise ValueError("unexpected MIME")
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000 or not raw:
            raise ValueError("invalid image size")
        ext = {"image/png":".png","image/jpeg":".jpg","image/webp":".webp","image/gif":".gif","image/svg+xml":".svg"}[mime]
        path = dest / (key + ext)
        path.write_bytes(raw)
        manifest.append({"url":url,"file":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(raw).hexdigest(),"status":"saved"})
    except Exception as exc:
        manifest.append({"url":url,"status":"failed","reason":type(exc).__name__})
(dest / "manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
saved = sum(x["status"]=="saved" for x in manifest)
print(f"Logo sources: {len(urls)} | saved: {saved} | failed: {len(urls)-saved}")
if saved == 0:
    raise SystemExit("No logos downloaded")

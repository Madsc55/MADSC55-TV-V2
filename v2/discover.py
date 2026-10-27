#!/usr/bin/env python3
"""V2 independent, read-only IPTV candidate discovery. Stdlib only."""
import argparse
import hashlib
import json
import pathlib
import re
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIVE = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
SOURCES = pathlib.Path(__file__).parent / "config" / "sources.json"
OUTPUT = ROOT / "v2" / "reports" / "candidates.json"
MAX_BYTES = 25_000_000

def fetch(url):
    if not url.startswith("https://"):
        raise ValueError("HTTPS source required")
    req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-Discovery/1.0"})
    with urllib.request.urlopen(req, timeout=25) as res:
        data = res.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Source too large")
    return data.decode("utf-8-sig", errors="replace")

def entries(data):
    lines = data.splitlines()
    for i, line in enumerate(lines):
        if not line.startswith("#EXTINF:"):
            continue
        name = line.rsplit(",", 1)[-1].strip()
        match = re.search(r'tvg-id="([^"]*)"', line)
        tvg_id = match.group(1).strip() if match else ""
        logo = re.search(r'tvg-logo="([^"]*)"', line)
        group = re.search(r'group-title="([^"]*)"', line)
        url = next((s.strip() for s in lines[i+1:] if s.strip() and not s.startswith("#")), "")
        if not url or not url.startswith(("https://", "http://")):
            continue
        yield {"name": name, "tvg_id": tvg_id, "logo": logo.group(1) if logo else "", "group": group.group(1) if group else "", "url": url}

def key(entry):
    return (entry["tvg_id"].casefold(), entry["name"].casefold())

def discover(source_texts, live_text):
    existing_urls = {e["url"] for e in entries(live_text)}
    existing_keys = {key(e) for e in entries(live_text)}
    candidates, seen = [], set()
    for source_id, content in source_texts:
        for e in entries(content):
            if e["url"] in existing_urls or key(e) in existing_keys or e["url"] in seen:
                continue
            seen.add(e["url"])
            # Do not persist stream URLs/tokens in public reports.
            candidates.append({"name": e["name"], "tvg_id": e["tvg_id"], "group": e["group"], "source": source_id, "url_sha256": hashlib.sha256(e["url"].encode()).hexdigest(), "logo": e["logo"]})
    return candidates

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true", help="Do not access external sources")
    args = p.parse_args()
    live = LIVE.read_text(encoding="utf-8-sig")
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    loaded, errors = [], []
    for source in sources:
        if args.offline:
            continue
        try:
            loaded.append((source["id"], fetch(source["url"])))
        except Exception as exc:
            errors.append({"source": source["id"], "error": type(exc).__name__})
    result = {"schema": 1, "mode": "read-only", "source_count": len(loaded), "errors": errors, "candidates": discover(loaded, live)}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Sources: {len(loaded)} | Candidates: {len(result['candidates'])} | Errors: {len(errors)}")
    if not args.offline and not loaded:
        raise SystemExit("No sources accessible")

if __name__ == "__main__":
    main()

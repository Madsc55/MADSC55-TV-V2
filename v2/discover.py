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
DYNAMIC = ROOT / "v2" / "reports" / "github-source-discovery.json"
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
    """Parse adjacent EXTINF/stream pairs in linear time."""
    pending = None
    for raw in data.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            name = line.rsplit(",", 1)[-1].strip()
            def field(label):
                m = re.search(r'\b' + re.escape(label) + r'="([^"]*)"', line)
                return m.group(1).strip() if m else ""
            pending = {"name": name, "tvg_id": field("tvg-id"), "logo": field("tvg-logo"), "group": field("group-title")}
        elif line and not line.startswith("#"):
            if pending is not None and line.startswith(("https://", "http://")):
                yield {**pending, "url": line}
            pending = None

def key(entry):
    return (entry["tvg_id"].casefold(), entry["name"].casefold())

def discover(source_texts, live_text):
    existing_urls = {e["url"] for e in entries(live_text)}
    existing_keys = {key(e) for e in entries(live_text) if e["tvg_id"]}
    candidates, seen = [], set()
    for source_id, content in source_texts:
        for e in entries(content):
            if e["url"] in existing_urls or e["url"] in seen:
                continue
            seen.add(e["url"])
            # Do not persist stream URLs/tokens in public reports.
            candidates.append({"name": e["name"], "tvg_id": e["tvg_id"], "group": e["group"], "source": source_id, "existing_channel_alternative": bool(e["tvg_id"] and key(e) in existing_keys), "url_sha256": hashlib.sha256(e["url"].encode()).hexdigest(), "logo": e["logo"]})
    return candidates

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true", help="Do not access external sources")
    p.add_argument("--limit", type=int, default=10000, help="Maximum candidate count")
    args = p.parse_args()
    live = LIVE.read_text(encoding="utf-8-sig")
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    if DYNAMIC.exists():
        try:
            dynamic = json.loads(DYNAMIC.read_text(encoding="utf-8"))
            for index, item in enumerate(dynamic.get("sources", [])[:80]):
                url = item.get("url", "")
                if url.startswith("https://") and not any(s["url"] == url for s in sources):
                    sources.append({"id": "github-auto-" + str(index), "url": url, "scope": "candidate"})
        except (OSError, ValueError, TypeError):
            pass
    loaded, errors, source_audit = [], [], []
    for source in sources:
        if args.offline:
            continue
        try:
            last_error = None
            for attempt in range(4):
                try:
                    content = fetch(source["url"])
                    parsed = list(entries(content))
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
            if last_error is not None:
                raise last_error
            loaded.append((source["id"], content))
            source_audit.append({"source": source["id"], "entries": len(parsed),
                                 "distinct_stream_urls": len({e["url"] for e in parsed}),
                                 "status": "PARSED_NOT_PLAYBACK_VERIFIED"})
        except Exception as exc:
            errors.append({"source": source["id"], "error": type(exc).__name__})
            source_audit.append({"source": source["id"], "status": "FETCH_FAILED",
                                 "error": type(exc).__name__})
    result = {"schema": 1, "mode": "read-only", "configured_and_discovered_sources": len(sources), "source_count": len(loaded), "errors": errors, "source_audit": source_audit, "candidates": discover(loaded, live)}
    result["candidates"] = result["candidates"][:max(0, args.limit)]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print(f"Sources: {len(loaded)} | Candidates: {len(result['candidates'])} | Errors: {len(errors)}")
    if not args.offline and not loaded:
        raise SystemExit("No sources accessible")

if __name__ == "__main__":
    main()

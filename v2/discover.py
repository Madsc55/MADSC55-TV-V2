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

def turkish_candidate(entry, scope):
    """Conservative Turkish candidate gate; not spoken-language proof."""
    if scope in ("TR", "AZ"):
        # Geographic candidate inclusion only; never proof of Turkish speech.
        return True
    fields = " ".join((entry.get("group", ""), entry.get("tvg_id", ""), entry.get("name", "")))
    if re.search(r"(?i)(?:^|[^a-z])(?:trt|türk|turk|turkish|türkçe|türkiye|turkiye|turkey|türkiye tv|azerbaijan|azerbaycan|azərbaycan|azerbaijani|azeri|azərbaycan dili)(?:$|[^a-z])", fields):
        return True
    if re.search(r"(?i)(?:^|[. _-])(?:tr)(?:[. _-]|$)", entry.get("tvg_id", "")):
        return True
    return False

def key(entry):
    return (entry["tvg_id"].casefold(), entry["name"].casefold())

def discover(source_texts, live_text, scopes):
    existing_urls = {e["url"] for e in entries(live_text)}
    existing_keys = {key(e) for e in entries(live_text) if e["tvg_id"]}
    candidates, seen = [], set()
    provenance = {}
    for source_id, content in source_texts:
        for e in entries(content):
            if not turkish_candidate(e, scopes.get(source_id, 'candidate')):
                continue
            if e["url"] in existing_urls:
                continue
            digest = hashlib.sha256(e["url"].encode()).hexdigest()
            if e["url"] in seen:
                if source_id not in provenance[digest]:
                    provenance[digest].append(source_id)
                continue
            seen.add(e["url"])
            provenance[digest] = [source_id]
            # Do not persist stream URLs/tokens in public reports.
            candidates.append({"name": e["name"], "tvg_id": e["tvg_id"], "group": e["group"], "source": source_id, "source_ids": provenance[digest], "existing_channel_alternative": bool(e["tvg_id"] and key(e) in existing_keys), "url_sha256": hashlib.sha256(e["url"].encode()).hexdigest(), "logo": e["logo"]})
    return candidates

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true", help="Do not access external sources")
    p.add_argument("--snapshot-output", action="store_true", help="Write private ephemeral playback snapshot")
    p.add_argument("--limit", type=int, default=0, help="Maximum candidate count; 0 means no limit")
    p.add_argument("--previous-report", type=pathlib.Path, help="Previous discovery JSON for source-loss audit")
    args = p.parse_args()
    if args.limit < 0:
        p.error("--limit must be zero or positive")
    if args.offline and args.snapshot_output:
        p.error("--snapshot-output cannot be used with --offline")
    if args.offline and args.previous_report:
        p.error("--previous-report requires an actual network discovery run")
    live = LIVE.read_text(encoding="utf-8-sig")
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    if DYNAMIC.exists():
        try:
            dynamic = json.loads(DYNAMIC.read_text(encoding="utf-8"))
            for item in dynamic.get("sources", [])[:240]:
                url = item.get("url", "")
                if url.startswith("https://") and not any(s["url"] == url for s in sources):
                    sources.append({"id": "github-auto-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:20], "url": url, "scope": "candidate"})
        except (OSError, ValueError, TypeError) as exc:
            raise SystemExit('Dynamic discovery inventory unreadable: ' + type(exc).__name__) from exc
    loaded, errors, source_audit = [], [], []
    scopes = {source['id']: source.get('scope', 'candidate') for source in sources}
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
    if args.snapshot_output and (errors or not loaded):
        raise SystemExit("Snapshot incomplete: no successful full source set; refusing private snapshot output")
    if args.snapshot_output:
        existing = {e["url"] for e in entries(live)}
        seen_urls = set()
        snapshot = []
        snapshot_by_url = {}
        for source_id, content in loaded:
            for item in entries(content):
                if not turkish_candidate(item, scopes.get(source_id, 'candidate')):
                    continue
                if item["url"] in existing:
                    continue
                if item["url"] in seen_urls:
                    prior = snapshot_by_url[item["url"]]
                    if source_id not in prior["source_ids"]:
                        prior["source_ids"].append(source_id)
                    continue
                seen_urls.add(item["url"])
                record = {"source": source_id, "source_ids": [source_id], **item}
                snapshot.append(record)
                snapshot_by_url[item["url"]] = record
        private = ROOT / "v2/reports/private-playback-snapshot.json"
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_text(json.dumps({"schema": 1, "sources": source_audit, "candidates": snapshot}, ensure_ascii=False), encoding="utf-8")
        private.chmod(0o600)
        if errors:
            raise SystemExit("Snapshot incomplete: " + str(len(errors)) + " source(s) failed; no playback permitted")
    result = {"schema": 1, "mode": "read-only", "configured_and_discovered_sources": len(sources), "source_count": len(loaded), "errors": errors, "source_audit": source_audit, "candidates": discover(loaded, live, scopes)}
    result["total_unique_candidates"] = len(result["candidates"])
    if args.previous_report:
        from source_loss_audit import compare
        previous = json.loads(args.previous_report.read_text(encoding="utf-8"))
        result["source_loss_audit"] = compare(previous, result)
        if result["source_loss_audit"]["findings"]:
            print("WARNING: source loss requires review; see source_loss_audit in report")
    result["candidate_limit"] = args.limit
    result["candidates_truncated"] = args.limit > 0 and len(result["candidates"]) > args.limit
    if args.limit > 0:
        result["candidates"] = result["candidates"][:args.limit]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print(f"Sources: {len(loaded)} | Candidates: {len(result['candidates'])} | Errors: {len(errors)}")
    if not args.offline and not loaded:
        raise SystemExit("No sources accessible")

if __name__ == "__main__":
    main()

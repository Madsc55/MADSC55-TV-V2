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
FORGE = ROOT / "v2" / "reports" / "forge-source-discovery.json"
FORGE_APPROVALS = ROOT / "v2" / "config" / "approved-forge-source-sha256.json"
MAX_BYTES = 25_000_000

def fetch(url, allow_html=False):
    from webpage_source_discovery import candidate_url, public_hostname
    from forge_source_review import valid_forge_source
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    valid_page = (allow_html and parsed.scheme == "https" and parsed.hostname
                  and public_hostname(parsed.hostname) and not parsed.username
                  and not parsed.password and parsed.port in (None, 443))
    if not (candidate_url(url) or valid_forge_source(url) or valid_page):
        raise ValueError("Public HTTPS M3U source or approved HTML index required")
    req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-Discovery/1.0"})
    # Redirects must never escape the validated source origin into private hosts.
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            from urllib.parse import urlsplit
            from webpage_source_discovery import public_hostname
            target = urlsplit(newurl)
            if (target.scheme != "https" or not target.hostname
                    or not public_hostname(target.hostname)
                    or target.username or target.password
                    or target.port not in (None, 443)):
                raise ValueError("Unsafe source redirect")
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SafeRedirect())
    with opener.open(req, timeout=25) as res:
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
            # Channel name begins after the first comma outside quoted attributes.
            quoted = False
            separator = -1
            for position, character in enumerate(line):
                if character == '"':
                    quoted = not quoted
                elif character == "," and not quoted:
                    separator = position
                    break
            name = line[separator + 1:].strip() if separator >= 0 else ""
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

def recognized_channel_ids(source_texts, scopes):
    known = set()
    for source_id, content in source_texts:
        if scopes.get(source_id) in ("TR", "AZ"):
            for item in entries(content):
                if item["tvg_id"].strip():
                    known.add(item["tvg_id"].strip().casefold())
    return known

def discover(source_texts, live_text, scopes):
    existing_urls = {e["url"] for e in entries(live_text)}
    existing_keys = {key(e) for e in entries(live_text) if e["tvg_id"]}
    # TR/AZ and Turkish-language playlists supply reliable cross-source identities.
    # Match TVG IDs only: generic names like "News" must not pull in world channels.
    # Materialize once so generators remain safe and provenance stays deterministic.
    source_texts = list(source_texts)
    known_ids = recognized_channel_ids(source_texts, scopes)
    candidates, seen = [], set()
    provenance = {}
    for source_id, content in source_texts:
        for e in entries(content):
            recognized = bool(e["tvg_id"].strip() and e["tvg_id"].strip().casefold() in known_ids)
            if not (turkish_candidate(e, scopes.get(source_id, 'candidate')) or recognized):
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
    p.add_argument("--snapshot-output", action="store_true", help="Legacy plaintext snapshot (disabled)")
    p.add_argument("--encrypted-archive", type=pathlib.Path, help="Append candidates to AES-GCM private archive")
    p.add_argument("--limit", type=int, default=0, help="Maximum candidate count; 0 means no limit")
    p.add_argument("--previous-report", type=pathlib.Path, help="Previous discovery JSON for source-loss audit")
    args = p.parse_args()
    if args.limit < 0:
        p.error("--limit must be zero or positive")
    if args.snapshot_output:
        p.error("Unencrypted token-bearing snapshots are disabled until encrypted archival and restore are verified")
    if args.offline and args.encrypted_archive:
        p.error("--encrypted-archive requires a real source scan")
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
    if FORGE.exists():
        from forge_source_review import approved_sources
        forge_report = json.loads(FORGE.read_text(encoding="utf-8"))
        approvals = set()
        if FORGE_APPROVALS.exists():
            approval_doc = json.loads(FORGE_APPROVALS.read_text(encoding="utf-8"))
            approvals = set(approval_doc.get("approved_sha256", []))
        for source in approved_sources(forge_report, approvals):
            if not any(x["url"] == source["url"] for x in sources):
                sources.append(source)
    if args.encrypted_archive:
        from archive_acceptance_gate import check
        check()
        from encrypted_archive import _cipher
        _cipher()
    loaded, errors, source_audit = [], [], []
    # A page is a discovery index, not an M3U stream. Expand only explicit
    # public HTTPS playlist links; never treat HTML as playable media.
    from webpage_source_discovery import discover_playlist_links
    scopes = {source['id']: source.get('scope', 'candidate') for source in sources}
    for source in sources:
        if args.offline:
            continue
        try:
            last_error = None
            for attempt in range(4):
                try:
                    content = fetch(source["url"], allow_html=source.get("kind") == "html")
                    parsed = list(entries(content))
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc
            if last_error is not None:
                raise last_error
            if source.get("kind", "m3u") == "html":
                links = discover_playlist_links(source["url"], content)[:30]
                source_audit.append({"source": source["id"], "entries": len(links),
                                     "distinct_stream_urls": 0,
                                     "status": "INDEX_LINKS_ONLY_NOT_PLAYBACK_VERIFIED"})
                for i, link in enumerate(links):
                    child_id = source["id"] + "-link-" + str(i)
                    try:
                        child_text = fetch(link)
                        child_entries = list(entries(child_text))
                        loaded.append((child_id, child_text))
                        scopes[child_id] = source.get("scope", "candidate")
                        source_audit.append({"source": child_id, "entries": len(child_entries),
                                             "distinct_stream_urls": len({e["url"] for e in child_entries}),
                                             "status": "PARSED_NOT_PLAYBACK_VERIFIED"})
                    except Exception as exc:
                        errors.append({"source": child_id, "error": type(exc).__name__})
                        source_audit.append({"source": child_id, "status": "FETCH_FAILED",
                                             "error": type(exc).__name__})
                continue
            loaded.append((source["id"], content))
            source_audit.append({"source": source["id"], "entries": len(parsed),
                                 "distinct_stream_urls": len({e["url"] for e in parsed}),
                                 "status": "PARSED_NOT_PLAYBACK_VERIFIED"})
        except Exception as exc:
            errors.append({"source": source["id"], "error": type(exc).__name__})
            source_audit.append({"source": source["id"], "status": "FETCH_FAILED",
                                 "error": type(exc).__name__})
    if args.encrypted_archive:
        if args.encrypted_archive.is_symlink():
            raise SystemExit("Encrypted archive path must not be a symlink")
        if errors or not loaded:
            raise SystemExit("Encrypted archive refused: source set incomplete")
        from encrypted_archive import append, restore
        from archive_acceptance_gate import check
        check()
        existing = {item["url"] for item in entries(live)}
        archived = set()
        known_ids = recognized_channel_ids(loaded, scopes)
        for source_id, content in loaded:
            for item in entries(content):
                if (item["url"] not in existing and item["url"] not in archived
                        and (turkish_candidate(item, scopes.get(source_id, "candidate"))
                             or bool(item["tvg_id"].strip() and item["tvg_id"].strip().casefold() in known_ids))):
                    append(args.encrypted_archive, {"source": source_id, **item})
                    archived.add(item["url"])
        restored = restore(args.encrypted_archive)
        if archived and not archived.issubset({x["url"] for x in restored}):
            raise SystemExit("Encrypted archive restore verification failed")
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

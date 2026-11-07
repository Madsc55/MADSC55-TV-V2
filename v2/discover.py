#!/usr/bin/env python3
"""V2 independent, read-only IPTV candidate discovery. Stdlib only."""
import argparse
import hashlib
import json
import pathlib
import re
import urllib.request
import urllib.error
import socket
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIVE = ROOT / "MADSC55_TV_IBO_CALISANLAR_TEST.m3u8"
SOURCES = pathlib.Path(__file__).parent / "config" / "sources.json"
OUTPUT = ROOT / "v2" / "reports" / "candidates.json"
DYNAMIC = ROOT / "v2" / "reports" / "github-source-discovery.json"
FORGE = ROOT / "v2" / "reports" / "forge-source-discovery.json"
FORGE_APPROVALS = ROOT / "v2" / "config" / "approved-forge-source-sha256.json"
GITHUB_APPROVALS = ROOT / "v2" / "config" / "approved-github-source-sha256.json"
MAX_BYTES = 25_000_000

def load_original_run60_sources(path):
    """Load only original #60 GitHub source IDs proven by the snapshot CI gate.

    Historic sources stay discovery candidates; they never auto-promote streams
    into the protected IBO playlist.
    """
    from urllib.parse import urlsplit
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if (doc.get("schema") != 1 or doc.get("source_run_id") != 40743765437
            or doc.get("artifact_id") != 12840886350
            or not isinstance(doc.get("sources"), list)
            or len(doc["sources"]) != 17
            or any(not isinstance(x, dict) or not isinstance(x.get("old_only"), int)
                   or isinstance(x.get("old_only"), bool) or x["old_only"] < 0
                   for x in doc["sources"])
            or sum(x["old_only"] for x in doc["sources"]) != 8449):
        raise ValueError("Unverified original #60 source ledger")
    restored, seen, seen_urls = [], set(), set()
    for row in doc["sources"]:
        ident, url = row.get("id"), row.get("url")
        if not isinstance(ident, str) or not re.fullmatch(r"github-auto-(?:0|[1-9][0-9]*)", ident):
            raise ValueError("Invalid original source identity")
        if ident in seen or not isinstance(url, str) or url in seen_urls:
            raise ValueError("Duplicate or missing original source identity/URL")
        try:
            p = urlsplit(url)
            valid_url = (p.scheme == "https" and p.hostname == "raw.githubusercontent.com"
                         and not p.username and not p.password and not p.fragment
                         and p.port in (None, 443)
                         and p.path.lower().endswith((".m3u", ".m3u8")))
        except ValueError:
            valid_url = False
        if not valid_url:
            raise ValueError("Original source URL is not a public GitHub M3U")
        seen.add(ident)
        seen_urls.add(url)
        restored.append({"id": ident, "url": url, "kind": "m3u",
                         "scope": "candidate", "historical_source_only": True})
    return restored


def normalize_original_source_text(source, content):
    """Accept headerless EXTINF feeds only for verified #60 source labels."""
    if source.get("historical_source_only") and content.lstrip("\ufeff\r\n\t ").startswith("#EXTINF:"):
        return "#EXTM3U\n" + content.lstrip("\ufeff\r\n\t ")
    return content


def approved_github_source(url, approved_hashes):
    from webpage_source_discovery import candidate_url
    return (isinstance(url, str) and candidate_url(url)
            and hashlib.sha256(url.encode("utf-8")).hexdigest() in approved_hashes)

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

def has_http_url_hostname(url):
    """Reject structurally broken HTTP URLs without filtering private device URLs."""
    from urllib.parse import urlsplit
    try:
        parsed = urlsplit(url)
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)
    except ValueError:
        return False


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
            if (pending is not None and line.startswith(("https://", "http://"))
                    and has_http_url_hostname(line)):
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
    if re.search(r"(?i)(?:^|[. _-])(?:tr|az)(?:[. _-]|$)", entry.get("tvg_id", "")):
        return True
    return False

def public_metadata(value):
    """Mask URL and credential-like metadata before public report emission."""
    if not isinstance(value, str):
        return ""
    value = re.sub(r"https?://\S+", "[URL_REDACTED]", value, flags=re.IGNORECASE)
    value = re.sub(r"(?i)(?:token|apikey|api_key|password|passwd|secret|auth|signature|sig|key)\s*[:=]\s*[^\s,;]+",
                   "[CREDENTIAL_REDACTED]", value)
    return value[:512]

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
            candidates.append({"name": public_metadata(e["name"]), "tvg_id": public_metadata(e["tvg_id"]), "group": public_metadata(e["group"]), "source": source_id, "source_ids": provenance[digest], "existing_channel_alternative": bool(e["tvg_id"] and key(e) in existing_keys), "url_sha256": hashlib.sha256(e["url"].encode()).hexdigest(), "logo": public_metadata(e["logo"])})
    return candidates

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--offline", action="store_true", help="Do not access external sources")
    p.add_argument("--snapshot-output", action="store_true", help="Legacy plaintext snapshot (disabled)")
    p.add_argument("--encrypted-archive", type=pathlib.Path, help="Append candidates to AES-GCM private archive")
    p.add_argument("--limit", type=int, default=0, help="Maximum candidate count; 0 means no limit")
    p.add_argument("--previous-report", type=pathlib.Path, help="Previous discovery JSON for source-loss audit")
    p.add_argument("--include-original-run60-github-sources", action="store_true",
                   help="Include the 17 exact originally discovered GitHub source locations")
    p.add_argument("--include-reviewed-public-source-references", action="store_true",
                   help="Read-only bounded parsing of public GitHub/Gist and GitLab/Codeberg M3U source references")
    p.add_argument("--include-approved-live-page-indexes", action="store_true",
                   help="Check approved broadcaster HTML pages for real M3U channel-list links only")
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
    configured = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    retired_sources = [item for item in configured if item.get("enabled", True) is False]
    sources = [item for item in configured if item.get("enabled", True) is not False]
    if args.include_original_run60_github_sources:
        original_sources = load_original_run60_sources(
            ROOT / "v2/history/run60-dynamic-source-ledger.json")
        known_ids = {item["id"] for item in sources}
        known_urls = {item["url"] for item in sources}
        for item in original_sources:
            if item["id"] in known_ids or item["url"] in known_urls:
                raise SystemExit("Original source ledger overlaps current M3U source identity")
            sources.append(item)
            known_ids.add(item["id"])
            known_urls.add(item["url"])
    github_approvals = set()
    if GITHUB_APPROVALS.exists():
        approval_doc = json.loads(GITHUB_APPROVALS.read_text(encoding="utf-8"))
        if approval_doc.get("schema") != 1 or not isinstance(approval_doc.get("approved_sha256"), list):
            raise SystemExit("Invalid GitHub source approval inventory")
        github_approvals = set(approval_doc["approved_sha256"])
    if DYNAMIC.exists():
        try:
            dynamic = json.loads(DYNAMIC.read_text(encoding="utf-8"))
            for item in dynamic.get("sources", [])[:240]:
                url = item.get("url", "")
                if (approved_github_source(url, github_approvals)
                        and not any(s["url"] == url for s in sources)):
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
    loaded, errors, source_audit = [], [], [
        {"source": item["id"], "status": "DISABLED_UPSTREAM_REMOVED",
         "entries": 0, "distinct_stream_urls": 0,
         "reason": item.get("retirement_reason", "RETAINED_HISTORICAL_SOURCE")}
        for item in retired_sources
    ]
    # Bounded public document references enter the same source-loss and dedup pipeline.
    from document_platform_discovery import accepted_sources
    for doc_source in accepted_sources():
        if not any(s["url"] == doc_source["url"] for s in sources):
            sources.append(doc_source)
    # Dynamic references that are not in permanent SHA approval files may be
    # inspected only during explicitly requested read-only source discovery.
    # No source reference or M3U channel metadata is treated as media/AV proof.
    public_source_handoff = {"status": "NOT_REQUESTED", "playback_verified": False}
    if args.include_reviewed_public_source_references:
        from public_source_handoff import staged_references
        inspected, public_source_handoff = staged_references(
            DYNAMIC, FORGE, {s["url"] for s in sources})
        sources.extend(inspected)
    live_page_handoff = {"status": "NOT_REQUESTED", "playback_verified": False}
    if args.include_approved_live_page_indexes:
        from public_source_handoff import approved_live_index_sources
        live_pages, live_page_handoff = approved_live_index_sources(
            ROOT / "v2/config/live-pages.json", {s["url"] for s in sources})
        sources.extend(live_pages)
    # A page is a discovery index, not an M3U stream. Expand only explicit
    # public HTTPS playlist links; never treat HTML as playable media.
    from webpage_source_discovery import discover_playlist_links
    # The approved public index inventory is part of the same source-fetch
    # pipeline, but links are only parsed after validating the HTML origin.
    index_inventory = ROOT / "v2/config/playlist-index-pages.json"
    if index_inventory.exists():
        index_document = json.loads(index_inventory.read_text(encoding="utf-8"))
        if index_document.get("schema") != 1 or not isinstance(index_document.get("pages"), list):
            raise SystemExit("Invalid approved public index inventory")
        for page in index_document["pages"]:
            if not isinstance(page, dict) or not isinstance(page.get("id"), str) or not isinstance(page.get("url"), str):
                raise SystemExit("Invalid public index entry")
            if not any(s["url"] == page["url"] for s in sources):
                sources.append({"id": "index-" + page["id"], "kind": "html",
                                "url": page["url"], "scope": "candidate"})
    scopes = {source['id']: source.get('scope', 'candidate') for source in sources}
    fetched_playlist_urls = {source["url"] for source in sources if source.get("kind", "m3u") != "html"}
    skipped_duplicate_index_links = 0
    index_link_errors = []
    optional_index_errors = []
    from source_failover import SourceCache, recover_source, FetchFailure
    failover_cache = SourceCache(ROOT / "v2" / "cache" / "discovery-source-failover")
    for source in sources:
        if args.offline:
            continue
        attempts = 0
        try:
            # Public dynamic references must resolve exclusively to globally
            # routable hosts. This gate is separate from playlist M3U parsing.
            if source.get("origin") == "reviewed-public-source-reference":
                from historical_targeted_playback import public_dns
                if not public_dns(source["url"]):
                    raise ValueError("Unsafe or unresolved public dynamic source host")
            last_error = None
            for attempt in range(4):
                attempts = attempt + 1
                try:
                    if source.get("kind") == "html":
                        content = fetch(source["url"], allow_html=True)
                    else:
                        def source_fetch(url):
                            try:
                                return normalize_original_source_text(source, fetch(url))
                            except urllib.error.HTTPError as exc:
                                raise FetchFailure("HTTP_" + str(exc.code), exc.code in (408, 429, 500, 502, 503, 504)) from exc
                            except (TimeoutError, socket.timeout, urllib.error.URLError, OSError) as exc:
                                raise FetchFailure(type(exc).__name__, True) from exc
                        content, recovery = recover_source(source, failover_cache, source_fetch)
                        if content is None or not recovery["fresh"]:
                            raise ValueError("No fresh source or fallback available")
                    parsed = list(entries(content))
                    last_error = None
                    break
                except (TimeoutError, socket.timeout, urllib.error.URLError, urllib.error.HTTPError,
                        OSError) as exc:
                    last_error = exc
                    # Retry transient network failures only. Do not retry HTTP 4xx
                    # (except 408/429) or validation failures.
                    if isinstance(exc, urllib.error.HTTPError) and exc.code not in (408, 429, 500, 502, 503, 504):
                        break
                    if attempt < 3:
                        time.sleep(min(2 ** attempt, 4))
                except (ValueError, UnicodeError) as exc:
                    last_error = exc
                    break
            if last_error is not None:
                raise last_error
            if source.get("kind", "m3u") != "html" and not content.lstrip().startswith("#EXTM3U"):
                raise ValueError("Playlist source returned non-M3U content")
            if source.get("kind", "m3u") == "html":
                links = discover_playlist_links(source["url"], content)[:30]
                source_audit.append({"source": source["id"], "entries": len(links),
                                     "distinct_stream_urls": 0,
                                     "status": "INDEX_LINKS_ONLY_NOT_PLAYBACK_VERIFIED"})
                for link in links:
                    if link in fetched_playlist_urls:
                        skipped_duplicate_index_links += 1
                        continue
                    fetched_playlist_urls.add(link)
                    # Stable across HTML link reordering; never expose the URL in reports.
                    child_id = source["id"] + "-link-" + hashlib.sha256(link.encode("utf-8")).hexdigest()[:16]
                    try:
                        child_text = fetch(link)
                        child_entries = list(entries(child_text))
                        if not child_text.lstrip().startswith("#EXTM3U"):
                            raise ValueError("Indexed source is not an M3U playlist")
                        loaded.append((child_id, child_text))
                        scopes[child_id] = source.get("scope", "candidate")
                        source_audit.append({"source": child_id, "entries": len(child_entries),
                                             "distinct_stream_urls": len({e["url"] for e in child_entries}),
                                             "status": "PARSED_NOT_PLAYBACK_VERIFIED"})
                    except Exception as exc:
                        index_link_errors.append({"source": child_id, "error": type(exc).__name__})
                        source_audit.append({"source": child_id, "status": "OPTIONAL_INDEX_LINK_FAILED",
                                             "error": type(exc).__name__})
                continue
            effective_source_id = source["id"]
            if recovery["status"] == "FALLBACK_OK":
                # Alternate streams are not proof that the old source remains.
                effective_source_id += "-alternative-" + recovery["used_url_sha256"][:16]
                scopes[effective_source_id] = source.get("scope", "candidate")
                errors.append({"source": source["id"], "error": "ORIGINAL_SOURCE_UNAVAILABLE",
                               "attempts": recovery["attempts"]})
                source_audit.append({"source": source["id"], "status": "FETCH_FAILED",
                                     "error": "ORIGINAL_SOURCE_UNAVAILABLE",
                                     "attempts": recovery["attempts"]})
            loaded.append((effective_source_id, content))
            source_audit.append({"source": effective_source_id, "entries": len(parsed),
                                 "distinct_stream_urls": len({e["url"] for e in parsed}),
                                 "status": "PARSED_NOT_PLAYBACK_VERIFIED"})
        except Exception as exc:
            optional = source.get("kind") == "html"
            record = {"source": source["id"], "error": type(exc).__name__, "attempts": attempts}
            (optional_index_errors if optional else errors).append(record)
            source_audit.append({"source": source["id"],
                                 "status": "OPTIONAL_INDEX_FAILED" if optional else "FETCH_FAILED",
                                 "error": type(exc).__name__, "attempts": attempts})
    if args.encrypted_archive:
        if args.encrypted_archive.is_symlink():
            raise SystemExit("Encrypted archive path must not be a symlink")
        if not loaded:
            raise SystemExit("Encrypted archive refused: no accessible sources")
        from encrypted_archive import append, restore
        from archive_acceptance_gate import check
        check()
        existing = {item["url"] for item in entries(live)}
        archived = {item["url"] for item in restore(args.encrypted_archive)} if args.encrypted_archive.exists() else set()
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
    result = {"schema": 1, "mode": "read-only", "configured_and_discovered_sources": len(sources), "configured_inventory_total": len(configured), "retired_configured_source_ids": [item["id"] for item in retired_sources], "source_count": len(loaded), "errors": errors, "source_audit": source_audit, "candidates": discover(loaded, live, scopes)}
    result["coverage_status"] = ("OFFLINE_NO_NETWORK" if args.offline else
                                 "NO_SOURCES_ACCESSIBLE" if not loaded else
                                 "COMPLETE_SOURCE_FETCH" if not errors else "PARTIAL_SOURCE_FETCH")
    result["failed_source_count"] = len(errors)
    result["index_link_errors"] = index_link_errors
    result["optional_index_errors"] = optional_index_errors
    result["failed_optional_index_links"] = len(index_link_errors)
    result["source_coverage_summary"] = {
        "configured_sources": len(sources),
        "parsed_playlists": sum(item["status"] == "PARSED_NOT_PLAYBACK_VERIFIED" for item in source_audit),
        "index_pages_checked": sum(item["status"] == "INDEX_LINKS_ONLY_NOT_PLAYBACK_VERIFIED" for item in source_audit),
        "index_playlist_links_found": sum(item["entries"] for item in source_audit if item["status"] == "INDEX_LINKS_ONLY_NOT_PLAYBACK_VERIFIED"),
        "failed_sources": len(errors),
        "failed_optional_index_links": len(index_link_errors),
        "skipped_duplicate_index_links": skipped_duplicate_index_links,
        "playback_verified": False,
    }
    result["archive_source_set_partial"] = bool(args.encrypted_archive and errors)
    result["playback_verified"] = False
    result["source_fetch_complete"] = bool(not args.offline and loaded and not errors)
    result["total_unique_candidates"] = len(result["candidates"])
    result["existing_channel_alternative_count"] = sum(
        bool(candidate.get("existing_channel_alternative")) for candidate in result["candidates"]
    )
    result["candidate_status"] = "UNVERIFIED"
    # Surface reference-only discovery coverage without claiming those URLs are streams.
    auxiliary_reports = {
        "github_gist": ROOT / "v2/reports/github-source-discovery.json",
        "gitlab_codeberg": ROOT / "v2/reports/forge-source-discovery.json",
        "official_live_pages": ROOT / "v2/reports/live-page-references.json",
        "public_playlist_indexes": ROOT / "v2/reports/webpage-playlist-references.json",
        "youtube": ROOT / "v2/reports/youtube-live-candidates.json",
        "document_platforms": ROOT / "v2/reports/document-platform-references.json",
        "official_turkish_sites": ROOT / "v2/reports/official-tv-sites.json",
        "official_site_matching": ROOT / "v2/reports/official-tv-gap.json",
        "source_availability": ROOT / "v2/reports/source-availability-audit.json",
    }
    auxiliary = {}
    for label, report_path in auxiliary_reports.items():
        if not report_path.is_file():
            auxiliary[label] = {"status": "REPORT_MISSING", "playback_verified": False}
            continue
        try:
            document = json.loads(report_path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("Invalid report")
            records = document.get("results", document.get("references", document.get("sources", [])))
            if not isinstance(records, list):
                raise ValueError("Invalid records")
            auxiliary[label] = {"status": "REFERENCE_ONLY_NOT_ARCHIVED",
                                "records": len(records),
                                "playback_verified": False,
                                "report_errors": len(document.get("errors", []))}
        except (OSError, ValueError, TypeError):
            auxiliary[label] = {"status": "REPORT_INVALID", "playback_verified": False}
    result["auxiliary_discovery_coverage"] = auxiliary
    # Real metadata-only connection to the same M3U candidate identities.
    # No YouTube URL or official website URL is ever a media candidate.
    from advisory_channel_identity_bridge import link_advisory_identities
    result["advisory_channel_identity_handoff"] = link_advisory_identities(
        result["candidates"],
        ROOT / "v2/reports/official-tv-sites.json",
        ROOT / "v2/reports/youtube-live-candidates.json")
    source_lookup = {source["id"]: source for source in sources}
    dynamic_checked = [row for row in source_audit if
                       source_lookup.get(row["source"], {}).get("origin") ==
                       "reviewed-public-source-reference"]
    live_checked = [row for row in source_audit if
                    source_lookup.get(row["source"], {}).get("origin") ==
                    "approved-live-page-index"]
    if args.include_reviewed_public_source_references:
        public_source_handoff = {**public_source_handoff,
            "inspection_records": len(dynamic_checked),
            "parsed_channel_playlists": sum(
                row["status"] == "PARSED_NOT_PLAYBACK_VERIFIED" for row in dynamic_checked),
            "failed_source_fetches": sum(row["status"] == "FETCH_FAILED"
                                        for row in dynamic_checked)}
    if args.include_approved_live_page_indexes:
        live_page_handoff = {**live_page_handoff,
            "pages_inspected": len(live_checked),
            "pages_with_m3u_links": sum(
                row["status"] == "INDEX_LINKS_ONLY_NOT_PLAYBACK_VERIFIED"
                and row.get("entries", 0) > 0 for row in live_checked),
            "pages_unavailable": sum(row["status"] == "OPTIONAL_INDEX_FAILED"
                                     for row in live_checked)}
    result["public_source_reference_handoff"] = public_source_handoff
    result["approved_live_page_handoff"] = live_page_handoff
    result["all_discovery_sources_integrated_into_encrypted_archive"] = False
    from channel_watchlist import report as target_channel_report
    result["exact_named_channel_watchlist"] = target_channel_report(loaded, live)
    result["discovery_routing"] = (
        "STATIC_AND_APPROVED_M3U_SCANNED;"
        "REVIEWED_PUBLIC_GITHUB_GIST_GITLAB_CODEBERG_SCANNED_IF_OPTED;"
        "APPROVED_LIVE_HTML_INDEX_M3U_SCANNED_IF_PRESENT;"
        "YOUTUBE_AND_OFFICIAL_SITES_REFERENCE_ONLY_NOT_PLAYBACK_PROOF")
    result["spoken_turkish_or_azeri_verified"] = False
    result["ibo_device_verified"] = False
    if args.previous_report:
        from source_loss_audit import compare
        previous = json.loads(args.previous_report.read_text(encoding="utf-8"))
        result["source_loss_audit"] = compare(previous, result)
        previous_hashes = {item.get("url_sha256") for item in previous.get("candidates", []) if isinstance(item, dict) and item.get("url_sha256")}
        current_hashes = {item["url_sha256"] for item in result["candidates"]}
        result["historical_candidate_recovery"] = {"previous_hashes": len(previous_hashes), "matched_now": len(previous_hashes & current_hashes), "still_missing": len(previous_hashes - current_hashes), "method": "URL_SHA256_ONLY_NOT_PLAYBACK_VERIFIED"}
        if result["source_loss_audit"]["findings"]:
            print("WARNING: source loss requires review; see source_loss_audit in report")
    from source_integrity import verify
    integrity = verify(loaded, live, scopes, result["candidates"], entries,
                       turkish_candidate, recognized_channel_ids(loaded, scopes),
                       source_audit, errors)
    result["source_integrity"] = integrity
    result["candidate_integrity_verified"] = integrity["verified"]
    result["candidate_limit"] = args.limit
    result["candidates_truncated"] = args.limit > 0 and len(result["candidates"]) > args.limit
    if args.limit > 0:
        result["candidates"] = result["candidates"][:args.limit]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print(f"Sources: {len(loaded)} | Candidates: {len(result['candidates'])} | Errors: {len(errors)}")
    if not args.offline and not loaded:
        raise SystemExit("No sources accessible")
    if not args.offline and not integrity["verified"]:
        raise SystemExit("Source integrity INCOMPLETE; inspect candidates.json")

if __name__ == "__main__":
    main()

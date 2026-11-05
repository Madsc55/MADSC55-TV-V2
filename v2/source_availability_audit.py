#!/usr/bin/env python3
"""Review-only HTTP availability of configured public M3U sources.

Never fetches or probes media stream URLs, never modifies playlists.
The report is limited to source-level metadata; URL query secrets are omitted.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from webpage_source_discovery import candidate_url, public_hostname

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "sources.json"
REPORT = ROOT / "reports" / "source-availability-audit.json"
MAX_BYTES = 1024
def probe(url):
    if not candidate_url(url):
        return {"status": "INVALID_SOURCE_URL"}
    class SafeRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            p = urlsplit(newurl)
            if (p.scheme != "https" or not p.hostname or not public_hostname(p.hostname)
                    or p.username or p.password or p.port not in (None, 443)):
                raise ValueError("Unsafe source redirect")
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    opener = urllib.request.build_opener(SafeRedirect())
    req = urllib.request.Request(url, method="GET",
        headers={"User-Agent": "MADSC55-TV-V2-SourceAudit/1.0", "Range": "bytes=0-1023"})
    for attempt in range(3):
        try:
            with opener.open(req, timeout=12) as response:
                content = response.read(MAX_BYTES)
                valid_header = content.removeprefix(b"\xef\xbb\xbf").lstrip(b"\r\n\t ").startswith(b"#EXTM3U")
                if not valid_header and attempt < 2:
                    # Some upstream playlist services intermittently serve
                    # HTML/error pages with HTTP 200. Retry twice, but never
                    # pretend a persistent non-M3U response is a valid feed.
                    time.sleep(min(2 ** attempt, 3))
                    continue
                return {"status": "HTTP_OK" if valid_header else "INVALID_M3U",
                        "http_status": response.status, "sample_m3u_header": valid_header,
                        "invalid_m3u_retry_attempts": attempt if not valid_header else 0}
        except urllib.error.HTTPError as exc:
            if exc.code in (408, 429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(min(2 ** attempt, 3))
                continue
            return {"status": "HTTP_ERROR", "http_status": exc.code}
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            # Retry only temporary network errors. Unsafe redirects and
            # malformed HTTP responses must remain visible failures.
            if isinstance(exc, (urllib.error.URLError, TimeoutError)) and attempt < 2:
                time.sleep(min(2 ** attempt, 3))
                continue
            return {"status": "FETCH_ERROR", "error": type(exc).__name__}
    raise AssertionError("Unreachable source availability retry state")

def audit(sources, fetcher=probe):
    results = []
    for source in sources:
        outcome = fetcher(source["url"])
        results.append({"source_id": source["id"], "scope": source.get("scope", "candidate"),
                        **outcome})
    ok = sum(item["status"] == "HTTP_OK" for item in results)
    failures = len(results) - ok
    return {"schema": 1, "kind": "source-level-only", "source_count": len(results),
            "reachable_source_count": ok, "unreachable_source_count": failures,
            "coverage_status": ("NO_CONFIGURED_SOURCES" if not results else
                                "NO_SOURCES_REACHABLE" if not ok else
                                "COMPLETE" if not failures else "PARTIAL_SOURCE_AVAILABILITY"),
            "results": results, "playback_verified": False}

def active_source_inventory(configured):
    """Keep disabled historical feeds in inventory, but do not probe them."""
    if not isinstance(configured, list) or any(
            not isinstance(item, dict) or not isinstance(item.get("id"), str)
            for item in configured):
        raise ValueError("Malformed configured source inventory")
    ids = [row["id"] for row in configured]
    if any(not item.strip() for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("Empty or duplicate configured source ID")
    if any(type(row.get("enabled", True)) is not bool for row in configured):
        raise ValueError("Invalid configured source enabled flag")
    active = [row for row in configured if row.get("enabled", True)]
    disabled = [row["id"] for row in configured if not row.get("enabled", True)]
    return active, disabled


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-public-sources", action="store_true", required=True)
    args = parser.parse_args()
    configured = json.loads(CONFIG.read_text(encoding="utf-8"))["sources"]
    sources, disabled = active_source_inventory(configured)
    report = audit(sources)
    report["configured_total_including_disabled"] = len(configured)
    report["disabled_historical_sources_not_probed"] = disabled
    report["disabled_source_count"] = len(disabled)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Source-level audit:", report["source_count"], "sources; reachable:",
          report["reachable_source_count"], "unreachable:", report["unreachable_source_count"])
if __name__ == "__main__":
    main()

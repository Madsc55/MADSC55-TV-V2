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
from webpage_source_discovery import candidate_url

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config" / "sources.json"
REPORT = ROOT / "reports" / "source-availability-audit.json"
MAX_BYTES = 1024
def probe(url):
    if not candidate_url(url):
        return {"status": "INVALID_SOURCE_URL"}
    req = urllib.request.Request(url, method="GET",
        headers={"User-Agent": "MADSC55-TV-V2-SourceAudit/1.0", "Range": "bytes=0-1023"})
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            content = response.read(MAX_BYTES)
            return {"status": "HTTP_OK", "http_status": response.status,
                    "sample_m3u_header": b"#EXTM3U" in content[:256]}
    except urllib.error.HTTPError as exc:
        return {"status": "HTTP_ERROR", "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return {"status": "FETCH_ERROR", "error": type(exc).__name__}

def audit(sources, fetcher=probe):
    results = []
    for source in sources:
        outcome = fetcher(source["url"])
        results.append({"source_id": source["id"], "scope": source.get("scope", "candidate"),
                        **outcome})
    return {"schema": 1, "kind": "source-level-only", "source_count": len(results),
            "results": results, "playback_verified": False}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-public-sources", action="store_true", required=True)
    args = parser.parse_args()
    sources = json.loads(CONFIG.read_text(encoding="utf-8"))["sources"]
    report = audit(sources)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Source-level audit:", report["source_count"], "sources")
if __name__ == "__main__":
    main()

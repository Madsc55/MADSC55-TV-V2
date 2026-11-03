#!/usr/bin/env python3
"""Bounded read-only HTTP probe of public Turkish stream candidates."""
import concurrent.futures
import datetime
import json
import urllib.error
import urllib.parse
import urllib.request
from discover import ROOT

SOURCE = ROOT / "v2/reports/turkish-stream-candidates.json"
OUT = ROOT / "v2/reports/turkish-stream-probe.json"
MAX_WORKERS = 8
MAX_PROBES = 120

def probe(item):
    url = item["url"]
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return {"channel_id": item["channel_id"], "status": "INVALID_URL"}
    request = urllib.request.Request(url, headers={"User-Agent": "MADSC55-TV-V2-Probe/1.0",
                                                   "Range": "bytes=0-4095"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            sample = response.read(4096)
            final_url = response.geturl()
            code = response.status
            media_type = response.headers.get("Content-Type", "").lower()
        text = sample.decode("utf-8", errors="ignore").lstrip()
        looks_playlist = text.startswith("#EXTM3U") or "#EXT-X-" in text[:200]
        looks_transport = sample.startswith(bytes([0x47])) and len(sample) > 188
        status = "HTTP_RESPONSIVE_MEDIA_HINT" if (looks_playlist or looks_transport or "mpegurl" in media_type or "video/" in media_type) else "HTTP_RESPONSIVE_UNVERIFIED"
        return {"channel_id": item["channel_id"], "status": status,
                "http_status": code, "content_type": media_type[:100],
                "redirected": final_url != url}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {"channel_id": item["channel_id"], "status": "UNREACHABLE",
                "error_type": type(exc).__name__}

def main():
    report = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidates = report["candidates"][:MAX_PROBES]
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(probe, candidates))
    summary = {status: sum(x["status"] == status for x in results)
               for status in sorted({x["status"] for x in results})}
    output = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY_HTTP_HINT_NOT_PLAYBACK_VERIFICATION",
              "source_candidates": len(report["candidates"]),
              "header_required_deferred": len(report.get("header_required_review", [])),
              "probed": len(results), "summary": summary, "results": results}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Probe summary:", json.dumps(summary, sort_keys=True),
          "header-dependent deferred:", output["header_required_deferred"])
if __name__ == "__main__":
    main()

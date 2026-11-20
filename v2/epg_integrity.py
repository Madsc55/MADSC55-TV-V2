#!/usr/bin/env python3
"""Read-only bounded XMLTV integrity inspection of EPG feeds."""
import concurrent.futures
import datetime
import gzip
import io
import hashlib
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from discover import ROOT, LIVE, entries

OUT = ROOT / "v2" / "reports" / "epg-integrity.json"
MAX_BYTES = 20_000_000

def parse_xmltv_time(value):
    """Parse XMLTV YYYYMMDDHHMMSS with optional numeric UTC offset."""
    if not isinstance(value, str):
        raise ValueError("Invalid XMLTV timestamp")
    match = re.fullmatch(r"(\d{14})(?:\s*([+-])(\d{2})(\d{2}))?", value.strip())
    if not match:
        raise ValueError("Invalid XMLTV timestamp")
    base = datetime.datetime.strptime(match.group(1), "%Y%m%d%H%M%S")
    if match.group(2):
        hours, remainder = int(match.group(3)), int(match.group(4))
        if remainder >= 60 or hours > 14 or (hours == 14 and remainder != 0):
            raise ValueError("Invalid UTC offset")
        minutes = hours * 60 + remainder
        if match.group(2) == "-":
            minutes = -minutes
        return base.replace(tzinfo=datetime.timezone(datetime.timedelta(minutes=minutes)))
    return base.replace(tzinfo=datetime.timezone.utc)

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Reject feed redirects before a second network request is sent."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("XMLTV feed redirect refused")


def inspect(url, playlist_ids):
    result = {"url_sha256": hashlib.sha256(url.encode()).hexdigest(), "status": "UNVERIFIED"}
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or "\\" in url):
        result["status"] = "NON_HTTPS"
        return result
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MADSC55-V2-EPG-Audit/1.0"})
        with urllib.request.build_opener(_NoRedirect).open(req, timeout=16) as res:
            data = res.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            result["status"] = "TOO_LARGE_FOR_AUDIT"
            return result
        if data.startswith(b"\x1f\x8b"):
            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                data = gz.read(120_000_001)
        if len(data) > 120_000_000:
            result["status"] = "DECOMPRESSED_TOO_LARGE"
            return result
        # Keep external entity declarations out of XMLTV inspection even when
        # the input passed compressed and uncompressed size limits.
        if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
            result["status"] = "XMLTV_DTD_REJECTED"
            return result
        root = ET.fromstring(data)
        if root.tag != "tv":
            result["status"] = "NOT_XMLTV"
            return result
        channel_counts = Counter(node.get("id") for node in root.iter("channel") if node.get("id"))
        channels = set(channel_counts)
        now = datetime.datetime.now(datetime.timezone.utc)
        programmes = 0
        current_programmes = 0
        current_titled_programmes = 0
        expired_programme_intervals = 0
        latest_programme_stop_utc = None
        invalid_programme_intervals = 0
        missing_programme_titles = 0
        matched_programme_ids = set()
        valid_matched_programme_ids = set()
        current_matched_programme_ids = set()
        for node in root.iter("programme"):
            programmes += 1
            channel_id = node.get("channel")
            if channel_id in playlist_ids:
                matched_programme_ids.add(channel_id)
            title = node.find("title")
            has_title = title is not None and bool("".join(title.itertext()).strip())
            if not has_title:
                missing_programme_titles += 1
            start, stop = node.get("start", ""), node.get("stop", "")
            try:
                start_at = parse_xmltv_time(start)
                stop_at = parse_xmltv_time(stop)
                if stop_at <= start_at:
                    invalid_programme_intervals += 1
                    continue
                # Only unique XMLTV channel declarations and valid time ranges
                # qualify for the stricter evidence counts. The legacy raw
                # matched-programme count is retained for compatibility.
                matching_unique = channel_id in playlist_ids and channel_counts[channel_id] == 1 and has_title
                if matching_unique:
                    valid_matched_programme_ids.add(channel_id)
                if latest_programme_stop_utc is None or stop_at > latest_programme_stop_utc:
                    latest_programme_stop_utc = stop_at
                if stop_at < now:
                    expired_programme_intervals += 1
                if start_at <= now <= stop_at:
                    current_programmes += 1
                    if has_title and channel_id in playlist_ids and channel_counts.get(channel_id, 0) == 1:
                        current_titled_programmes += 1
                    if matching_unique:
                        current_matched_programme_ids.add(channel_id)
            except ValueError:
                invalid_programme_intervals += 1
        result.update(status="XMLTV_VALID", channels=len(channels), programmes=programmes,
                      playlist_id_matches=len(channels & playlist_ids),
                      matched_programme_channel_ids=len(matched_programme_ids),
                      valid_matched_programme_channel_ids=len(valid_matched_programme_ids),
                      current_matched_programme_channel_ids=len(current_matched_programme_ids),
                      duplicate_channel_ids=sum(count > 1 for count in channel_counts.values()),
                      current_programme_intervals=current_programmes,
                      current_titled_unique_programme_intervals=current_titled_programmes,
                      expired_programme_intervals=expired_programme_intervals,
                      latest_programme_stop_utc=(latest_programme_stop_utc.isoformat() if latest_programme_stop_utc else None),
                      invalid_programme_intervals=invalid_programme_intervals,
                      missing_programme_titles=missing_programme_titles,
                      playlist_id_match_rate=round(len(channels & playlist_ids) / len(playlist_ids), 4) if playlist_ids else None)
    except (OSError, ValueError, ET.ParseError, EOFError, gzip.BadGzipFile, MemoryError) as exc:
        result.update(status="EPG_UNVERIFIED", error_type=type(exc).__name__)
    return result

def main():
    sources = json.loads((ROOT / "v2" / "epg_sources.json").read_text(encoding="utf-8"))["sources"]
    playlist_ids = {e["tvg_id"] for e in entries(LIVE.read_text(encoding="utf-8-sig")) if e["tvg_id"]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        checks = list(pool.map(lambda url: inspect(url, playlist_ids), sources))
    # Per-feed observations are not unique channel counts across feeds.
    valid_feeds = [item for item in checks if item["status"] == "XMLTV_VALID"]
    source_coverage = {
        "configured_sources": len(sources),
        "valid_xmltv_sources": len(valid_feeds),
        "unverified_sources": len(sources) - len(valid_feeds),
        "feeds_with_valid_matched_programmes": sum(
            item.get("valid_matched_programme_channel_ids", 0) > 0 for item in valid_feeds
        ),
        "feeds_with_current_matched_programmes": sum(
            item.get("current_matched_programme_channel_ids", 0) > 0 for item in valid_feeds
        ),
        "historical_303_gaps_resolved": None,
        "historical_gap_status": "UNVERIFIED_REQUIRES_INDEPENDENT_ID_EVIDENCE",
    }
    report = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; XMLTV numeric UTC offsets are respected; missing offsets assume UTC; matching IDs do not prove accurate schedules",
              "status_counts": dict(Counter(x["status"] for x in checks)),
              "source_coverage": source_coverage,
              "playlist_distinct_tvg_ids": len(playlist_ids), "sources": checks}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("EPG XMLTV validation:", report["status_counts"])

if __name__ == "__main__":
    main()

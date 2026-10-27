#!/usr/bin/env python3
"""Read-only Turkish TV discovery and playlist health audit."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import re
import urllib.request
import urllib.error
import shutil
import subprocess
import os
import urllib.parse
from collections import Counter
from discover import ROOT, LIVE, SOURCES, fetch, entries

OUT = ROOT / "v2" / "reports" / "turkish-tv-health.json"
RADIO = re.compile(r"\b(radio|radyo|fm|audio only)\b", re.I)
LOCKED = re.compile(r"\b(drm|widevine|playready|encrypted|şifreli|sifreli)\b", re.I)
TURKISH = re.compile(r"\b(turk|türk|turkiye|türkiye|trt|atv|show tv|kanal d|star tv|now tv|haber|ulusal)\b", re.I)

def identity(e):
    return (e["tvg_id"] or e["name"]).strip().casefold()

def digest(url):
    return hashlib.sha256(url.encode()).hexdigest()

def satellite_directory():
    """Public channel metadata directory: suggestions only, not verified streams."""
    endpoint = "https://iptv-org.github.io/api/channels.json"
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "MADSC55-V2-Audit/1.0"})
        with urllib.request.urlopen(req, timeout=20) as res:
            data = res.read(30_000_001)
        if len(data) > 30_000_000:
            return [], "DIRECTORY_TOO_LARGE"
        catalog = json.loads(data)
        found = []
        for item in catalog:
            if item.get("country") != "TR" or item.get("is_nsfw"):
                continue
            found.append({"name": str(item.get("name", "")).upper(), "channel_id": item.get("id", ""),
                          "website_host": urllib.parse.urlsplit(item.get("website") or "").hostname or "",
                          "status": "DIRECTORY_ONLY_NO_STREAM_VERIFICATION"})
        return found[:500], None
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return [], type(exc).__name__

def playback_probe(url):
    """Decode a short media sample with ffprobe; no downloads or recording."""
    if not shutil.which("ffprobe"):
        return "DECODER_UNAVAILABLE"
    try:
        p = subprocess.run(["ffprobe", "-v", "error", "-rw_timeout", "6000000",
                            "-analyzeduration", "1500000", "-probesize", "1000000",
                            "-show_entries", "stream=codec_type,codec_name,width,height",
                            "-of", "json", url], capture_output=True, text=True, timeout=12)
        if p.returncode != 0:
            return "PLAYBACK_UNVERIFIED"
        streams = json.loads(p.stdout).get("streams", [])
        return "DECODABLE_VIDEO" if any(s.get("codec_type") == "video" for s in streams) else ("AUDIO_ONLY" if streams else "PLAYBACK_UNVERIFIED")
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return "PLAYBACK_UNVERIFIED"

def check(e):
    url = e["url"]
    result = {"name": e["name"].upper(), "id": identity(e), "url_sha256": digest(url),
              "status": "UNVERIFIED", "resolution": "UNKNOWN"}
    if not url.startswith(("http://", "https://")):
        return result
    if "youtube.com" in url or "youtu.be" in url:
        if not shutil.which("yt-dlp"):
            result["status"] = "YOUTUBE_TOOL_UNAVAILABLE"
            return result
        try:
            proc = subprocess.run(["yt-dlp", "--no-playlist", "--skip-download", "--dump-single-json", "--no-warnings", "--socket-timeout", "8", url], capture_output=True, text=True, timeout=18)
            if proc.returncode == 0:
                meta = json.loads(proc.stdout)
                result["status"] = "YOUTUBE_METADATA_AVAILABLE_PLAYBACK_UNCONFIRMED" if meta.get("is_live") or meta.get("live_status") == "is_live" else "YOUTUBE_NOT_LIVE_OR_UNVERIFIED"
                result["resolution"] = str(meta.get("height") or "UNKNOWN")
            else:
                result["status"] = "YOUTUBE_UNVERIFIED"
        except (OSError, subprocess.TimeoutExpired, ValueError, json.JSONDecodeError):
            result["status"] = "YOUTUBE_UNVERIFIED"
        return result
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MADSC55-TV-V2", "Range": "bytes=0-32767"})
        with urllib.request.urlopen(req, timeout=9) as res:
            sample = res.read(32768)
            mime = res.headers.get("Content-Type", "").lower()
            status = res.status
        txt = sample.decode("utf-8", errors="replace")
        manifest = "#EXTM3U" in txt and ("#EXT-X-" in txt or "#EXTINF:" in txt)
        transport = sample.startswith(bytes.fromhex("4740")) or ("video/" in mime)
        if status in (200, 206) and (manifest or transport):
            result["status"] = "STREAM_RESPONDS_PLAYBACK_UNCONFIRMED"
            if "#EXT-X-STREAM-INF" in txt:
                resolutions = re.findall(r"RESOLUTION=(\d+x\d+)", txt)
                if resolutions:
                    result["resolution"] = ",".join(sorted(set(resolutions)))
        else:
            result["status"] = "UNVERIFIED"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        result["status"] = "UNREACHABLE_OR_TIMEOUT"
    return result

def main():
    live = list(entries(LIVE.read_text(encoding="utf-8-sig")))
    categories = Counter(e["group"] or "KATEGORİSİZ" for e in live)
    unique = {identity(e) for e in live}
    live_urls = {e["url"] for e in live}
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    discovered = {}
    errors = []
    for source in sources:
        try:
            for e in entries(fetch(source["url"])):
                if RADIO.search(e["name"] + " " + e["group"]) or LOCKED.search(e["name"] + " " + e["group"]):
                    continue
                is_tr = source.get("scope") == "TR" or e["tvg_id"].lower().endswith(".tr") or bool(TURKISH.search(e["name"] + " " + e["group"]))
                if not is_tr or identity(e) in unique or e["url"] in live_urls:
                    continue
                discovered.setdefault((identity(e), digest(e["url"])), e)
        except Exception as exc:
            errors.append({"source": source["id"], "error": type(exc).__name__})
    # Limit remote probes per run; live channels take precedence.
    candidate_items = list(discovered.values())[:300]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        live_checks = list(pool.map(check, live))
        candidate_checks = list(pool.map(check, candidate_items))
    # Limit decoder work to a bounded sample; metadata probes are not a continuous playback guarantee.
    responsive = [(i, e) for i, (e, check_result) in enumerate(zip(live, live_checks))
                  if check_result["status"] == "STREAM_RESPONDS_PLAYBACK_UNCONFIRMED"]
    # Rotate the bounded decoder sample daily to cover more of the playlist over time.
    sample_limit = max(0, min(1039, int(os.environ.get("MADSC55_DECODER_SAMPLE", "30"))))
    offset = datetime.datetime.now(datetime.timezone.utc).date().toordinal() * sample_limit
    eligible = ([responsive[(offset + j) % len(responsive)] for j in range(min(sample_limit, len(responsive)))]
                if responsive else [])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        decoded = list(pool.map(lambda pair: playback_probe(pair[1]["url"]), eligible))
    for (idx, _), status in zip(eligible, decoded):
        live_checks[idx]["decoder_status"] = status
    # Only responsive candidates are presented; never claim confirmed playback.
    candidates = []
    for e, c in zip(candidate_items, candidate_checks):
        if c["status"] == "STREAM_RESPONDS_PLAYBACK_UNCONFIRMED":
            candidates.append({**c, "logo_url_sha256": digest(e["logo"]) if e["logo"] else "", "epg_id": e["tvg_id"], "category_suggestion": (e["group"] or "YENİ GELEN").upper()})
    # Verify short video decoding for responsive new candidates, without changing the playlist.
    responsive_candidate_indexes = [i for i, item in enumerate(candidate_checks)
                                    if item["status"] == "STREAM_RESPONDS_PLAYBACK_UNCONFIRMED"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        candidate_decoders = list(pool.map(lambda i: playback_probe(candidate_items[i]["url"]), responsive_candidate_indexes))
    for i, decoder_status in zip(responsive_candidate_indexes, candidate_decoders):
        candidate_checks[i]["decoder_status"] = decoder_status
    candidates = []
    for e, check_result in zip(candidate_items, candidate_checks):
        if check_result["status"] == "STREAM_RESPONDS_PLAYBACK_UNCONFIRMED":
            candidates.append({**check_result, "logo_url_sha256": digest(e["logo"]) if e["logo"] else "",
                               "epg_id": e["tvg_id"], "category_suggestion": (e["group"] or "YENİ GELEN").upper()})
    # Export a standalone IBO-compatible YEDEKLER trial list; never overwrite existing backups.
    def m3u_attr(value):
        return str(value or "").replace("\\r", " ").replace("\\n", " ").replace('"', "'")
    trial = ["#EXTM3U"]
    for e, check_result in zip(candidate_items, candidate_checks):
        if check_result.get("decoder_status") != "DECODABLE_VIDEO":
            continue
        if not e["url"].startswith(("https://", "http://")):
            continue
        trial.append(f'#EXTINF:-1 tvg-id="{m3u_attr(e["tvg_id"])}" tvg-logo="{m3u_attr(e["logo"])}" group-title="YEDEKLER TEST", {m3u_attr(e["name"])}')
        trial.append(e["url"])
    trial_path = ROOT / "v2" / "reports" / "YEDEKLER_TEST.m3u8"
    trial_path.parent.mkdir(parents=True, exist_ok=True)
    trial_path.write_text("\\n".join(trial) + "\\n", encoding="utf-8")
    print("YEDEKLER trial playlist decoded-video entries:", (len(trial) - 1) // 2)
    directory, directory_error = satellite_directory()
    report = {"schema": 1, "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "policy": "READ_ONLY; no playlist writes; network response is not playback confirmation",
              "playlist_entries": len(live), "unique_channel_identities": len(unique),
              "category_counts": dict(sorted(categories.items())), "live_status_counts": dict(Counter(x["status"] for x in live_checks)),
              "live_checks": live_checks, "decoder_sample_size": len(eligible),
              "decoder_status_counts": dict(Counter(x.get("decoder_status", "NOT_SAMPLED") for x in live_checks)), "candidate_status": "NETWORK_RESPONSIVE_ONLY_NOT_APPROVED",
              "candidate_checked": len(candidate_items), "candidates": candidates,
              "candidate_decoder_status_counts": dict(Counter(x.get("decoder_status", "NOT_TESTED") for x in candidates)), "source_errors": errors,
              "turkish_channel_directory": directory, "directory_error": directory_error,
              "directory_note": "Public metadata catalog, not satellite reception verification"}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    print("Live entries:", len(live), "Unique IDs:", len(unique), "Candidate probes:", len(candidate_items), "Responsive candidates:", len(candidates))
    print("New candidate names and decoder evidence:", [(x["name"], x.get("decoder_status", "NOT_TESTED")) for x in candidates])

if __name__ == "__main__":
    main()

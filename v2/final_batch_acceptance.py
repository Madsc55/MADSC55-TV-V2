#!/usr/bin/env python3
"""Read-only global M3U AV audit; plaintext URLs never leave process memory."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from discover import (ROOT, SOURCES, LIVE, DYNAMIC, GITHUB_APPROVALS,
    FORGE, FORGE_APPROVALS, fetch, entries, load_original_run60_sources,
    normalize_original_source_text, approved_github_source, public_metadata)
from historical_url_recovery import validate_url
from historical_targeted_playback import public_dns, classify_probe_failure
from stage3_sealed_export import seal_rows

REPORTS = ROOT / "v2/reports/ci"
KEY = ROOT / "v2/config/stage5_recovery_public.pem"
HISTORY = ROOT / "v2/history/stage3-4955-hash-only.jsonl"
HISTORY_SHA = "ee00a844a028e3410715d411467a2d3306f5f5cc4565766140b6438e786cdd27"
LIVE_BLOB = "4b1c3cea4b5107a425abab60f62d41f9f81e05a7"

def sha(v):
    return hashlib.sha256(v.encode("utf-8") if isinstance(v, str) else v).hexdigest()

def gitblob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def route(meta, scopes):
    s = " ".join(str(meta.get(x, "")) for x in ("tvg_id", "group", "name")).casefold()
    tvg = str(meta.get("tvg_id", "")).casefold()
    tr = bool(re.search(r"(?:^|[^a-z])(?:trt|türk|turk|turkish|türkiye|turkiye)(?:$|[^a-z])|(?:[._-])tr(?:[._-]|$)", s))
    az = bool(re.search(r"(?:^|[^a-z])(?:azeri|azerbaijan|azerbaycan|azərbaycan)(?:$|[^a-z])|(?:[._-])az(?:[._-]|$)", s))
    if re.search(r"(?:[._-])(?:az|aze)$", tvg): az = True
    if re.search(r"(?:[._-])(?:tr|tur)$", tvg): tr = True
    if tr != az: return "TR_METADATA_HINT" if tr else "AZ_METADATA_HINT"
    if scopes == {"TR"}: return "TR_SOURCE_HINT"
    if scopes == {"AZ"}: return "AZ_SOURCE_HINT"
    if re.search(r"(?:[._-])(?:de|en|eng|fr|es|it|ru|pl|se|sv)$", tvg):
        return "FOREIGN_METADATA_HINT"
    return "LANGUAGE_UNVERIFIED"

def sources(require_public_reports=False):
    config = json.loads(SOURCES.read_text())["sources"]
    entries_ = [dict(x) for x in config if x.get("enabled", True) is not False]
    hist = load_original_run60_sources(ROOT / "v2/history/run60-dynamic-source-ledger.json")
    known = {x["url"] for x in entries_}
    for row in hist:
        if row["url"] not in known:
            entries_.append(row); known.add(row["url"])
    if DYNAMIC.is_file() and GITHUB_APPROVALS.is_file():
        approved = set(json.loads(GITHUB_APPROVALS.read_text())["approved_sha256"])
        for row in json.loads(DYNAMIC.read_text()).get("sources", [])[:240]:
            url = row.get("url", "")
            if approved_github_source(url, approved) and url not in known:
                entries_.append({"id": "github-final-" + sha(url)[:16],
                                 "url": url, "scope": "candidate"})
                known.add(url)
    if FORGE.is_file() and FORGE_APPROVALS.is_file():
        from forge_source_review import approved_sources
        approvals = set(json.loads(FORGE_APPROVALS.read_text()).get("approved_sha256", []))
        for row in approved_sources(json.loads(FORGE.read_text()), approvals):
            if row["url"] not in known:
                entries_.append(row); known.add(row["url"])
    # Include bounded validated-for-inspection M3U references in read-only AV
    # probing, never in protected playlist publication.
    github_report = ROOT / "v2/reports/github-source-discovery.json"
    forge_report = ROOT / "v2/reports/forge-source-discovery.json"
    if require_public_reports and not (github_report.is_file() and forge_report.is_file()):
        raise ValueError("Required reviewed public M3U source reports are missing")
    if github_report.is_file() and forge_report.is_file():
        from public_source_handoff import staged_references
        reviewed, handoff = staged_references(github_report, forge_report, known)
        for public_source in reviewed:
            if public_source["url"] not in known:
                entries_.append(public_source)
                known.add(public_source["url"])
        if require_public_reports and not all(handoff["report_checked"].values()):
            raise ValueError("Incomplete public source inspection handoff")
    from document_platform_discovery import accepted_sources
    for doc_source in accepted_sources():
        if doc_source["url"] not in known:
            entries_.append(doc_source)
            known.add(doc_source["url"])
    ix = ROOT / "v2/config/playlist-index-pages.json"
    if ix.is_file():
        from webpage_source_discovery import discover_playlist_links
        for page in json.loads(ix.read_text()).get("pages", []):
            try:
                html = fetch(page["url"], allow_html=True)
                for url in discover_playlist_links(page["url"], html)[:30]:
                    if url not in known:
                        entries_.append({"id": "index-" + sha(url)[:16],
                                         "url": url, "scope": "candidate"})
                        known.add(url)
            except (OSError, ValueError, TypeError, KeyError, UnicodeError):
                entries_.append({"id": "index-failed-" + str(page.get("id", "?"))[:32],
                                 "url": None, "scope": "candidate"})
    return entries_, len(config), len(hist)

def fetch_one(source):
    if not source.get("url"): return source["id"], [], "INDEX_UNAVAILABLE"
    try:
        body = normalize_original_source_text(source, fetch(source["url"]))
        if not body.lstrip().startswith("#EXTM3U"):
            return source["id"], [], "INVALID_SOURCE"
        result = [x for x in entries(body) if validate_url(x["url"])]
        return source["id"], result, "FETCHED"
    except Exception as exc:
        return source["id"], [], ("FETCH_FAILED_" + type(exc).__name__)[:60]

def probe(pair):
    digest, url = pair
    failed = {"url_sha256": digest, "status": "UNVERIFIED",
              "video": False, "audio": False, "decoded": False, "audio_lang_tags": []}
    if not public_dns(url):
        return {**failed, "status": "UNSAFE_OR_UNRESOLVED_HOST"}
    try:
        command = ["ffprobe", "-hide_banner", "-loglevel", "error",
                   "-rw_timeout", "5000000", "-protocol_whitelist",
                   "http,https,tcp,tls,crypto", "-analyzeduration", "2000000",
                   "-probesize", "65536",
                   "-show_entries", "stream=codec_type:stream_tags=language",
                   "-of", "json", url]
        p = subprocess.run(command, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=16)
        if p.returncode:
            return {**failed, "status": "PROBE_FAILED_" + classify_probe_failure(p.stderr)}
        streams = json.loads(p.stdout).get("streams", [])
        video = any(x.get("codec_type") == "video" for x in streams)
        audio = any(x.get("codec_type") == "audio" for x in streams)
        lang = sorted({str(x.get("tags", {}).get("language", "")).lower()
                       for x in streams if x.get("codec_type") == "audio"
                       and re.fullmatch(r"[A-Za-z]{2,8}", str(x.get("tags", {}).get("language", "")))})
        decoded = False
        if video and audio:
            cmd = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                   "-rw_timeout", "5000000", "-protocol_whitelist",
                   "http,https,tcp,tls,crypto", "-i", url,
                   "-map", "0:v:0", "-map", "0:a:0", "-t", "1", "-f", "null", "-"]
            decoded = subprocess.run(cmd, capture_output=True, text=True,
                                     stdin=subprocess.DEVNULL, timeout=20).returncode == 0
        status = ("VIDEO_AUDIO_DECODED" if decoded else
                  "VIDEO_AUDIO_STREAMS_ONLY" if video and audio else
                  "VIDEO_ONLY" if video else "AUDIO_ONLY" if audio else "NO_AV")
        return {**failed, "status": status, "video": video,
                "audio": audio, "decoded": decoded, "audio_lang_tags": lang}
    except (OSError, ValueError, subprocess.TimeoutExpired, TypeError):
        return {**failed, "status": "PROBE_UNCONFIRMED"}

def report(source_results, inventory, checks, *, configured, historic, expired, elapsed):
    failures = {name: status for name, _, status in source_results if status != "FETCHED"}
    candidates, route_counts = [], Counter()
    for digest, item in sorted(inventory.items()):
        result = checks.get(digest, {"status": "NOT_PROBED_BUDGET",
            "video": False, "audio": False, "decoded": False, "audio_lang_tags": []})
        lang_route = route(item["meta"], item["scopes"])
        route_counts[lang_route] += 1
        candidates.append({"url_sha256": digest, "source_ids": sorted(item["source_ids"]),
            "name": public_metadata(item["meta"].get("name", "")),
            "language_route": lang_route,
            "audio_tags_not_spoken_language_proof": result["audio_lang_tags"],
            "spoken_language_verified": False, "status": result["status"],
            "video": result["video"], "audio": result["audio"],
            "decoded": result["decoded"], "ibo_player_verified": False})
    return {
        "schema": 1, "kind": "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE",
        "configured_source_count": configured, "original_run60_source_count": historic,
        "source_fetch_count": len(source_results),
        "source_success_count": sum(x[2] == "FETCHED" for x in source_results),
        "failed_source_ids": failures, "unique_url_candidates": len(inventory),
        "probed": len(checks), "unprobed": len(inventory)-len(checks),
        "probe_budget_expired": expired,
        "av_status_counts": dict(Counter(x["status"] for x in checks.values())),
        "audio_video_decoded": sum(x["decoded"] for x in checks.values()),
        "metadata_language_route_counts": dict(route_counts),
        "spoken_language_verified": 0,
        "readiness": "REVIEW_REQUIRED",
        "source_metadata_and_audio_track_language_tags_are_not_speech_proof": True,
        "protected_main_playlist_modified": False, "ibo_player_verified": False,
        "plaintext_url_in_public_report": False, "elapsed_seconds": round(elapsed, 1),
        "candidates": candidates}

def resume_checks(prior, inventory):
    """Accept matching AV evidence only; transient failures get re-probed."""
    if prior.get("schema") != 1 or prior.get("kind") != "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE":
        raise ValueError("Invalid prior report")
    rows = prior.get("candidates")
    if not isinstance(rows, list) or len(rows) != prior.get("unique_url_candidates"):
        raise ValueError("Invalid prior candidate count")
    checks = {}
    seen = set()
    allowed = {"VIDEO_AUDIO_DECODED", "VIDEO_AUDIO_STREAMS_ONLY",
               "VIDEO_ONLY", "AUDIO_ONLY", "NO_AV"}
    expected_flags = {"VIDEO_AUDIO_DECODED": (True, True, True),
                      "VIDEO_AUDIO_STREAMS_ONLY": (True, True, False),
                      "VIDEO_ONLY": (True, False, False),
                      "AUDIO_ONLY": (False, True, False),
                      "NO_AV": (False, False, False)}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid prior candidate")
        digest = row.get("url_sha256")
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest) or digest in seen:
            raise ValueError("Invalid or repeated candidate digest")
        seen.add(digest)
        status = row.get("status")
        if digest not in inventory or status not in allowed:
            continue
        if any(type(row.get(k)) is not bool for k in ("video", "audio", "decoded")):
            raise ValueError("Invalid AV evidence flags")
        if (row["video"], row["audio"], row["decoded"]) != expected_flags[status]:
            raise ValueError("Inconsistent AV status flags")
        tags = row.get("audio_tags_not_spoken_language_proof", [])
        if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
            raise ValueError("Invalid audio tags")
        checks[digest] = {"url_sha256": digest, "status": status,
                          "video": row["video"], "audio": row["audio"],
                          "decoded": row["decoded"], "audio_lang_tags": tags}
    return checks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--budget-seconds", type=int, default=14400)
    parser.add_argument("--reuse-report", type=Path, help="Prior hash-only anonymous AV evidence; never plaintext URLs")
    parser.add_argument("--require-public-sources", action="store_true",
                        help="Fail rather than silently skip reviewed dynamic source reports")
    a = parser.parse_args()
    if not 1 <= a.workers <= 32 or not 60 <= a.budget_seconds <= 14400:
        parser.error("Unsafe scan limits")
    if sha(HISTORY.read_bytes()) != HISTORY_SHA or gitblob(LIVE.read_bytes()) != LIVE_BLOB:
        raise SystemExit("Protected data fingerprint differs")
    t0 = time.monotonic()
    all_sources, configured, historic = sources(require_public_reports=a.require_public_sources)
    with ThreadPoolExecutor(max_workers=12) as executor:
        outputs = list(executor.map(fetch_one, all_sources))
    scopes = {x["id"]: x.get("scope", "candidate") for x in all_sources}
    inventory = {}
    for source, rows, status in outputs:
        if status != "FETCHED": continue
        for row in rows:
            url = row["url"]
            digest = sha(url)
            old = inventory.setdefault(digest, {"url": url, "meta": row,
                                                 "source_ids": set(), "scopes": set()})
            if old["url"] != url: raise ValueError("Hash collision")
            old["source_ids"].add(source); old["scopes"].add(scopes[source])
    entries_ = sorted(inventory.items())
    checks = {}
    if a.reuse_report:
        if not a.reuse_report.is_file():
            raise SystemExit("Required prior AV evidence is missing")
        prior = json.loads(a.reuse_report.read_text(encoding="utf-8"))
        if prior.get("kind") != "V2_WORLDWIDE_READ_ONLY_FINAL_ACCEPTANCE":
            raise SystemExit("Invalid prior AV evidence report")
        # Recheck transient failures; never freeze an outage into historical evidence.
        checks = resume_checks(prior, inventory)
        print("Reused prior hash-only AV evidence:", len(checks), flush=True)
    expired = False
    deadline = t0 + a.budget_seconds
    pending = [(digest, item["url"]) for digest, item in entries_ if digest not in checks]
    with ThreadPoolExecutor(max_workers=a.workers) as executor:
        for offset in range(0, len(pending), 128):
            if time.monotonic() > deadline:
                expired = True; break
            rows = pending[offset:offset+128]
            if not rows: continue
            for result in executor.map(probe, rows):
                checks[result["url_sha256"]] = result
            if offset % 1280 == 0:
                print("Probed:", len(checks), "/", len(entries_), flush=True)
    expired = len(checks) < len(entries_)
    REPORTS.mkdir(parents=True, exist_ok=True)
    sealed = []
    for i, offset in enumerate(range(0, len(entries_), 4000), 1):
        chunk = entries_[offset:offset+4000]
        rows = []
        for digest, item in chunk:
            p = checks.get(digest, {"status": "NOT_PROBED_BUDGET",
                                   "video": False, "audio": False, "decoded": False})
            rows.append({"url": item["url"], "url_sha256": digest,
                "source_ids": sorted(item["source_ids"]),
                "metadata_route": route(item["meta"], item["scopes"]),
                "video_stream": p["video"], "audio_stream": p["audio"],
                "av_decode_verified": p["decoded"], "probe_status": p["status"]})
        path = REPORTS / ("final-worldwide-%03d.sealed" % i)
        seal_rows(rows, ROOT / "v2/config/stage5_recovery_public.pem", path)
        sealed.append({"name": path.name, "count": len(rows), "sha256": sha(path.read_bytes())})
    result = report(outputs, inventory, checks, configured=configured,
                    historic=historic, expired=expired, elapsed=time.monotonic()-t0)
    result["sealed_url_count"] = sum(x["count"] for x in sealed)
    result["sealed_artifacts"] = sealed
    path = REPORTS / "final-worldwide-acceptance.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n")
    print("FINAL_ANONYMOUS_COUNTS", json.dumps({k: v for k,v in result.items()
        if k not in ("candidates", "failed_source_ids", "sealed_artifacts")}, ensure_ascii=False))
    if result["sealed_url_count"] != len(inventory):
        raise SystemExit("Missing encrypted candidate identities")

if __name__ == "__main__":
    main()

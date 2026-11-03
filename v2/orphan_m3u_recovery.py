#!/usr/bin/env python3
"""Repair evidence for only the 41 orphan entries in 3 known M3U documents.

This job never modifies upstream feeds or the protected IBO playlist. Exact
#EXTINF matches from historical Git commits / the publisher's official
alternate feeds are candidate URL evidence; FFprobe A/V is required before a
candidate is called playable. Plaintext stream URLs are held only in memory
and, for proven A/V successes, sealed to the existing RSA public key.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, urlencode

from stage3_historical_source_recovery import _read
from historical_url_recovery import validate_url
from historical_targeted_playback import probe_one
from stage3_sealed_export import seal_rows

ORIGINALS = (
    ("discevisita-tr", "discevisita/iptv", "tr.m3u"),
    ("github-auto-24", "Hannstcott/SunshineTr", "sunshinetv.m3u"),
)
ONUR = ("onureroz-turk-karma", "https://onureroz.com/indirmeler/turk/karma-index.m3u")
ONUR_ALTERNATES = (
    "https://onureroz.com/indirmeler/turk/index.m3u",
    "https://onureroz.com/indirmeler/turk/all.m3u",
)
MAX_FILE_BYTES = 32_000_000
MAX_CANDIDATE_STREAMS = 100


def _hash(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _read_document(url):
    raw = _read(url)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Playlist exceeds safe byte limit")
    text = raw.decode("utf-8-sig", errors="replace")
    if not text.lstrip().startswith(("#EXTM3U", "#EXTINF:")):
        raise ValueError("Not an M3U document")
    return text


def parse_exact_pairs(payload):
    """Return exact metadata-keyed orphan lines and valid URL candidates."""
    if not isinstance(payload, str):
        raise TypeError("M3U document must be text")
    rows = defaultdict(set)
    orphan = []
    pending = None

    def orphaned(reason, previous):
        n, extinf = previous
        orphan.append({"line_number": n, "extinf_sha256": _hash(extinf),
                       "extinf": extinf, "reason": reason})

    for n, raw in enumerate(payload.splitlines(), 1):
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            if pending:
                orphaned("MISSING_URI_BEFORE_NEXT_EXTINF", pending)
            pending = (n, line)
        elif line and not line.startswith("#") and pending:
            n0, extinf = pending
            if validate_url(line):
                rows[extinf].add(line)
            elif line.startswith(("[NO PUBLIC STREAM]", "[NO STREAM]")):
                orphaned("EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER", pending)
            else:
                orphaned("INVALID_OR_RELATIVE_STREAM_REFERENCE", pending)
            pending = None
    if pending:
        orphaned("TRAILING_EXTINF_WITHOUT_URI", pending)
    return rows, orphan


def historical_revisions(repo, path, *, limit=20):
    if (repo, path) not in {(r, p) for _, r, p in ORIGINALS}:
        raise ValueError("Historical source outside pinned scope")
    owner, name = repo.split("/")
    url = ("https://api.github.com/repos/" + quote(owner) + "/" + quote(name)
           + "/commits?" + urlencode({"path": path, "per_page": str(limit)}))
    data = json.loads(_read(url, api=True))
    if not isinstance(data, list):
        raise ValueError("GitHub history is not a list")
    shas = []
    for entry in data[:limit]:
        sha = entry.get("sha") if isinstance(entry, dict) else None
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha):
            raise ValueError("Untrusted historical Git revision")
        shas.append(sha)
    return shas


def find_historical(orphan_rows, repo, path, *, limit=20,
                    commits=historical_revisions, reader=_read_document):
    if (repo, path) not in {(r, p) for _, r, p in ORIGINALS}:
        raise ValueError("Historical source outside pinned scope")
    wanted = {o["extinf"] for o in orphan_rows}
    matches = defaultdict(dict)
    files_read = 0
    failures = 0
    revisions = commits(repo, path, limit=limit)
    for revision in revisions:
        url = ("https://raw.githubusercontent.com/" + repo + "/" + revision
               + "/" + quote(path, safe="/"))
        try:
            rows, _ = parse_exact_pairs(reader(url))
            files_read += 1
            for extinf in wanted & rows.keys():
                for stream in rows[extinf]:
                    h = _hash(stream)
                    candidate = matches[extinf].setdefault(h, {"url": stream,
                                                                "proof_commits": []})
                    candidate["proof_commits"].append(revision)
        except (OSError, ValueError, TypeError):
            failures += 1
    return matches, {"revisions_listed": len(revisions), "historical_files_read": files_read,
                     "historical_files_unavailable": failures}


def find_official_alternates(orphan_rows, *, reader=_read_document):
    wanted = {row["extinf"] for row in orphan_rows}
    matches = defaultdict(dict)
    states = []
    for source in ONUR_ALTERNATES:
        try:
            rows, _ = parse_exact_pairs(reader(source))
            for extinf in wanted & rows.keys():
                for url in rows[extinf]:
                    matches[extinf].setdefault(_hash(url), {"url": url,
                                                             "proof_official_feed": source})
            states.append("READ")
        except (OSError, ValueError, TypeError):
            states.append("UNAVAILABLE")
    return matches, {"official_alternate_feeds_read": states.count("READ"),
                     "official_alternate_feeds_unavailable": states.count("UNAVAILABLE")}


def evaluate(sources, *, probe=probe_one):
    """Use deduped URL candidates, report only anonymous evidence."""
    mapping = defaultdict(list)
    urls = {}
    for item in sources:
        for evidence in item["candidates"].values():
            url = evidence["url"]
            digest = _hash(url)
            urls[digest] = url
            mapping[digest].append(item)
    if len(urls) > MAX_CANDIDATE_STREAMS:
        raise ValueError("Too many historical streams for bounded validation")
    with ThreadPoolExecutor(max_workers=4) as pool:
        probed = list(pool.map(probe, sorted(urls.items())))
    verified = {z["url_sha256"] for z in probed
                if z["status"] == "VIDEO_STREAM_OBSERVED"
                and z.get("video_stream") and z.get("audio_stream")}
    rows = []
    for sha in sorted(verified):
        owners = mapping[sha]
        rows.append({"url": urls[sha], "url_sha256": sha,
                     "source_id": owners[0]["source_id"],
                     "orphan_extinf_sha256": owners[0]["extinf_sha256"],
                     "extinf": owners[0]["extinf"]})
    return probed, rows, mapping


def audit(*, report_path, sealed_path, key_path, limit=20,
          reader=_read_document, commits=historical_revisions, probe=probe_one):
    sources = []
    source_summaries = []
    source_evidence = []
    historic_errors = 0
    for ident, repo, path in ORIGINALS:
        upstream = "https://raw.githubusercontent.com/" + repo + "/main/" + quote(path)
        current = reader(upstream)
        _, orphans = parse_exact_pairs(current)
        orphans = [o for o in orphans if o["reason"] !=
                   "EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER"]
        old, status = find_historical(orphans, repo, path,
                                      limit=limit, reader=reader, commits=commits)
        historic_errors += status["historical_files_unavailable"]
        source_summaries.append({"source_id": ident, "orphan_count": len(orphans),
                                  "original_document_sha256": _hash(current),
                                  **status})
        for item in orphans:
            candidates = old.get(item["extinf"], {})
            sources.append({"source_id": ident, "extinf_sha256": item["extinf_sha256"],
                            "extinf": item["extinf"], "reason": item["reason"],
                            "line_number": item["line_number"],
                            "candidates": candidates})
    current = reader(ONUR[1])
    _, orphans = parse_exact_pairs(current)
    orphans = [o for o in orphans
               if o["reason"] != "EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER"]
    alts, alt_status = find_official_alternates(orphans, reader=reader)
    source_summaries.append({"source_id": ONUR[0], "orphan_count": len(orphans),
                             "original_document_sha256": _hash(current), **alt_status})
    for item in orphans:
        sources.append({"source_id": ONUR[0], "extinf_sha256": item["extinf_sha256"],
                        "extinf": item["extinf"], "reason": item["reason"],
                        "line_number": item["line_number"],
                        "candidates": alts.get(item["extinf"], {})})
    probed, verified_rows, mapping = evaluate(sources, probe=probe)
    proof_states = {p["url_sha256"]: p for p in probed}
    for item in sources:
        candidate_evidence = []
        for sha, record in sorted(item["candidates"].items()):
            p = proof_states[sha]
            candidate_evidence.append({"url_sha256": sha,
                                       "video_stream": bool(p.get("video_stream")),
                                       "audio_stream": bool(p.get("audio_stream")),
                                       "status": p["status"],
                                       "diagnostic_category": p.get("diagnostic_category"),
                                       "proof_commits": record.get("proof_commits", []),
                                       "publisher_official_alternate":
                                           bool(record.get("proof_official_feed"))})
        source_evidence.append({
            "source_id": item["source_id"], "line_number": item["line_number"],
            "extinf_sha256": item["extinf_sha256"], "reason": item["reason"],
            "historical_or_official_candidates": len(candidate_evidence),
            "verified_av_candidates": sum(x["video_stream"] and x["audio_stream"]
                                          for x in candidate_evidence),
            "candidates": candidate_evidence})
    result = {
        "schema": 1, "kind": "THREE_UPSTREAM_ORPHAN_REPAIR_EVIDENCE_NOT_IBO",
        "status": "SOURCE_REPAIR_CANDIDATES_VERIFIED" if verified_rows
                  else "NO_CURRENT_AV_VERIFIED_REPLACEMENTS",
        "upstream_sources": source_summaries,
        "orphan_entries": len(sources),
        "unique_candidate_urls_historically_or_officially_proven": len(probed),
        "unique_candidates_video_audio_verified": len(verified_rows),
        "orphan_entries_with_current_av": sum(
            any(p["video_stream"] and p["audio_stream"] for p in x["candidates"])
            for x in source_evidence),
        "orphan_entries_without_current_av": sum(
            not any(p["video_stream"] and p["audio_stream"] for p in x["candidates"])
            for x in source_evidence),
        "unavailable_historical_git_files": historic_errors,
        "records": source_evidence,
        "plain_stream_urls_reported": False, "protected_playlist_modified": False,
        "ibo_device_verified": False, "scan_scope": "ONLY_THREE_PREVIOUSLY_FLAGGED_M3U_SOURCES",
    }
    if verified_rows:
        seal_rows(verified_rows, key_path, sealed_path)
        result["sealed_successful_av_stream_count"] = len(verified_rows)
    else:
        result["sealed_successful_av_stream_count"] = 0
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, ensure_ascii=False, sort_keys=True)
        out.write("\n")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--sealed", type=Path, required=True)
    p.add_argument("--public-key", type=Path,
                   default=Path("v2/config/stage3_transit_public.pem"))
    p.add_argument("--history-revisions", type=int, default=20)
    args = p.parse_args()
    if (args.report.exists() or args.report.is_symlink()
            or args.sealed.exists() or args.sealed.is_symlink()
            or args.report.resolve() == args.sealed.resolve()
            or not 1 <= args.history_revisions <= 35):
        p.error("Unsafe output path or unbounded history")
    result = audit(report_path=args.report, sealed_path=args.sealed,
                   key_path=args.public_key, limit=args.history_revisions)
    print("Three source orphan metadata cases:", result["orphan_entries"],
          "exact historic/official candidate URL hashes:",
          result["unique_candidate_urls_historically_or_officially_proven"],
          "currently video+audio verified:",
          result["unique_candidates_video_audio_verified"],
          "orphan entries with no current verified replacement:",
          result["orphan_entries_without_current_av"])


if __name__ == "__main__":
    main()

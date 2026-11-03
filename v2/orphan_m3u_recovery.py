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
from urllib.parse import quote, urlencode, urlsplit

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
MAX_CANDIDATE_STREAMS = 256


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


def is_nonpublic_absolute_http_reference(value):
    if not value.startswith(("http://", "https://")):
        return False
    try:
        return bool(urlsplit(value).hostname) and not validate_url(value)
    except ValueError:
        return False


def classify_invalid_uri_structure(value):
    if value is None:
        return "NO_URI_PROVIDED"
    if value.startswith(("http://", "https://")):
        try:
            u = urlsplit(value)
            return "HTTP_URI_WITHOUT_HOST" if not u.hostname else (
                "HTTP_URI_REJECTED_BY_SAFETY_POLICY")
        except ValueError:
            return "MALFORMED_HTTP_URI"
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value):
        return "NON_HTTP_PROTOCOL_REFERENCE"
    return "RELATIVE_OR_UNRECOGNIZED_URI"


def parse_exact_pairs(payload):
    """Return exact metadata-keyed orphan lines and valid URL candidates."""
    if not isinstance(payload, str):
        raise TypeError("M3U document must be text")
    rows = defaultdict(set)
    orphan = []
    pending = None

    def orphaned(reason, previous, bad_reference=None):
        n, extinf = previous
        orphan.append({"line_number": n, "extinf_sha256": _hash(extinf),
                       "extinf": extinf, "reason": reason,
                       "uri_structure": classify_invalid_uri_structure(bad_reference)})

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
                orphaned("EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER", pending, line)
            elif is_nonpublic_absolute_http_reference(line):
                # Present absolute HTTP URI rejected by our public-network safety
                # rules: not a *missing* EXTINF pair and never a probe candidate.
                pass
            else:
                orphaned("INVALID_OR_RELATIVE_STREAM_REFERENCE", pending, line)
            pending = None
    if pending:
        orphaned("TRAILING_EXTINF_WITHOUT_URI", pending)
    return rows, orphan


def count_excluded_network_references(payload):
    """Count nonpublic/credentialed HTTP media locations without exposing them."""
    pending = False
    count = 0
    for raw in payload.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            pending = True
        elif line and not line.startswith("#") and pending:
            if is_nonpublic_absolute_http_reference(line):
                count += 1
            pending = False
    return count


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


def exact_channel_identity(extinf):
    """Only exact case-folded tvg-id PLUS channel display-name evidence.

    Reject missing IDs and names; never use name-only or fuzzy similarity.
    """
    m = re.search(r'\btvg-id="([^"]+)"', extinf, flags=re.IGNORECASE)
    if not m or not m.group(1).strip():
        return None
    quoted, name_at = False, -1
    for i, c in enumerate(extinf):
        if c == '"':
            quoted = not quoted
        elif c == "," and not quoted:
            name_at = i
            break
    name = extinf[name_at + 1:].strip() if name_at >= 0 else ""
    if not name:
        return None
    return (m.group(1).strip().casefold(), " ".join(name.casefold().split()))


def existing_source_catalog():
    """Only 46 enabled configured sources and 17 original #60 feeds."""
    from discover import load_original_run60_sources
    root = Path(__file__).resolve().parent
    cfg = json.loads((root / "config/sources.json").read_text(encoding="utf-8"))
    originals = load_original_run60_sources(
        root / "history/run60-dynamic-source-ledger.json")
    active = [x for x in cfg["sources"] if x.get("enabled", True) is not False]
    all_sources = active + originals
    if (len(active) != 46 or len(originals) != 17
            or len({x["id"] for x in all_sources}) != 63):
        raise ValueError("Original 63-source catalog coverage differs")
    return all_sources


def find_existing_exact_identity(orphans, catalog, *, reader=_read_document):
    """Only metadata-equivalent alternatives from already-known sources.

    No new provider searches; a same EPG ID and exact name is a candidate,
    NEVER proof of actual channel content or suitability for the IBO device.
    """
    wanted = defaultdict(list)
    for item in orphans:
        identity = exact_channel_identity(item["extinf"])
        if identity is not None:
            wanted[identity].append(item["extinf_sha256"])

    def one(source):
        try:
            data = reader(source["url"])
            pairs, _ = parse_exact_pairs(data)
            found = []
            for extinf, urls in pairs.items():
                for dst in wanted.get(exact_channel_identity(extinf), []):
                    for url in urls:
                        found.append((dst, _hash(url), url, source["id"]))
            return found, None
        except (OSError, ValueError, TypeError):
            return [], "SOURCE_DOCUMENT_UNAVAILABLE_OR_INVALID"

    matched = defaultdict(dict)
    failures = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for source, result in zip(catalog, pool.map(one, catalog)):
            found, error = result
            if error:
                failures.append(source["id"])
            for extinf_sha, url_sha, url, source_id in found:
                cand = matched[extinf_sha].setdefault(
                    url_sha, {"url": url, "proof_existing_source_ids": []})
                if source_id not in cand["proof_existing_source_ids"]:
                    cand["proof_existing_source_ids"].append(source_id)
    for values in matched.values():
        for item in values.values():
            item["proof_existing_source_ids"].sort()
    return matched, {
        "preconfigured_sources_checked": len(catalog),
        "source_documents_unavailable_count": len(failures),
        "unavailable_source_ids": sorted(failures),
        "orphan_entries_with_exact_existing_epg_and_name": len(matched),
        "proof_only": "MATCHED_EPG_ID_AND_EXACT_CHANNEL_NAME_NOT_CHANNEL_CONTENT",
    }


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
          reader=_read_document, commits=historical_revisions, probe=probe_one,
          known_source_catalog=None):
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
                                  "excluded_nonpublic_http_references":
                                      count_excluded_network_references(current),
                                  "original_document_sha256": _hash(current),
                                  **status})
        for item in orphans:
            candidates = old.get(item["extinf"], {})
            sources.append({"source_id": ident, "extinf_sha256": item["extinf_sha256"],
                            "extinf": item["extinf"], "reason": item["reason"],
                            "line_number": item["line_number"],
                            "uri_structure": item["uri_structure"],
                            "candidates": candidates})
    current = reader(ONUR[1])
    _, orphans = parse_exact_pairs(current)
    orphans = [o for o in orphans
               if o["reason"] != "EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER"]
    alts, alt_status = find_official_alternates(orphans, reader=reader)
    source_summaries.append({"source_id": ONUR[0], "orphan_count": len(orphans),
                             "excluded_nonpublic_http_references":
                                 count_excluded_network_references(current),
                             "original_document_sha256": _hash(current), **alt_status})
    for item in orphans:
        sources.append({"source_id": ONUR[0], "extinf_sha256": item["extinf_sha256"],
                        "extinf": item["extinf"], "reason": item["reason"],
                        "line_number": item["line_number"],
                        "uri_structure": item["uri_structure"],
                        "candidates": alts.get(item["extinf"], {})})
    existing_report = None
    if known_source_catalog is not None:
        existing, existing_report = find_existing_exact_identity(
            sources, known_source_catalog, reader=reader)
        for item in sources:
            for urlsha, candidate in existing.get(item["extinf_sha256"], {}).items():
                record = item["candidates"].setdefault(urlsha, {"url": candidate["url"]})
                ids = set(record.get("proof_existing_source_ids", []))
                ids.update(candidate["proof_existing_source_ids"])
                record["proof_existing_source_ids"] = sorted(ids)
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
                                           bool(record.get("proof_official_feed")),
                                       "exact_epg_and_name_other_source":
                                           record.get("proof_existing_source_ids", [])})
        source_evidence.append({
            "source_id": item["source_id"], "line_number": item["line_number"],
            "extinf_sha256": item["extinf_sha256"], "reason": item["reason"],
            "uri_structure": item["uri_structure"],
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
        "orphan_uri_structure_counts": dict(sorted(Counter(
            item["uri_structure"] for item in sources).items())),
        "unique_candidate_urls_historically_or_officially_proven": len(probed),
        "unique_candidates_video_audio_verified": len(verified_rows),
        "orphan_entries_with_current_av": sum(
            any(p["video_stream"] and p["audio_stream"] for p in x["candidates"])
            for x in source_evidence),
        "orphan_entries_without_current_av": sum(
            not any(p["video_stream"] and p["audio_stream"] for p in x["candidates"])
            for x in source_evidence),
        "unavailable_historical_git_files": historic_errors,
        "existing_catalog_reconciliation": existing_report,
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
                   key_path=args.public_key, limit=args.history_revisions,
                   known_source_catalog=existing_source_catalog())
    print("Three source orphan metadata cases:", result["orphan_entries"],
          "exact historic/official candidate URL hashes:",
          result["unique_candidate_urls_historically_or_officially_proven"],
          "currently video+audio verified:",
          result["unique_candidates_video_audio_verified"],
          "orphan entries with no current verified replacement:",
          result["orphan_entries_without_current_av"],
          "existing source catalog checked:",
          result.get("existing_catalog_reconciliation", {}).get(
              "preconfigured_sources_checked"))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Repair evidence for orphan entries in four known M3U source documents.

This job never modifies upstream feeds or the protected IBO playlist. Exact
#EXTINF matches from historical Git commits / the publisher's official
alternate feeds are candidate URL evidence; real FFmpeg video+audio decoding
is required before a candidate is called playable. Plaintext stream URLs are held only in memory
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
from final_batch_acceptance import probe as ffmpeg_probe
from orphan_strong_av_probe import extended_probe
from stage3_sealed_export import seal_rows

ORIGINALS = (
    ("discevisita-tr", "discevisita/iptv", "tr.m3u"),
    ("github-auto-24", "Hannstcott/SunshineTr", "sunshinetv.m3u"),
)
ONUR_SOURCES = (
    ("onureroz-turk-karma", "https://onureroz.com/indirmeler/turk/karma-index.m3u"),
    ("onureroz-turk-all", "https://onureroz.com/indirmeler/turk/all.m3u"),
)
ONUR_ALTERNATES = (
    "https://onureroz.com/indirmeler/turk/index.m3u",
    "https://onureroz.com/indirmeler/turk/all.m3u",
    # Publicly listed by the same publisher; exact EXTINF / EPG+name only.
    "https://onureroz.com/indirmeler/dunya/index.m3u",
)
MAX_FILE_BYTES = 32_000_000
MAX_CANDIDATE_STREAMS = 800


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
    """Read a bounded number of real Git revisions, including older pages."""
    if (repo, path) not in {(r, p) for _, r, p in ORIGINALS}:
        raise ValueError("Historical source outside pinned scope")
    if type(limit) is not int or not 1 <= limit <= 300:
        raise ValueError("Historical revision limit out of bounds")
    owner, name = repo.split("/")
    shas, seen = [], set()
    while len(shas) < limit:
        page = len(shas) // 100 + 1
        query = urlencode({"path": path, "per_page": "100", "page": str(page)})
        url = ("https://api.github.com/repos/" + quote(owner) + "/" + quote(name)
               + "/commits?" + query)
        data = json.loads(_read(url, api=True))
        if not isinstance(data, list):
            raise ValueError("GitHub history is not a list")
        if len(data) > 100:
            raise ValueError("GitHub history page exceeded 100 results")
        for entry in data:
            sha = entry.get("sha") if isinstance(entry, dict) else None
            if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha):
                raise ValueError("Untrusted historical Git revision")
            if sha in seen:
                raise ValueError("Duplicate historical revision across pages")
            seen.add(sha)
            shas.append(sha)
        if len(data) < 100:
            break
    return shas[:limit]


def find_historical(orphan_rows, repo, path, *, limit=20,
                    commits=historical_revisions, reader=_read_document):
    if (repo, path) not in {(r, p) for _, r, p in ORIGINALS}:
        raise ValueError("Historical source outside pinned scope")
    wanted = {o["extinf"] for o in orphan_rows}
    by_identity = defaultdict(set)
    by_logo_group = defaultdict(set)
    by_reviewed_alias = defaultdict(set)
    for extinf in wanted:
        identity = exact_channel_identity(extinf)
        if identity is not None:
            by_identity[identity].add(extinf)
        strict = exact_no_epg_logo_group_name(extinf)
        if strict is not None:
            by_logo_group[strict].add(extinf)
        alias = reviewed_hanoicab3_identity(extinf)
        if alias is not None:
            by_reviewed_alias[alias].add(extinf)

    matches = defaultdict(dict)
    files_read = 0
    failures = 0
    revisions = commits(repo, path, limit=limit)
    def fetch_revision(revision):
        url = ("https://raw.githubusercontent.com/" + repo + "/" + revision
               + "/" + quote(path, safe="/"))
        try:
            rows, _ = parse_exact_pairs(reader(url))
            return revision, rows, False
        except (OSError, ValueError, TypeError):
            return revision, {}, True

    # Bounded concurrency preserves revision order and avoids 300 sequential
    # HTTP requests. No media/stream URL is fetched in this archive pass.
    with ThreadPoolExecutor(max_workers=8) as pool:
        for revision, rows, failed in pool.map(fetch_revision, revisions):
            if failed:
                failures += 1
                continue
            files_read += 1
            for historical_extinf, streams in rows.items():
                destinations = {}
                if historical_extinf in wanted:
                    destinations[historical_extinf] = "EXACT_EXTINF"
                historical_identity = exact_channel_identity(historical_extinf)
                if historical_identity is not None:
                    for current_extinf in by_identity.get(historical_identity, ()):
                        destinations.setdefault(current_extinf, "EXACT_EPG_ID_AND_NAME")
                logo_identity = exact_no_epg_logo_group_name(historical_extinf)
                if logo_identity is not None:
                    for current_extinf in by_logo_group.get(logo_identity, ()):
                        destinations.setdefault(current_extinf, "EXACT_NO_EPG_LOGO_GROUP_NAME")
                reviewed = reviewed_hanoicab3_identity(historical_extinf)
                if reviewed is not None:
                    for current_extinf in by_reviewed_alias.get(reviewed, ()):
                        destinations.setdefault(current_extinf, "REVIEWED_ANTG_NAME_ALIAS")
                for target_extinf, rule in destinations.items():
                    for stream in streams:
                        h = _hash(stream)
                        candidate = matches[target_extinf].setdefault(
                            h, {"url": stream, "proof_commits": [], "proof_rules": []})
                        if revision not in candidate["proof_commits"]:
                            candidate["proof_commits"].append(revision)
                        if rule not in candidate["proof_rules"]:
                            candidate["proof_rules"].append(rule)
    return matches, {"revisions_listed": len(revisions), "historical_files_read": files_read,
                     "historical_files_unavailable": failures,
                     "metadata_identity_match_rule":
                         "EXACT_EXTINF_OR_EXACT_EPG_ID_AND_CHANNEL_NAME"}



def find_official_alternates(orphan_rows, *, reader=_read_document):
    """Publisher URLs must match exact EXTINF or exact EPG ID AND channel name."""
    wanted = {row["extinf"] for row in orphan_rows}
    identities = defaultdict(set)
    by_logo_group = defaultdict(set)
    by_reviewed_alias = defaultdict(set)
    for extinf in wanted:
        identity = exact_channel_identity(extinf)
        if identity is not None:
            identities[identity].add(extinf)
        strict = exact_no_epg_logo_group_name(extinf)
        if strict is not None:
            by_logo_group[strict].add(extinf)
        alias = reviewed_hanoicab3_identity(extinf)
        if alias is not None:
            by_reviewed_alias[alias].add(extinf)
    matches = defaultdict(dict)
    states = []
    for source in ONUR_ALTERNATES:
        try:
            rows, _ = parse_exact_pairs(reader(source))
            for extinf, urls in rows.items():
                destinations = {extinf: "EXACT_EXTINF"} if extinf in wanted else {}
                for dst in identities.get(exact_channel_identity(extinf), []):
                    destinations.setdefault(dst, "EXACT_EPG_ID_AND_NAME_OFFICIAL_ALTERNATE")
                logo_identity = exact_no_epg_logo_group_name(extinf)
                if logo_identity is not None:
                    for dst in by_logo_group.get(logo_identity, ()):
                        destinations.setdefault(dst, "EXACT_NO_EPG_LOGO_GROUP_NAME_OFFICIAL_ALTERNATE")
                reviewed = reviewed_hanoicab3_identity(extinf)
                if reviewed is not None:
                    for dst in by_reviewed_alias.get(reviewed, ()):
                        destinations.setdefault(dst, "REVIEWED_ANTG_NAME_ALIAS_OFFICIAL_ALTERNATE")
                for dst, rule in destinations.items():
                    for url in urls:
                        proof = matches[dst].setdefault(
                            _hash(url), {"url": url, "proof_official_feed": source,
                                         "proof_rules": []})
                        if rule not in proof["proof_rules"]:
                            proof["proof_rules"].append(rule)
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
    # Some genuine upstream M3U records have malformed EXTINF punctuation:
    #   #EXTINF:-1, tvg-id="vtc12hd" ...,VTC12
    # and one Hanoicab3 record has an unfinished trailing group-title quote.
    # Correct ONLY these bounded, syntactically identifiable defects.
    # Preserve the original EXTINF bytes/hash and never infer a media URL.
    quoted = False
    separators = []
    for i, c in enumerate(extinf):
        if c == '"':
            quoted = not quoted
        elif c == "," and not quoted:
            separators.append(i)
    if (re.match(r'^#EXTINF:-1,\s*tvg-id="', extinf, flags=re.I)
            and len(separators) >= 2):
        name = extinf[separators[1] + 1:].strip()
    elif separators:
        name = extinf[separators[0] + 1:].strip()
    else:
        unclosed = (extinf.count('"') % 2 == 1)
        recover = re.search(
            r'\bgroup-title="\s*,([^,\r\n"]+)\Z', extinf, flags=re.I)
        name = recover.group(1).strip() if unclosed and recover else ""
    if not name:
        return None
    return (m.group(1).strip().casefold(), " ".join(name.casefold().split()))





def reviewed_hanoicab3_identity(extinf):
    """Explicit Hanoicab 3 / An Ninh The Gioi alias with the SAME EPG ID.

    This independently documented historical channel name is NOT a fuzzy
    string rule. Only these two exact spellings and 'antg' are accepted;
    a resulting URL still has no playback evidence until FFprobe checks it.
    """
    ident = exact_channel_identity(extinf)
    if ident is None or ident[0] != "antg":
        return None
    if ident[1] not in ("hanoicab 3 | an ninh thế giới", "an ninh thế giới"):
        return None
    return ("antg", "an ninh thế giới")


def exact_no_epg_logo_group_name(extinf):
    """Secondary strict identity: no EPG ID, exact name + group + logo.

    A logo alone or an unverified name is never enough. This only discovers
    real alternate URLs, whose audio/video must still be separately probed.
    Channels with a populated tvg-id cannot fall back to the weaker rule.
    """
    if not isinstance(extinf, str) or not extinf.startswith("#EXTINF:"):
        return None
    epg = re.search(r'\btvg-id="([^"]*)"', extinf, flags=re.IGNORECASE)
    if epg and epg.group(1).strip():
        return None
    group = re.search(r'\bgroup-title="([^"]+)"', extinf, flags=re.IGNORECASE)
    logo = re.search(r'\btvg-logo="([^"]+)"', extinf, flags=re.IGNORECASE)
    if not group or not logo:
        return None
    group_value = " ".join(group.group(1).casefold().split())
    logo_value = logo.group(1).strip()
    if not group_value or not logo_value.startswith(("https://", "http://")):
        return None
    in_quotes = False
    name_position = -1
    for i, char in enumerate(extinf):
        if char == '"':
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            name_position = i
            break
    if name_position < 0:
        return None
    name = " ".join(extinf[name_position + 1:].casefold().split())
    if not name:
        return None
    return (group_value, logo_value, name)


def restore_exact_original_metadata_from_official_alternates(
        source_id, baseline, *, reader):
    """Rebuild only published, exact SHA-256 EXTINF metadata when an original
    publisher feed is unavailable. NEVER reconstruct a URL or assert that the
    original upstream URI is active. The actual alternate URLs are separately
    collected and FFprobed via find_official_alternates.
    """
    expected = set(baseline["sources"][source_id])
    observed = {}
    for official_url in ONUR_ALTERNATES:
        try:
            document = reader(official_url)
        except (OSError, TypeError, ValueError):
            continue
        for raw in document.splitlines():
            extinf = raw.strip()
            if not extinf.startswith("#EXTINF:"):
                continue
            digest = _hash(extinf)
            if digest in expected:
                observed.setdefault(digest, extinf)
    missing = expected - set(observed)
    if missing:
        raise ValueError(
            "ORIGINAL_PUBLISHER_M3U_UNAVAILABLE_AND_EXACT_METADATA_NOT_RECOVERED:"
            + source_id + ":" + str(len(missing)))
    # These bare EXTINF lines are real publisher metadata, not invented
    # addresses; the subsequent candidate search must retrieve real URLs.
    return "#EXTM3U\n" + "\n".join(observed[h] for h in sorted(expected)) + "\n"

def existing_source_catalog():
    """The immutable 63 known sources plus vetted public-document M3U sources.

    Only sources whose M3U channel pairs were verified enter this catalog;
    original source IDs and the 46+17 historical counts are never reduced.
    """
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
    from document_platform_discovery import accepted_sources
    known_urls = {item["url"] for item in all_sources}
    known_ids = {item["id"] for item in all_sources}
    for item in accepted_sources():
        if item["url"] in known_urls:
            continue
        if item["id"] in known_ids:
            raise ValueError("Document source identity conflicts with original ledger")
        all_sources.append(item)
        known_urls.add(item["url"])
        known_ids.add(item["id"])
    # Two separately pinned third-party TR/AZ candidate-only references.
    # Preserve the 46 fixed and 17 historical base identities unchanged.
    from orphan_curated_traz_sources import pinned_traz_candidate_references
    all_sources.extend(pinned_traz_candidate_references(known_urls, known_ids))
    return all_sources


def find_existing_exact_identity(orphans, catalog, *, reader=_read_document,
                                 doc_reader=None, doc_resolver=None):
    """Exact original EXTINF or EPG ID + channel-name recovery from reviewed sources.

    An unchanged original EXTINF line is a stronger identity than an inferred
    name, including when tvg-id is absent. No fuzzy/name-only matches allowed.
    Public-document sources must also pass URL and public DNS checks before
    the distinct safe, redirect-validated document fetcher is invoked. Matching
    alone never proves channel content, actual playback or device compatibility.
    """
    wanted = defaultdict(list)
    by_logo_group = defaultdict(list)
    by_reviewed_alias = defaultdict(list)
    exact_originals = defaultdict(list)
    for item in orphans:
        extinf, digest = item["extinf"], item["extinf_sha256"]
        if _hash(extinf) != digest:
            raise ValueError("Orphan EXTINF identity hash mismatch")
        exact_originals[extinf].append(digest)
        identity = exact_channel_identity(extinf)
        if identity is not None:
            wanted[identity].append(digest)
        strict = exact_no_epg_logo_group_name(extinf)
        if strict is not None:
            by_logo_group[strict].append(digest)
        alias = reviewed_hanoicab3_identity(extinf)
        if alias is not None:
            by_reviewed_alias[alias].append(digest)

    def one(source):
        try:
            if source.get("origin") == "v2-main-protected-playlist":
                from main_playlist_candidate_bridge import read_verified_snapshot
                data = read_verified_snapshot(source)
            elif source.get("origin") == "orphan-discovery-reference":
                from orphan_source_expansion import safe_reference_url
                from historical_targeted_playback import public_dns
                from discover import fetch
                if not safe_reference_url(source["url"]) or not public_dns(source["url"]):
                    raise ValueError("Unsafe public orphan discovery reference")
                data = fetch(source["url"])
                if not data.lstrip("\ufeff\r\n\t ").startswith("#EXTM3U"):
                    raise ValueError("Public orphan source missing M3U header")
            elif source.get("origin") == "public-document-reference":
                from document_platform_discovery import source_url
                from discover import fetch
                from historical_targeted_playback import public_dns
                resolver = public_dns if doc_resolver is None else doc_resolver
                if not source_url(source["url"]) or not resolver(source["url"]):
                    raise ValueError("Unsafe public document source")
                source_reader = fetch if doc_reader is None else doc_reader
                data = source_reader(source["url"])
                if not data.lstrip().startswith("#EXTM3U"):
                    raise ValueError("Public document is not an M3U feed")
            else:
                data = reader(source["url"])
            pairs, _ = parse_exact_pairs(data)
            found = []
            for extinf, urls in pairs.items():
                targets = {dst: "EXACT_ORIGINAL_EXTINF"
                           for dst in exact_originals.get(extinf, ())}
                for dst in wanted.get(exact_channel_identity(extinf), ()):
                    targets.setdefault(dst, "EXACT_EPG_ID_AND_CHANNEL_NAME")
                logo_identity = exact_no_epg_logo_group_name(extinf)
                if logo_identity is not None:
                    for dst in by_logo_group.get(logo_identity, ()):
                        targets.setdefault(dst, "EXACT_NO_EPG_LOGO_GROUP_NAME")
                reviewed = reviewed_hanoicab3_identity(extinf)
                if reviewed is not None:
                    for dst in by_reviewed_alias.get(reviewed, ()):
                        targets.setdefault(dst, "REVIEWED_ANTG_NAME_ALIAS")
                for dst, proof_rule in targets.items():
                    for url in urls:
                        found.append((dst, _hash(url), url, source["id"], proof_rule))
            return found, None
        except (OSError, ValueError, TypeError):
            return [], "SOURCE_DOCUMENT_UNAVAILABLE_OR_INVALID"

    matched = defaultdict(dict)
    proof_identity_groups = defaultdict(set)
    failures = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for source, result in zip(catalog, pool.map(one, catalog)):
            found, error = result
            if error:
                failures.append(source["id"])
            for extinf_sha, url_sha, url, source_id, proof_rule in found:
                proof_identity_groups[proof_rule].add(extinf_sha)
                cand = matched[extinf_sha].setdefault(
                    url_sha, {"url": url, "proof_existing_source_ids": [],
                              "proof_rules": []})
                if source_id not in cand["proof_existing_source_ids"]:
                    cand["proof_existing_source_ids"].append(source_id)
                if proof_rule not in cand["proof_rules"]:
                    cand["proof_rules"].append(proof_rule)
    for values in matched.values():
        for item in values.values():
            item["proof_existing_source_ids"].sort()
            item["proof_rules"].sort()
    return matched, {
        "preconfigured_sources_checked": len(catalog),
        "vetted_public_document_sources_checked": sum(
            source.get("origin") == "public-document-reference" for source in catalog),
        "public_discovery_source_references_checked": sum(
            source.get("origin") == "orphan-discovery-reference" for source in catalog),
        "source_documents_unavailable_count": len(failures),
        "unavailable_source_ids": sorted(failures),
        "orphan_entries_with_exact_existing_epg_and_name": len(
            proof_identity_groups["EXACT_EPG_ID_AND_CHANNEL_NAME"] |
            proof_identity_groups["EXACT_ORIGINAL_EXTINF"] & {
                x["extinf_sha256"] for x in orphans if exact_channel_identity(x["extinf"]) is not None}),
        "orphan_entries_with_exact_original_extinf": len(
            proof_identity_groups["EXACT_ORIGINAL_EXTINF"]),
        "orphan_entries_with_exact_no_epg_logo_group_name": len(
            proof_identity_groups["EXACT_NO_EPG_LOGO_GROUP_NAME"]),
        "orphan_entries_with_reviewed_hanoicab_name_alias": len(
            proof_identity_groups["REVIEWED_ANTG_NAME_ALIAS"]),
        "orphan_entries_with_any_exact_existing_match": len(matched),
        "proof_only": "EXACT_EXTINF_OR_EPG_NAME_OR_NO_EPG_LOGO_GROUP_OR_REVIEWED_ANTG_ALIAS_NOT_AV",
    }


def probe_real_av(pair):
    """Validate actual FFprobe and one-second FFmpeg video+audio decode."""
    result = ffmpeg_probe(pair)
    if (not isinstance(result, dict) or result.get("url_sha256") != pair[0]
            or any(type(result.get(field)) is not bool
                   for field in ("video", "audio", "decoded"))):
        raise ValueError("Invalid real FFmpeg evidence")
    status = result.get("status")
    if not isinstance(status, str) or not re.fullmatch(r"[A-Z_]{2,100}", status):
        raise ValueError("Unapproved media status")
    # Second, wider FFprobe+FFmpeg decoding only after ambiguous media proof.
    # 401/403/404, unsafe hosts, and already decoded streams are never retried.
    result = extended_probe(pair, result)
    status = result["status"]
    decoded = result["decoded"]
    if (decoded and (not result["video"] or not result["audio"]
                     or status != "VIDEO_AUDIO_DECODED")
            or status == "VIDEO_AUDIO_DECODED" and not decoded):
        raise ValueError("False FFmpeg video+audio proof")
    return {"url_sha256": pair[0], "status": status,
            "video_stream": result["video"], "audio_stream": result["audio"],
            "ffmpeg_video_audio_decoded": decoded,
            "diagnostic_category": None if decoded else status}


def evaluate(sources, *, probe=probe_real_av):
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
    with ThreadPoolExecutor(max_workers=8) as pool:
        probed = list(pool.map(probe, sorted(urls.items())))
    if (len(probed) != len(urls) or
            {z.get("url_sha256") for z in probed} != set(urls)):
        raise ValueError("Incomplete candidate SHA playback coverage")
    for evidence in probed:
        status = evidence.get("status")
        decoded = evidence.get("ffmpeg_video_audio_decoded", False)
        if (not isinstance(status, str)
                or not re.fullmatch(r"[A-Z_]{2,100}", status)
                or type(decoded) is not bool
                or decoded and (status != "VIDEO_AUDIO_DECODED"
                                or evidence.get("video_stream") is not True
                                or evidence.get("audio_stream") is not True)
                or status == "VIDEO_AUDIO_DECODED" and not decoded):
            raise ValueError("Unproven or inconsistent FFmpeg decoder evidence")
    verified = {z["url_sha256"] for z in probed
                if z.get("ffmpeg_video_audio_decoded") is True}
    rows = []
    for sha in sorted(verified):
        owners = mapping[sha]
        rows.append({"url": urls[sha], "url_sha256": sha,
                     "source_id": owners[0]["source_id"],
                     "orphan_extinf_sha256": owners[0]["extinf_sha256"],
                     "extinf": owners[0]["extinf"]})
    return probed, rows, mapping



def candidate_repairs_from_current_verified_sources(baseline, source_documents):
    """Return true original SHA-matched URI repairs, never guessed channel URLs.

    If the publisher adds a valid URI beneath an original EXTINF record, the
    channel's immutable SHA already proves the metadata came from that source.
    These candidate URLs still require guarded FFprobe A/V checks before being
    marked video/audio verified or considered for a separate user device test.
    """
    repairs = []
    for source_id, original_hashes in baseline["sources"].items():
        wanted = set(original_hashes)
        text = source_documents[source_id]
        pairs, _ = parse_exact_pairs(text)
        for extinf, urls in pairs.items():
            digest = _hash(extinf)
            if digest not in wanted:
                continue
            candidates = {
                _hash(url): {
                    "url": url,
                    "proof_rules": ["EXACT_ORIGINAL_EXTINF_NOW_HAS_URI"],
                    "proof_existing_source_ids": [source_id],
                    "proof_original_upstream_now_has_uri": True,
                }
                for url in urls if validate_url(url)
            }
            if candidates:
                repairs.append({
                    "source_id": source_id, "extinf_sha256": digest,
                    "extinf": extinf, "reason": "UPSTREAM_ORIGINAL_URI_RESTORED",
                    "line_number": None, "uri_structure": "PUBLIC_ABSOLUTE_HTTP_URI",
                    "candidates": candidates,
                })
    return repairs


def sealed_retest_candidate_rows(sources, proof_states):
    """Retain all exact-proven historical URLs, even if today's A/V probe failed.

    Returned plaintext must only go into seal_rows; public reports contain
    counts, URL SHA256 and status categories, never stream URLs.
    """
    index = {}
    for source in sources:
        for digest, candidate in source["candidates"].items():
            url = candidate["url"]
            if _hash(url) != digest or not validate_url(url):
                raise ValueError("Invalid historical candidate identity")
            existing = index.get(digest)
            if existing is None:
                existing = {"url": url, "url_sha256": digest,
                            "source_ids": set(), "orphan_extinf_sha256": set(),
                            "proof_commits": set(), "proof_rules": set(),
                            "proof_existing_source_ids": set()}
                index[digest] = existing
            if existing["url"] != url:
                raise ValueError("Contradictory candidate URL for same SHA256")
            existing["source_ids"].add(source["source_id"])
            existing["orphan_extinf_sha256"].add(source["extinf_sha256"])
            existing["proof_commits"].update(candidate.get("proof_commits", []))
            existing["proof_rules"].update(candidate.get("proof_rules", []))
            existing["proof_existing_source_ids"].update(
                candidate.get("proof_existing_source_ids", []))
    if set(index) != set(proof_states):
        raise ValueError("Cannot archive candidates without exact probe status")
    rows = []
    for digest in sorted(index):
        old = index[digest]
        status = proof_states[digest]
        rows.append({"url": old["url"], "url_sha256": digest,
                     "source_ids": sorted(old["source_ids"]),
                     "orphan_extinf_sha256": sorted(old["orphan_extinf_sha256"]),
                     "proof_commits": sorted(old["proof_commits"]),
                     "proof_rules": sorted(old["proof_rules"]),
                     "proof_existing_source_ids":
                         sorted(old["proof_existing_source_ids"]),
                     "probe_status": status["status"],
                     "video_stream": bool(status.get("video_stream")),
                     "audio_stream": bool(status.get("audio_stream")),
                     "ffmpeg_video_audio_decoded":
                         status.get("ffmpeg_video_audio_decoded") is True,
                     "needs_retest":
                         status.get("ffmpeg_video_audio_decoded") is not True})
    return rows


def audit(*, report_path, sealed_path, key_path, limit=20,
          reader=_read_document, commits=historical_revisions, probe=probe_real_av,
          known_source_catalog=None, all_candidates_sealed_path=None,
          immutable_orphan_baseline_path=None, public_registry=False,
          registry_fetcher=None, targeted_code_search=False,
          targeted_fetcher=None):
    if all_candidates_sealed_path is not None:
        paths = [Path(report_path).resolve(), Path(sealed_path).resolve(),
                 Path(all_candidates_sealed_path).resolve()]
        if len(set(paths)) != 3:
            raise ValueError("Public and encrypted output paths must be distinct")
        if (Path(all_candidates_sealed_path).exists() or
                Path(all_candidates_sealed_path).is_symlink()):
            raise ValueError("Refusing overwrite of sealed candidate archive")
    immutable = None
    if immutable_orphan_baseline_path is not None:
        from orphan_baseline_guard import load_immutable_baseline
        immutable = load_immutable_baseline(immutable_orphan_baseline_path)
    source_documents = {}
    official_metadata_fallback_ids = []
    sources = []
    source_summaries = []
    source_evidence = []
    historic_errors = 0
    for ident, repo, path in ORIGINALS:
        upstream = "https://raw.githubusercontent.com/" + repo + "/main/" + quote(path)
        current = reader(upstream)
        source_documents[ident] = current
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
    # Reuse each publisher document once: repeated rapid requests can trigger
    # temporary HTML/error responses instead of the published M3U. No retry
    # storms, no synthetic metadata and no unsafe host fallbacks.
    onur_cache = {}
    def onur_reader(url):
        if url in onur_cache:
            if onur_cache[url] is None:
                raise ValueError("Publisher document unavailable in this run")
            return onur_cache[url]
        try:
            result = reader(url)
            if not result.lstrip("\ufeff\r\n\t ").startswith(("#EXTM3U", "#EXTINF:")):
                raise ValueError("Not an M3U document")
            onur_cache[url] = result
            return result
        except (OSError, TypeError, ValueError):
            onur_cache[url] = None
            raise

    for ident, source_url in ONUR_SOURCES:
        original_current_available = True
        try:
            current = onur_reader(source_url)
        except (OSError, TypeError, ValueError):
            if immutable is None:
                raise
            current = restore_exact_original_metadata_from_official_alternates(
                ident, immutable, reader=onur_reader)
            official_metadata_fallback_ids.append(ident)
            original_current_available = False
        source_documents[ident] = current
        _, orphans = parse_exact_pairs(current)
        orphans = [o for o in orphans
                   if o["reason"] != "EXPLICIT_NO_PUBLIC_STREAM_PLACEHOLDER"]
        alts, alt_status = find_official_alternates(orphans, reader=onur_reader)
        source_summaries.append({
            "source_id": ident, "orphan_count": len(orphans),
            "original_source_current_document_available": original_current_available,
            "exact_official_metadata_fallback_only": not original_current_available,
            "excluded_nonpublic_http_references":
                count_excluded_network_references(current),
            "original_document_sha256": _hash(current), **alt_status})
        for item in orphans:
            sources.append({
                "source_id": ident, "extinf_sha256": item["extinf_sha256"],
                "extinf": item["extinf"], "reason": item["reason"],
                "line_number": item["line_number"],
                "uri_structure": item["uri_structure"],
                "candidates": alts.get(item["extinf"], {})})
    identity_guard = None
    fixed_current_originals = []
    if immutable_orphan_baseline_path is not None:
        from orphan_baseline_guard import reconcile_immutable_sources
        identity_guard = reconcile_immutable_sources(immutable, source_documents)
        fixed_current_originals = candidate_repairs_from_current_verified_sources(
            immutable, source_documents)
        orphan_occurrences_before_repairs = len(sources)
        by_source_identity = {
            (x["source_id"], x["extinf_sha256"]): x for x in sources}
        for fixed in fixed_current_originals:
            key = (fixed["source_id"], fixed["extinf_sha256"])
            original = by_source_identity.get(key)
            if original is not None:
                # An upstream file may contain one broken and one valid copy
                # of the exact same original EXTINF: preserve both evidences.
                original["candidates"].update(fixed["candidates"])
                original["reason"] = "UPSTREAM_PARTIALLY_RESTORED"
            else:
                sources.append(fixed)
                by_source_identity[key] = fixed
    else:
        orphan_occurrences_before_repairs = len(sources)
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
                record["proof_rules"] = sorted(set(record.get("proof_rules", [])) |
                                              set(candidate.get("proof_rules", [])))
    public_registry_report = {"status": "NOT_REQUESTED"}
    if public_registry:
        from orphan_iptv_org_registry import find_exact_orphan_streams
        if registry_fetcher is None:
            registry_candidates, public_registry_report = find_exact_orphan_streams(sources)
        else:
            registry_candidates, public_registry_report = find_exact_orphan_streams(
                sources, fetcher=registry_fetcher)
        for item in sources:
            for urlsha, candidate in registry_candidates.get(item["extinf_sha256"], {}).items():
                record = item["candidates"].setdefault(urlsha, {"url": candidate["url"]})
                if record["url"] != candidate["url"]:
                    raise ValueError("Contradictory registry URL for SHA256 identity")
                for field in ("proof_existing_source_ids", "proof_rules"):
                    record[field] = sorted(set(record.get(field, [])) | set(candidate[field]))
    targeted_search_report = {"status": "NOT_REQUESTED"}
    if targeted_code_search:
        # Only currently URL-less exact original identities get targeted code
        # search; pinned public M3U references are NOT media playback proof.
        from orphan_targeted_github_code import targeted_source_references
        if known_source_catalog is None:
            raise ValueError("Targeted code search needs approved source catalog")
        missing = {}
        for item in sources:
            if not item["candidates"]:
                missing.setdefault(item["extinf_sha256"], item)
        known = {item["url"] for item in known_source_catalog
                 if isinstance(item.get("url"), str)}
        kwargs = {} if targeted_fetcher is None else {"fetcher": targeted_fetcher}
        pinned_sources, targeted_search_report = targeted_source_references(
            list(missing.values()), known, **kwargs)
        matched_count = 0
        if pinned_sources:
            targeted, targeted_scan_report = find_existing_exact_identity(
                sources, pinned_sources, reader=reader)
            matched_count = len(targeted)
            for item in sources:
                for urlsha, candidate in targeted.get(item["extinf_sha256"], {}).items():
                    record = item["candidates"].setdefault(
                        urlsha, {"url": candidate["url"]})
                    if record["url"] != candidate["url"]:
                        raise ValueError("Contradictory targeted source URL for SHA")
                    for field in ("proof_existing_source_ids", "proof_rules"):
                        record[field] = sorted(
                            set(record.get(field, [])) | set(candidate[field]))
            targeted_search_report["pinned_source_files_unavailable"] = (
                targeted_scan_report["source_documents_unavailable_count"])
        targeted_search_report["exact_identity_matches_found"] = matched_count
    probed, verified_rows, mapping = evaluate(sources, probe=probe)
    proof_states = {p["url_sha256"]: p for p in probed}
    sealed_candidate_count = None
    if all_candidates_sealed_path is not None:
        # All failed candidates are retained for later bounded retesting;
        # this does not promote a failed stream to playable.
        private_candidates = sealed_retest_candidate_rows(sources, proof_states)
        sealed_candidate_count = seal_rows(
            private_candidates, key_path, all_candidates_sealed_path)
    for item in sources:
        candidate_evidence = []
        for sha, record in sorted(item["candidates"].items()):
            p = proof_states[sha]
            candidate_evidence.append({"url_sha256": sha,
                                       "video_stream": bool(p.get("video_stream")),
                                       "audio_stream": bool(p.get("audio_stream")),
                                       "ffmpeg_video_audio_decoded":
                                           p.get("ffmpeg_video_audio_decoded") is True,
                                       "status": p["status"],
                                       "diagnostic_category": p.get("diagnostic_category"),
                                       "proof_commits": record.get("proof_commits", []),
                                       "proof_rules": sorted(record.get("proof_rules", [])),
                                       "proof_original_upstream_now_has_uri":
                                           bool(record.get("proof_original_upstream_now_has_uri")),
                                       "publisher_official_alternate":
                                           bool(record.get("proof_official_feed")),
                                       "exact_epg_and_name_other_source":
                                           record.get("proof_existing_source_ids", [])})
        source_evidence.append({
            "source_id": item["source_id"], "line_number": item["line_number"],
            "extinf_sha256": item["extinf_sha256"], "reason": item["reason"],
            "uri_structure": item["uri_structure"],
            "historical_or_official_candidates": len(candidate_evidence),
            "verified_av_candidates": sum(x["ffmpeg_video_audio_decoded"]
                                          for x in candidate_evidence),
            "candidates": candidate_evidence})
    result = {
        "schema": 1, "kind": "FOUR_UPSTREAM_ORPHAN_REPAIR_EVIDENCE_NOT_IBO",
        "status": "SOURCE_REPAIR_CANDIDATES_VERIFIED" if verified_rows
                  else "NO_CURRENT_AV_VERIFIED_REPLACEMENTS",
        "upstream_sources": source_summaries,
        "unavailable_original_publisher_documents_restored_as_exact_metadata_only":
            sorted(official_metadata_fallback_ids),
        "original_publisher_media_streams_inferred_from_metadata": False,
        "currently_unpaired_source_occurrences": orphan_occurrences_before_repairs,
        "restored_current_upstream_uri_occurrences": len(fixed_current_originals),
        "orphan_entries": len(sources),
        "unique_orphan_metadata_identities": len({
            item["extinf_sha256"] for item in sources}),
        "duplicate_orphan_occurrences": len(sources) - len({
            item["extinf_sha256"] for item in sources}),
        "orphan_uri_structure_counts": dict(sorted(Counter(
            item["uri_structure"] for item in sources).items())),
        "public_iptv_org_registry_reconciliation": public_registry_report,
        "targeted_public_github_code_search": targeted_search_report,
        "unique_candidate_urls_historically_or_officially_proven": len(probed),
        "all_proven_url_candidates_sealed_for_future_retest": sealed_candidate_count,
        "currently_unverified_candidate_urls_preserved_in_encrypted_archive":
            sealed_candidate_count - len(verified_rows)
            if sealed_candidate_count is not None else None,
        "unique_candidates_video_audio_verified": len(verified_rows),
        "orphan_entries_with_current_av": sum(
            any(p["ffmpeg_video_audio_decoded"] for p in x["candidates"])
            for x in source_evidence),
        "orphan_entries_without_current_av": sum(
            not any(p["ffmpeg_video_audio_decoded"] for p in x["candidates"])
            for x in source_evidence),
        "unavailable_historical_git_files": historic_errors,
        "existing_catalog_reconciliation": existing_report,
        "immutable_orphan_identity_guard": identity_guard,
        "records": source_evidence,
        "plain_stream_urls_reported": False, "protected_playlist_modified": False,
        "ibo_device_verified": False,
        "av_acceptance_rule": "FFMPEG_VIDEO_AND_AUDIO_DECODED_ONLY",
        "scan_scope": "FOUR_ORIGINAL_M3U_FEEDS_63_KNOWN_AND_VALIDATED_PUBLIC_DOCUMENT_SOURCES",
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
    p.add_argument("--all-candidates-sealed", type=Path, required=True)
    p.add_argument("--public-key", type=Path,
                   default=Path("v2/config/stage3_transit_public.pem"))
    p.add_argument("--history-revisions", type=int, default=20)
    p.add_argument("--v2-main-playlist-snapshot", type=Path)
    p.add_argument("--v2-main-foreign-archive-snapshot", type=Path)
    p.add_argument("--include-public-discovery", action="store_true",
                   help="Review bounded verified public source reports only for exact orphan matches")
    p.add_argument("--include-targeted-code-search", action="store_true",
                   help="Bounded GitHub code search for source-less original identities")
    p.add_argument("--include-public-registry", action="store_true",
                   help="Cross-check exact EPG ID and registered name in public IPTV-org API")
    p.add_argument("--immutable-orphan-baseline", type=Path,
                   default=Path("v2/history/m3u-orphan-50-hash-baseline.json"))
    args = p.parse_args()
    if (args.report.exists() or args.report.is_symlink()
            or args.sealed.exists() or args.sealed.is_symlink()
            or args.all_candidates_sealed.exists()
            or args.all_candidates_sealed.is_symlink()
            or len({args.report.resolve(), args.sealed.resolve(),
                    args.all_candidates_sealed.resolve()}) != 3
            or not 1 <= args.history_revisions <= 300):
        p.error("Unsafe output path or unbounded history")
    if bool(args.v2_main_playlist_snapshot) != bool(args.v2_main_foreign_archive_snapshot):
        p.error("Both protected V2 main snapshots must be provided together")
    known_catalog = existing_source_catalog()
    if args.include_public_discovery:
        from orphan_source_expansion import reviewed_source_references
        added_sources, public_source_stats = reviewed_source_references(
            {x["url"] for x in known_catalog})
        known_catalog.extend(added_sources)
        print("Extra public source references for exact orphan metadata only:",
              public_source_stats["new_source_references"])
    if args.v2_main_playlist_snapshot:
        from main_playlist_candidate_bridge import validated_v2_main_catalog
        protected_catalog, protected_counts = validated_v2_main_catalog(
            args.v2_main_playlist_snapshot, args.v2_main_foreign_archive_snapshot)
        known_catalog.extend(protected_catalog)
        print("Protected main read-only source handoff:", protected_counts)
    result = audit(report_path=args.report, sealed_path=args.sealed,
                   key_path=args.public_key, limit=args.history_revisions,
                   known_source_catalog=known_catalog,
                   all_candidates_sealed_path=args.all_candidates_sealed,
                   immutable_orphan_baseline_path=args.immutable_orphan_baseline,
                   public_registry=args.include_public_registry,
                   targeted_code_search=args.include_targeted_code_search)
    if result["immutable_orphan_identity_guard"]["status"] == "LOSS_RISK_REVIEW_REQUIRED":
        print("LOSS_RISK: original orphan EXTINF metadata missing, requires manual review")
        raise SystemExit(2)
    print("Four source orphan metadata occurrences:", result["orphan_entries"],
          "exact historic/official candidate URL hashes:",
          result["unique_candidate_urls_historically_or_officially_proven"],
          "currently video+audio verified:",
          result["unique_candidates_video_audio_verified"],
          "all candidate URLs sealed:",
          result["all_proven_url_candidates_sealed_for_future_retest"],
          "orphan entries with no current verified replacement:",
          result["orphan_entries_without_current_av"],
          "immutable historical EXTINF source identities present:",
          result["immutable_orphan_identity_guard"]["original_source_occurrences_still_present"],
          "/ 55",
          "existing source catalog checked:",
          result.get("existing_catalog_reconciliation", {}).get(
              "preconfigured_sources_checked"))


if __name__ == "__main__":
    main()

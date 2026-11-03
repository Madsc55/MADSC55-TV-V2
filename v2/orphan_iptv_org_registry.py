#!/usr/bin/env python3
"""Exact metadata-only public IPTV-org registry reconciliation.

IPTV-org channels/streams are public discovery evidence, not an official
publisher endorsement or a guarantee that media plays. We ONLY reconcile a
source orphan when both channel ID AND public registry channel name/alt-name
are exactly equal after Unicode casefold and whitespace normalization.
Never use stream title alone, fuzzy channel names or fabricated URLs.
No plaintext URL is written to reports; the caller RSA-seals all candidates.
"""
from collections import defaultdict
import json
from stage3_historical_source_recovery import _read
from historical_url_recovery import validate_url

CHANNELS_ENDPOINT = "https://iptv-org.github.io/api/channels.json"
STREAMS_ENDPOINT = "https://iptv-org.github.io/api/streams.json"
MAX_ROWS = 150000
MAX_JSON_BYTES = 32_000_000
MAX_MATCHED_STREAMS = 800


def norm(value):
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def _json_rows(raw, label):
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, bytes) or len(raw) > MAX_JSON_BYTES:
        raise ValueError("UNSAFE_REGISTRY_BYTES_" + label)
    data = json.loads(raw)
    if not isinstance(data, list) or len(data) > MAX_ROWS:
        raise ValueError("UNSAFE_REGISTRY_ROWS_" + label)
    return data


def find_exact_orphan_streams(orphan_rows, *, fetcher=_read):
    from orphan_m3u_recovery import exact_channel_identity, _hash
    wanted = defaultdict(set)
    for item in orphan_rows:
        key = exact_channel_identity(item["extinf"])
        if key is not None:
            wanted[key].add(item["extinf_sha256"])
    empty = {"status": "NO_EXACT_REGISTRY_MATCH",
             "channel_records_read": 0, "stream_records_read": 0,
             "matched_orphan_metadata_identities": 0,
             "unique_exact_registry_urls": 0,
             "streams_requiring_headers_skipped": 0,
             "invalid_or_nonpublic_stream_urls_skipped": 0,
             "proof_rule": "EXACT_IPTV_ORG_CHANNEL_ID_AND_REGISTERED_NAME_NOT_AV"}
    if not wanted:
        return {}, {**empty, "status": "NO_EPG_AND_NAME_IDENTITIES_TO_MATCH"}
    # Exact hardcoded endpoint URLs: no user-supplied registry destination.
    try:
        channels = _json_rows(fetcher(CHANNELS_ENDPOINT), "CHANNELS")
        streams = _json_rows(fetcher(STREAMS_ENDPOINT), "STREAMS")
    except (OSError, ValueError, TypeError, UnicodeError, KeyError):
        return {}, {**empty, "status": "PUBLIC_REGISTRY_UNAVAILABLE"}
    names_by_id = defaultdict(set)
    wanted_ids = {key[0] for key in wanted}
    for row in channels:
        if not isinstance(row, dict):
            continue
        channel_id = norm(row.get("id"))
        if channel_id not in wanted_ids:
            continue
        if row.get("is_nsfw") is True or row.get("closed") or row.get("replaced_by"):
            continue
        names = [row.get("name")] + (
            row["alt_names"] if isinstance(row.get("alt_names"), list) else [])
        names_by_id[channel_id].update(n for value in names if (n := norm(value)))
    matched = defaultdict(dict)
    header_count = invalid_count = 0
    for row in streams:
        if not isinstance(row, dict):
            continue
        channel_id = norm(row.get("channel"))
        if channel_id not in names_by_id:
            continue
        keys = [(channel_id, name) for name in names_by_id[channel_id]
                if (channel_id, name) in wanted]
        if not keys:
            continue
        if row.get("referrer") or row.get("user_agent"):
            # URL alone cannot be audited without publisher-requested headers.
            header_count += 1
            continue
        url = row.get("url")
        if not isinstance(url, str) or not validate_url(url):
            invalid_count += 1
            continue
        for key in keys:
            for orphan_sha in wanted[key]:
                candidates = matched[orphan_sha]
                h = _hash(url)
                candidates[h] = {
                    "url": url,
                    "proof_existing_source_ids": ["iptv-org-public-registry"],
                    "proof_rules": ["EXACT_IPTV_ORG_CHANNEL_ID_AND_REGISTERED_NAME"],
                }
                if sum(map(len, matched.values())) > MAX_MATCHED_STREAMS:
                    raise ValueError("REGISTRY_MATCH_LIMIT_EXCEEDED")
    nurls = len({h for c in matched.values() for h in c})
    return dict(matched), {
        "status": "EXACT_REGISTRY_CANDIDATES_FOUND" if matched else "NO_EXACT_REGISTRY_MATCH",
        "channel_records_read": len(channels),
        "stream_records_read": len(streams),
        "matched_orphan_metadata_identities": len(matched),
        "unique_exact_registry_urls": nurls,
        "streams_requiring_headers_skipped": header_count,
        "invalid_or_nonpublic_stream_urls_skipped": invalid_count,
        "proof_rule": "EXACT_IPTV_ORG_CHANNEL_ID_AND_REGISTERED_NAME_NOT_AV",
    }

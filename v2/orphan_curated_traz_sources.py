#!/usr/bin/env python3
"""Pinned third-party TR/AZ M3U candidate sources; not verified playback.

The immutable repository revision was inspected with 254 TR and 33 AZ entries.
Compared with the upstream iptv-org country streams at inspection time, it
contained 70 additional TR and 13 AZ stream URL candidates. Different source
metadata is NOT proof of a new channel nor working video/audio.

These references never enter the protected playlist, core 46 fixed sources,
or 17 historical dynamic source identities.
"""
from orphan_source_expansion import safe_reference_url

REPOSITORY = "shovo127/IPTV-By-Shovo"
PINNED_REVISION = "f3008de1e64cd7049acf2a897868ad1faa1bf6c1"
COUNTRIES = (("tr", "TR"), ("az", "AZ"))


def pinned_traz_candidate_references(known_urls=(), known_ids=()):
    known_urls, known_ids = set(known_urls), set(known_ids)
    result = []
    for code, scope in COUNTRIES:
        url = ("https://raw.githubusercontent.com/" + REPOSITORY + "/"
               + PINNED_REVISION + "/streams/" + code + ".m3u")
        source_id = "orphan-extra-public-" + code + "-" + PINNED_REVISION[:12]
        if not safe_reference_url(url):
            raise ValueError("Unapproved public candidate source URL")
        if source_id in known_ids and url not in known_urls:
            raise ValueError("Conflicting candidate source identity")
        if url in known_urls:
            continue
        result.append({
            "id": source_id, "url": url, "scope": scope, "kind": "m3u",
            "origin": "orphan-discovery-reference",
            "source_identity_rule": "EXACT_EXTINF_OR_EPG_AND_NAME_ONLY",
            "playback_verified": False,
            "ibo_playlist_modified": False,
        })
        known_urls.add(url)
        known_ids.add(source_id)
    return result

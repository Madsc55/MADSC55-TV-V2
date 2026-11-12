"""Offline Stage 2 bridge: identity, URL digest and recovery decisions.

Does not fetch channels, probe streams, or modify the production IBO playlist.
"""
from identity_metadata import identity_metadata, verify_epg_ids
from recovery_queue import build_queue, sha_for_url


def integrate(records, *, scopes=None, xmltv_text=None, max_attempts=3):
    """Enrich existing observations, validate identity, then partition recovery."""
    if not isinstance(records, list):
        raise ValueError("Records must be a list")
    if scopes is None:
        scopes = {}
    if not isinstance(scopes, dict):
        raise ValueError("Scopes must be an object")
    enriched = []
    for original in records:
        if not isinstance(original, dict):
            raise ValueError("Recovery observation must be an object")
        row = dict(original)
        url = row.get("url")
        digest = row.get("url_sha256")
        if url is not None:
            actual = sha_for_url(url)
            if digest is not None and digest != actual:
                raise ValueError("Recovery URL SHA-256 mismatch")
            row["url_sha256"] = actual
        elif digest is None:
            raise ValueError("URL or URL SHA-256 required")
        scope = scopes.get(row.get("source"), "candidate")
        hints = identity_metadata(row, scope)
        for key, value in hints.items():
            if key not in row:
                row[key] = value
        # Do not allow a caller's unverified metadata flags to become verified.
        row["country_verified"] = False
        row["category_verified"] = False
        row["epg_verified"] = False
        enriched.append(row)
    if xmltv_text is not None:
        enriched = verify_epg_ids(enriched, xmltv_text)
    decisions = build_queue(enriched, max_attempts=max_attempts)
    # Never return raw stream URLs or credentials in a public integration report.
    safe = [{key: value for key, value in row.items()
             if key in ("url_sha256", "name", "source", "country_hint",
                        "country_verified", "category_hint", "category_verified",
                        "epg_id_candidate", "epg_verified",
                        "epg_programme_available", "epg_match_type", "status")}
            for row in enriched]
    return {"schema": 1, "mode": "offline-no-channel-search",
            "observations": safe, "recovery": decisions}

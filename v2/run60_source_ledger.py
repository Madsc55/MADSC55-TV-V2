#!/usr/bin/env python3
"""Verify original #60 GitHub auto-source identities against sealed run evidence.

Source URLs here refer to public M3U DOCUMENTS, not IPTV playback credentials.
Only exact original discovery snapshot entries are accepted: no guessed URLs,
automatic channel publication, or silent replacement of historical provenance.
"""
import json
from pathlib import Path
from urllib.parse import urlsplit


def read_verified_ledger(ledger_path, snapshot_path, historical_loss,
                         expected_sources=17, expected_old_only=8449):
    ledger = json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    snapshot = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
    if (ledger.get("schema") != 1 or ledger.get("source_run_id") != 40743765437
            or ledger.get("artifact_id") != 12840886350
            or not isinstance(ledger.get("sources"), list)
            or not isinstance(snapshot.get("sources"), list)):
        raise ValueError("Original #60 source provenance unavailable")
    source_breakdown = {r["source_id"]: r for r in historical_loss["source_breakdown"]}
    found, found_urls, items = set(), set(), []
    for row in ledger["sources"]:
        ident = row.get("id", "")
        if not isinstance(ident, str) or not ident.startswith("github-auto-"):
            raise ValueError("Invalid #60 dynamic source identity")
        idx_str = ident[len("github-auto-"):]
        if not idx_str.isdecimal() or str(int(idx_str)) != idx_str:
            raise ValueError("Invalid #60 source index")
        index = int(idx_str)
        if ident in found or row.get("url") in found_urls or index >= len(snapshot["sources"]):
            raise ValueError("Duplicate or out-of-range historical source")
        original = snapshot["sources"][index]
        evidence = source_breakdown.get(ident)
        if (row.get("url") != original.get("url")
                or row.get("original_entries") != original.get("entries")
                or not evidence or row.get("run60_tested") != evidence["old_tested"]
                or row.get("old_only") != evidence["old_only_url_identities"]):
            raise ValueError("Historical source URL or count not backed by original #60 evidence")
        u = urlsplit(row["url"])
        if (u.scheme != "https" or u.hostname != "raw.githubusercontent.com"
                or u.username or u.password or u.fragment or u.port not in (None, 443)
                or row.get("kind") != "m3u"):
            raise ValueError("Untrusted historical M3U document endpoint")
        found.add(ident)
        found_urls.add(row["url"])
        items.append({"id": ident, "url": row["url"], "kind": "m3u",
                      "scope": "candidate", "historical_source_only": True})
    if (len(items) != expected_sources
            or sum(row["old_only"] for row in ledger["sources"]) != expected_old_only):
        raise ValueError("Incomplete #60 dynamic source ledger")
    return items


def inventory_coverage(historical, active_sources, supplemental_rows):
    active = {s["id"] for s in active_sources}
    supplementary = {s["source_id"]: s for s in supplemental_rows}
    required = [r for r in historical["source_breakdown"]
                if r["source_id"].startswith("github-auto-")
                and r["old_tested"] and r["source_id"] not in active]
    missing_map = sorted(r["source_id"] for r in required
                         if r["source_id"] not in supplementary)
    inaccessible = sorted(r["source_id"] for r in required
                          if r["source_id"] in supplementary
                          and supplementary[r["source_id"]]["status"]
                          not in ("PARSED_M3U_NOT_PLAYBACK_VERIFIED",
                                  "PARSED_WITH_NON_HTTP_REFERENCES_NOT_PLAYBACK_VERIFIED",
                                  "PARSED_HISTORICAL_HEADERLESS_NORMALIZED_NO_PLAYBACK"))
    return {
        "historical_dynamic_source_identities": len(required),
        "recovered_exact_original_source_locations": len(required) - len(missing_map),
        "unmapped_source_ids": missing_map,
        "not_fully_readable_source_ids": inaccessible,
        "all_original_locations_recovered": not missing_map,
        "all_original_feeds_fully_parsed_now": not missing_map and not inaccessible,
        "playback_reverified": False,
    }

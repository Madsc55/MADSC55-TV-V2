#!/usr/bin/env python3
"""Read-only provenance acceptance for approved official-page HTTP audits.

Checks the full page/reference relation, not merely aggregate counters.
HTTP references are discovery evidence, never decoded video/audio proof.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{64}\Z")


def verify(report):
    if not isinstance(report, dict) or report.get("kind") != "READ_ONLY_APPROVED_PAGE_HTTP_REFERENCE_AUDIT":
        raise ValueError("Unexpected official-page audit schema")
    if report.get("playback_verified") is not False or report.get("protected_playlist_modified") is not False:
        raise ValueError("HTTP audit must not claim playback or playlist writes")
    pages = report.get("pages")
    if not isinstance(pages, list) or not pages:
        raise ValueError("Missing page provenance")
    ids, occurrences, fetched = set(), Counter(), 0
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Invalid page record")
        page_id, status = page.get("page_id"), page.get("status")
        if not isinstance(page_id, str) or not page_id or page_id in ids:
            raise ValueError("Missing or duplicate page identity")
        ids.add(page_id)
        refs = page.get("references", [])
        if not isinstance(refs, list) or any(not isinstance(x, str) or not SHA.fullmatch(x) for x in refs):
            raise ValueError("Invalid reference hashes")
        if len(refs) != len(set(refs)):
            raise ValueError("Duplicate reference within a page")
        if status not in ("FETCHED", "ERROR"):
            raise ValueError("Unknown official-page fetch status")
        if status == "ERROR" and (not isinstance(page.get("error"), str) or not page["error"]):
            raise ValueError("Failed page missing explicit error provenance")
        if status == "FETCHED" and page.get("error"):
            raise ValueError("Fetched page cannot carry a failure error")
        if status == "FETCHED":
            fetched += 1
            if not isinstance(page.get("html_sha256"), str) or not SHA.fullmatch(page["html_sha256"]):
                raise ValueError("Fetched page missing content digest")
        elif refs:
            raise ValueError("Unfetched page cannot claim extracted references")
        occurrences.update(refs)
    expected = {
        "pages_checked": len(pages),
        "pages_fetched": fetched,
        "unique_reference_hashes": len(occurrences),
        "shared_reference_hashes": sum(n > 1 for n in occurrences.values()),
        "reference_source_associations": sum(occurrences.values()),
    }
    for key, value in expected.items():
        if type(report.get(key)) is not int or report[key] != value:
            raise ValueError("Official-page audit counter mismatch: " + key)
    return expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    summary = verify(json.loads(args.report.read_text(encoding="utf-8")))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

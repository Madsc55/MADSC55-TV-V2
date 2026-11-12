#!/usr/bin/env python3
"""#34 bounded live API contract check. Metadata only; no playlist or stream fetch."""
import json
import sys
import urllib.error
from discovery_34 import search_url, fetch_json, repository_candidates

def main():
    results = {}
    for source in ("github", "gitlab", "codeberg"):
        try:
            payload = fetch_json(search_url(source, "turkish-iptv"))
            records = repository_candidates(source, payload)
            results[source] = {"status": "ok", "candidates": len(records)}
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            results[source] = {"status": "error", "reason": type(exc).__name__}
    print(json.dumps(results, indent=2))
    if any(row["status"] != "ok" for row in results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Bounded live metadata contracts. Fail closed for required provider errors."""
import json
import sys
import urllib.error
from discovery_34 import search_url, fetch_json, repository_candidates

def probe(source, query="turkish-iptv"):
    url = search_url(source, query)
    try:
        payload = fetch_json(url)
        return {"status": "ok", "candidates": len(repository_candidates(source, payload))}
    except urllib.error.HTTPError as exc:
        return {"status": "error", "reason": "HTTP_" + str(exc.code)}
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {"status": "error", "reason": type(exc).__name__}

def main():
    results = {source: probe(source) for source in ("github", "gitlab", "codeberg")}
    print(json.dumps(results, indent=2))
    if any(row["status"] != "ok" for row in results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main()

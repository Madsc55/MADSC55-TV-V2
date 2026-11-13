#!/usr/bin/env python3
"""Bounded live metadata contracts. Fail closed for required provider errors."""
import json
import sys
import time
import urllib.error
from discovery_34 import search_url, fetch_json, repository_candidates

RETRYABLE_HTTP = frozenset((408, 425, 429, 500, 502, 503, 504))
MAX_ATTEMPTS = 3

def probe(source, query="turkish-iptv", fetch=fetch_json, sleep=time.sleep):
    url = search_url(source, query)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            payload = fetch(url)
            # A 200 response with an API error object is not successful discovery.
            if source == "gitlab":
                valid = isinstance(payload, list)
            else:
                key = "items" if source == "github" else "data"
                valid = isinstance(payload, dict) and isinstance(payload.get(key), list)
            if not valid:
                raise ValueError("Invalid repository API response shape")
            return {"status": "ok", "candidates": len(repository_candidates(source, payload)), "attempts": attempt}
        except urllib.error.HTTPError as exc:
            retryable = exc.code in RETRYABLE_HTTP
            if retryable and attempt < MAX_ATTEMPTS:
                sleep(attempt)
                continue
            return {"status": "error", "reason": "HTTP_" + str(exc.code),
                    "retryable": retryable, "provider": source, "attempts": attempt,
                    "endpoint_host": {"github": "api.github.com", "gitlab": "gitlab.com", "codeberg": "codeberg.org"}[source]}
        except urllib.error.URLError as exc:
            # Temporary DNS/connection failures may recover; never mark them successful.
            if attempt < MAX_ATTEMPTS:
                sleep(attempt)
                continue
            return {"status": "error", "reason": "URLError",
                    "retryable": True, "provider": source, "attempts": attempt}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {"status": "error", "reason": type(exc).__name__,
                    "provider": source, "attempts": attempt}

def main():
    results = {source: probe(source) for source in ("github", "gitlab", "codeberg")}
    print(json.dumps(results, indent=2))
    if any(row["status"] != "ok" for row in results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main()

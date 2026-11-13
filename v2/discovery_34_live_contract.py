#!/usr/bin/env python3
"""Bounded live metadata contracts. Fail closed for required provider errors."""
import json
import sys
import time
import urllib.error
from discovery_34 import QUERIES, search_url, fetch_json, repository_candidates

RETRYABLE_HTTP = frozenset((408, 425, 429, 500, 502, 503, 504))
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 60

def retry_delay(exc, attempt):
    """Honor a bounded numeric Retry-After; otherwise back off more for 429."""
    headers = getattr(exc, "headers", None)
    raw = headers.get("Retry-After") if headers is not None else None
    try:
        if raw is not None:
            return min(MAX_RETRY_AFTER_SECONDS, max(0, int(raw.strip())))
    except (AttributeError, TypeError, ValueError):
        pass
    return min(MAX_RETRY_AFTER_SECONDS, (5 if getattr(exc, "code", None) == 429 else 1) * (2 ** (attempt - 1)))

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
                sleep(retry_delay(exc, attempt))
                continue
            headers = getattr(exc, "headers", None)
            return {"status": "error", "reason": "HTTP_" + str(exc.code),
                    "http_status": exc.code, "http_reason": str(getattr(exc, "reason", ""))[:120],
                    "retry_after": headers.get("Retry-After") if headers is not None else None,
                    "rate_limit_remaining": (headers.get("X-RateLimit-Remaining") or headers.get("x-ratelimit-remaining")) if headers is not None else None,
                    "retryable": retryable, "provider": source, "attempts": attempt,
                    "endpoint_host": {"github": "api.github.com", "gitlab": "gitlab.com", "codeberg": "codeberg.org"}[source]}
        except urllib.error.URLError as exc:
            # Temporary DNS/connection failures may recover; never mark them successful.
            if attempt < MAX_ATTEMPTS:
                sleep(attempt)
                continue
            return {"status": "error", "reason": "URLError",
                    "retryable": True, "provider": source, "attempts": attempt}
        except (TimeoutError, ConnectionResetError, ConnectionAbortedError) as exc:
            if attempt < MAX_ATTEMPTS:
                sleep(attempt)
                continue
            return {"status": "error", "reason": type(exc).__name__,
                    "retryable": True, "provider": source, "attempts": attempt}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {"status": "error", "reason": type(exc).__name__,
                    "provider": source, "attempts": attempt}

def probe_queries(source, queries=QUERIES, fetch=fetch_json, sleep=time.sleep):
    """Probe every configured discovery term; preserve per-query failures."""
    results = []
    for query in queries:
        row = probe(source, query=query, fetch=fetch, sleep=sleep)
        results.append({"query": query, **row})
    failed = [row for row in results if row["status"] != "ok"]
    return {"status": "error" if failed else "ok",
            "queries_checked": len(results),
            "queries_ok": len(results) - len(failed),
            "queries_failed": len(failed),
            "query_results": results}


def main():
    results = {source: probe_queries(source) for source in ("github", "gitlab", "codeberg")}
    print(json.dumps(results, indent=2))
    if any(row["status"] != "ok" for row in results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main()

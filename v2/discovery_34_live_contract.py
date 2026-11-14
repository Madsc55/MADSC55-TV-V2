#!/usr/bin/env python3
"""Bounded live metadata contracts. Fail closed for required provider errors."""
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
import urllib.error
from discovery_34 import QUERIES, search_url, fetch_json, repository_candidates

RETRYABLE_HTTP = frozenset((408, 425, 429, 500, 502, 503, 504))
MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 120

def retry_delay(exc, attempt):
    """Honor numeric or HTTP-date Retry-After, capped to avoid unbounded waits."""
    headers = getattr(exc, "headers", None)
    raw = headers.get("Retry-After") if headers is not None else None
    try:
        if raw is not None:
            try:
                seconds = int(raw.strip())
            except (AttributeError, TypeError, ValueError):
                retry_at = parsedate_to_datetime(raw)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                seconds = int((retry_at - datetime.now(timezone.utc)).total_seconds())
            return min(MAX_RETRY_AFTER_SECONDS, max(0, seconds))
        reset = (headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")) if headers is not None else None
        if reset is not None and getattr(exc, "code", None) == 429:
            seconds = int(reset) - int(time.time())
            return min(MAX_RETRY_AFTER_SECONDS, max(0, seconds))
    except (AttributeError, TypeError, ValueError):
        pass
    return min(MAX_RETRY_AFTER_SECONDS, (30 if getattr(exc, "code", None) == 429 else 1) * (2 ** (attempt - 1)))

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
                    "rate_limit_reset": (headers.get("X-RateLimit-Reset") or headers.get("x-ratelimit-reset")) if headers is not None else None,
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

def provider_rate_limited(row):
    """Recognize HTTP 429 and GitHub-style 403 rate-limit exhaustion."""
    if row.get("http_status") == 429:
        return True
    if row.get("http_status") != 403:
        return False
    reason = str(row.get("http_reason", "")).casefold()
    remaining = str(row.get("rate_limit_remaining", "")).strip()
    return remaining == "0" or "rate limit" in reason


def probe_queries(source, queries=QUERIES, fetch=fetch_json, sleep=time.sleep):
    """Probe terms sequentially; stop provider fanout after an exhausted HTTP 429."""
    terms = list(queries)
    results = []
    for index, query in enumerate(terms):
        row = probe(source, query=query, fetch=fetch, sleep=sleep)
        results.append({"query": query, **row})
        # A 429 is provider-wide pressure, not a query-specific failure.
        # Record remaining terms as skipped rather than amplifying the rate limit.
        if provider_rate_limited(row):
            results.extend({"query": skipped, "status": "skipped",
                            "reason": "provider_rate_limit_circuit_open",
                            "provider": source, "attempts": 0}
                           for skipped in terms[index + 1:])
            break
    failed = [row for row in results if row["status"] == "error"]
    skipped = [row for row in results if row["status"] == "skipped"]
    return {"status": "error" if failed or skipped else "ok",
            "queries_total": len(terms),
            "queries_checked": len(results) - len(skipped),
            "queries_ok": sum(row["status"] == "ok" for row in results),
            "queries_failed": len(failed),
            "queries_skipped": len(skipped),
            "rate_limited": any(provider_rate_limited(row) for row in failed),
            "query_results": results}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, help="Write read-only diagnostic JSON using exclusive creation")
    args = parser.parse_args()
    results = {source: probe_queries(source) for source in ("github", "gitlab", "codeberg")}
    report = {"policy": "METADATA_ONLY_NOT_AV_VERIFIED", "verified_av": 0, "providers": results}
    payload = json.dumps(report, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as output:
            output.write(payload)
    print(payload, end="")
    if any(row["status"] != "ok" for row in results.values()):
        sys.exit(1)

if __name__ == "__main__":
    main()

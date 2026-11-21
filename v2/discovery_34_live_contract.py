#!/usr/bin/env python3
"""Bounded live metadata contracts. Fail closed for required provider errors."""
import argparse
import json
import sys
from pathlib import Path
import time
import urllib.error
import urllib.parse
from discovery_34 import (
    QUERIES, search_url, fetch_json, repository_candidates, incomplete_repository_response,
)
from discovery_provider_requests import (
    MAX_ATTEMPTS, REQUEST_ERRORS, http_error_details, provider_rate_limited,
    retry_delay, _indicates_throttling,
)

def probe(source, query="turkish-iptv", fetch=fetch_json, sleep=time.sleep):
    url = search_url(source, query)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            payload = fetch(url)
            # Some providers return a throttle error envelope with HTTP 200.
            # Stop this provider's remaining queries instead of multiplying load.
            if (isinstance(payload, dict) and
                    any(_indicates_throttling(payload.get(key, ""))
                        for key in ("message", "error"))):
                return {"status": "error", "reason": "provider_throttled_response",
                        "provider": source, "rate_limited": True, "attempts": attempt}
            candidates = len(repository_candidates(source, payload))
            if incomplete_repository_response(source, payload):
                return {"status": "error", "reason": "incomplete_repository_response",
                        "candidates": candidates, "attempts": attempt}
            return {"status": "ok", "candidates": candidates, "attempts": attempt}
        except REQUEST_ERRORS as exc:
            delay = retry_delay(exc, attempt)
            if delay is not None and attempt < MAX_ATTEMPTS:
                if isinstance(exc, urllib.error.HTTPError):
                    exc.close()
                sleep(delay)
                continue
            result = {"status": "error", "reason": type(exc).__name__, "provider": source,
                      "attempts": attempt, "retryable": delay is not None}
            if isinstance(exc, urllib.error.HTTPError):
                result.update(http_error_details(exc))
                result["reason"] = "HTTP_" + str(exc.code)
                result["endpoint_host"] = urllib.parse.urlsplit(url).hostname
            return result


def probe_queries(source, queries=QUERIES, fetch=fetch_json, sleep=time.sleep):
    """Probe terms sequentially and stop provider fanout when throttled."""
    terms = list(queries)
    if (len(terms) > len(QUERIES)
            or any(not isinstance(term, str) or term not in QUERIES for term in terms)
            or len(set(terms)) != len(terms)):
        raise ValueError("Diagnostic queries must be unique members of the approved plan")
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
    parser.add_argument("--provider", choices=("all", "github", "gitlab", "codeberg"), default="all",
                        help="Limit the diagnostic to a single provider without re-querying others")
    args = parser.parse_args()
    sources = ("github", "gitlab", "codeberg") if args.provider == "all" else (args.provider,)
    results = {source: probe_queries(source) for source in sources}
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

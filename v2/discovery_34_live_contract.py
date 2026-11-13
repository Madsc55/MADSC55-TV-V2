#!/usr/bin/env python3
"""Bounded live metadata contracts. Fail closed for required provider errors."""
import json
import sys
import time
import urllib.error
from discovery_34 import search_url, fetch_json, repository_candidates

RETRYABLE_HTTP = frozenset((429, 500, 502, 503, 504))
MAX_ATTEMPTS = 4\nMAX_RETRY_DELAY_SECONDS = 30\n\ndef retry_delay(exc, attempt):\n    """Honor provider backoff hints, with a bounded exponential fallback."""\n    headers = getattr(exc, "headers", None)\n    if headers is not None:\n        value = headers.get("Retry-After")\n        if value is not None:\n            try:\n                return min(MAX_RETRY_DELAY_SECONDS, max(0, int(value)))\n            except (TypeError, ValueError):\n                pass\n        reset = headers.get("X-RateLimit-Reset")\n        if reset is not None:\n            try:\n                return min(MAX_RETRY_DELAY_SECONDS, max(0, int(reset) - int(time.time())))\n            except (TypeError, ValueError):\n                pass\n    return min(MAX_RETRY_DELAY_SECONDS, 2 ** (attempt - 1))

def probe(source, query="turkish-iptv", fetch=fetch_json, sleep=time.sleep):
    url = search_url(source, query)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            payload = fetch(url)
            if source in ("github", "codeberg") and not isinstance(payload, dict):
                raise ValueError("Invalid repository API payload")
            if source == "gitlab" and not isinstance(payload, list):
                raise ValueError("Invalid repository API payload")
            return {"status": "ok", "candidates": len(repository_candidates(source, payload)), "attempts": attempt}
        except urllib.error.HTTPError as exc:
            retryable = exc.code in RETRYABLE_HTTP
            if retryable and attempt < MAX_ATTEMPTS:
                sleep(attempt)
                continue
            return {"status": "error", "reason": "HTTP_" + str(exc.code),
                    "retryable": retryable, "provider": source, "attempts": attempt}
        except urllib.error.URLError as exc:
            # Temporary DNS/connection failures may recover; never mark them successful.
            if attempt < MAX_ATTEMPTS:
                sleep(attempt)
                continue
            return {"status": "error", "reason": "URLError",
                    "retryable": True, "provider": source, "attempts": attempt}
        except (TimeoutError, ConnectionResetError, ConnectionAbortedError) as exc:
            # Bounded retry for transient socket failures; never imply acceptance.
            if attempt < MAX_ATTEMPTS:
                sleep(attempt)
                continue
            return {"status": "error", "reason": type(exc).__name__,
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

"""Shared retry limits and HTTP throttle detection for discovery providers."""
import http.client
import json
import math
import time
import urllib.error
import urllib.parse
from datetime import timezone
from email.utils import parsedate_to_datetime

MAX_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 120
RETRYABLE_HTTP = frozenset((408, 425, 429, 500, 502, 503, 504))
RETRYABLE_CONNECTION = (
    urllib.error.URLError, TimeoutError, ConnectionError, http.client.IncompleteRead,
)
REQUEST_ERRORS = (OSError, ValueError, KeyError, TypeError, http.client.HTTPException)
RATE_LIMIT_PHRASES = ("rate limit", "abuse detection", "too many requests")


def header(exc, name):
    headers = getattr(exc, "headers", None)
    if headers is not None:
        return headers.get(name) or headers.get(name.lower())
    return None


def _indicates_throttling(text):
    return any(phrase in str(text).casefold() for phrase in RATE_LIMIT_PHRASES)


def provider_rate_limited(row):
    status = row.get("http_status")
    return row.get("rate_limited") is True or status == 429 or (status == 403 and (
        row.get("rate_limited") is True
        or str(row.get("rate_limit_remaining", "")).strip() == "0"
        or bool(row.get("retry_after"))
        or _indicates_throttling(row.get("http_reason", ""))
    ))


def http_error_details(exc):
    details = {
        "http_status": exc.code,
        "http_reason": str(exc.reason)[:120],
        "retry_after": header(exc, "Retry-After"),
        "rate_limit_remaining": header(exc, "X-RateLimit-Remaining"),
        "rate_limit_reset": header(exc, "X-RateLimit-Reset"),
    }
    try:
        if exc.code == 403 and not provider_rate_limited(details) and exc.fp is not None:
            # GitHub can put the secondary limit message in JSON behind a generic
            # HTTP Forbidden reason. Use a bounded read and keep the body private.
            payload = json.loads(exc.read(8192))
            if isinstance(payload, dict) and _indicates_throttling(payload.get("message", "")):
                details["rate_limited"] = True
    except (OSError, ValueError, http.client.HTTPException):
        pass
    finally:
        exc.close()
    return details


def _retry_after_seconds(raw):
    if raw is None:
        return None
    try:
        seconds = int(raw)
        return seconds if seconds >= 0 else None
    except (TypeError, ValueError):
        try:
            retry_at = parsedate_to_datetime(raw)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0, math.ceil(retry_at.timestamp() - time.time()))
        except (AttributeError, OverflowError, TypeError, ValueError):
            return None


def _rate_limit_wait(retry_after, remaining, reset):
    delay = _retry_after_seconds(retry_after)
    if delay is None or str(remaining).strip() == "0":
        try:
            delay = max(delay or 0, math.ceil(int(reset) - time.time()))
        except (OverflowError, TypeError, ValueError):
            pass
    return delay


def retry_not_before(details):
    """Record a provider cooldown for later discovery runs."""
    wait = _rate_limit_wait(details.get("retry_after"), details.get("rate_limit_remaining"),
                            details.get("rate_limit_reset"))
    return math.ceil(time.time()) + max(30, wait if wait is not None else 60)


def retry_delay(exc, attempt):
    """Return a delay within the request budget, or None to end this request."""
    if not isinstance(exc, urllib.error.HTTPError):
        return attempt if isinstance(exc, RETRYABLE_CONNECTION) else None
    # HTTP 403 must open the provider circuit immediately; retry only 429.
    throttled = exc.code == 429
    if exc.code not in RETRYABLE_HTTP and not throttled:
        return None
    retry_after = header(exc, "Retry-After")
    if throttled:
        delay = _rate_limit_wait(retry_after, header(exc, "X-RateLimit-Remaining"),
                                 header(exc, "X-RateLimit-Reset"))
    else:
        delay = _retry_after_seconds(retry_after)
    if delay is None:
        base = 1
        if throttled:
            try:
                host = urllib.parse.urlsplit(exc.url or "").hostname
            except ValueError:
                # Malformed provider URL must not abort bounded retry handling.
                host = None
            base = 60 if host == "api.github.com" else 30
        delay = base * (2 ** (attempt - 1))
    if throttled and str(retry_after).strip() == "0":
        try:
            host = urllib.parse.urlsplit(exc.url or "").hostname
        except ValueError:
            host = None
        if host in ("gitlab.com", "codeberg.org"):
            delay = max(delay, min(120, 30 * (2 ** (attempt - 1))))
    return delay if delay <= MAX_RETRY_AFTER_SECONDS else None

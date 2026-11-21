#!/usr/bin/env python3
"""Fail-closed, offline retry scheduling policy for #497.

This module NEVER starts FFmpeg, opens a socket, or releases the 685 hold.
Only an independently reviewed sandbox acceptance can authorize future execution.
"""
from dataclasses import dataclass

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 30
MAX_DELAY_SECONDS = 120
TRANSIENT = frozenset({"TIMEOUT", "TEMPORARY_NETWORK_ERROR", "HTTP_429", "HTTP_502", "HTTP_503", "HTTP_504"})
SECURITY = frozenset({"INVALID_URL", "PRIVATE_IP", "DNS_REBIND", "REDIRECT_DENIED", "UNSAFE_HLS", "EGRESS_DENIED", "TLS_FAILURE"})

@dataclass(frozen=True)
class RetryDecision:
    action: str
    delay_seconds: int
    live_retry_authorized: bool = False

def decide(status: str, attempts_completed: int, *, sandbox_accepted: bool = False,
           hls_children_isolated: bool = False, final_test_authorized: bool = False) -> RetryDecision:
    """Plan only; never execute. Every absent acceptance signal fails closed."""
    if type(attempts_completed) is not int or not 0 <= attempts_completed <= MAX_ATTEMPTS:
        raise ValueError("Invalid retry count")
    if not isinstance(status, str):
        raise ValueError("Invalid retry status")
    if not (sandbox_accepted is True and hls_children_isolated is True
            and final_test_authorized is True):
        return RetryDecision("SECURITY_HOLD", 0)
    if status in SECURITY or status not in TRANSIENT:
        return RetryDecision("NO_RETRY", 0)
    if attempts_completed >= MAX_ATTEMPTS:
        return RetryDecision("EXHAUSTED", 0)
    # Deterministic bounded exponential backoff; no retry storm or random state.
    return RetryDecision("SCHEDULE_ONLY", min(MAX_DELAY_SECONDS, BASE_DELAY_SECONDS * 2 ** max(0, attempts_completed - 1)))

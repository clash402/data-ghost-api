from __future__ import annotations

import threading
import time
from typing import Final

from fastapi import Request


_LOCK: Final = threading.Lock()
_COUNTS: dict[tuple[str, str, int], int] = {}


class RateLimitExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded. Retry after {retry_after_seconds}s.")


def get_request_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def clear_rate_limit_state() -> None:
    with _LOCK:
        _COUNTS.clear()


def enforce_rate_limit(*, bucket: str, key: str, limit: int, window_seconds: int) -> None:
    if limit <= 0:
        return

    now = int(time.time())
    window_start = now - (now % window_seconds)
    counter_key = (bucket, key, window_start)

    with _LOCK:
        current = _COUNTS.get(counter_key, 0)
        if current >= limit:
            retry_after = max(1, window_seconds - (now - window_start))
            raise RateLimitExceededError(retry_after_seconds=retry_after)
        _COUNTS[counter_key] = current + 1

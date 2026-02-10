from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Final


_LOCK: Final = threading.Lock()
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _normalize_question(question: str) -> str:
    return " ".join(question.strip().lower().split())


def build_ask_cache_key(
    *,
    question: str,
    dataset_id: str | None,
    clarifications: dict[str, Any] | None,
) -> str:
    payload = {
        "question": _normalize_question(question),
        "dataset_id": dataset_id or "",
        "clarifications": clarifications or {},
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def clear_ask_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def get_cached_ask_response(cache_key: str) -> dict[str, Any] | None:
    now = time.time()
    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached is None:
            return None
        expires_at, payload = cached
        if expires_at <= now:
            _CACHE.pop(cache_key, None)
            return None
        return json.loads(json.dumps(payload))


def set_cached_ask_response(*, cache_key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    expires_at = time.time() + ttl_seconds
    serialized = json.loads(json.dumps(payload, default=str))
    with _LOCK:
        _CACHE[cache_key] = (expires_at, serialized)

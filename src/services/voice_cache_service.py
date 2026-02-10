from __future__ import annotations

import hashlib
import threading
import time
from typing import Final


_LOCK: Final = threading.Lock()
_CACHE: dict[str, tuple[float, bytes]] = {}


def build_voice_cache_key(
    *,
    text: str,
    voice_id: str,
    model_id: str,
    output_format: str,
) -> str:
    payload = f"{text}\n{voice_id}\n{model_id}\n{output_format}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def clear_voice_cache() -> None:
    with _LOCK:
        _CACHE.clear()


def get_cached_voice_audio(cache_key: str) -> bytes | None:
    now = time.time()
    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached is None:
            return None
        expires_at, audio_bytes = cached
        if expires_at <= now:
            _CACHE.pop(cache_key, None)
            return None
        return audio_bytes


def set_cached_voice_audio(*, cache_key: str, audio_bytes: bytes, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    expires_at = time.time() + ttl_seconds
    with _LOCK:
        _CACHE[cache_key] = (expires_at, audio_bytes)

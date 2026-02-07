from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
EMBED_SIZE = 128


def _hash_token(token: str) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % EMBED_SIZE


def embed_text(text: str) -> list[float]:
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        return [0.0] * EMBED_SIZE

    counts = Counter(tokens)
    vector = [0.0] * EMBED_SIZE
    for token, count in counts.items():
        vector[_hash_token(token)] += float(count)

    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    return float(sum(x * y for x, y in zip(a, b, strict=False)))

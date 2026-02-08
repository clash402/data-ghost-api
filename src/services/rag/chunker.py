from __future__ import annotations

from src.core.settings import get_settings


def chunk_text(text: str) -> list[str]:
    settings = get_settings()
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    size = settings.rag_chunk_size
    overlap = settings.rag_chunk_overlap

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks

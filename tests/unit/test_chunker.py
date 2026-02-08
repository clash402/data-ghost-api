from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.services.rag.chunker import chunk_text


def test_chunk_text_respects_size_and_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.services.rag.chunker.get_settings",
        lambda: SimpleNamespace(rag_chunk_size=5, rag_chunk_overlap=2),
    )

    chunks = chunk_text("abcdefghij")
    assert chunks == ["abcde", "defgh", "ghij"]


def test_chunk_text_returns_empty_for_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.services.rag.chunker.get_settings",
        lambda: SimpleNamespace(rag_chunk_size=5, rag_chunk_overlap=2),
    )

    assert chunk_text("   \n\t   ") == []

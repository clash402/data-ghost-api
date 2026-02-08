from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("context.txt", "Revenue means booked invoice amount."),
        ("context.md", "# Metric definitions\n\nRevenue excludes refunds."),
    ],
)
def test_upload_context_accepts_text_and_markdown(filename: str, content: str) -> None:
    response = client.post(
        "/upload/context",
        files={"file": (filename, content, "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == filename
    assert body["chunks"] >= 1
    assert body["doc_id"]


def test_upload_context_rejects_unsupported_file_type() -> None:
    response = client.post(
        "/upload/context",
        files={"file": ("context.json", '{"foo":"bar"}', "application/json")},
    )
    assert response.status_code == 400
    assert "unsupported context file type" in response.json()["detail"].lower()


def test_upload_context_rejects_empty_document() -> None:
    response = client.post(
        "/upload/context",
        files={"file": ("empty.txt", "   \n\t   ", "text/plain")},
    )
    assert response.status_code == 400
    assert "empty after extraction" in response.json()["detail"].lower()

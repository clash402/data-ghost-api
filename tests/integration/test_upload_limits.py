from __future__ import annotations

from fastapi.testclient import TestClient

from src.core.settings import get_settings
from src.main import app

client = TestClient(app)


def test_dataset_upload_rejects_oversized_file_with_413(monkeypatch) -> None:
    monkeypatch.setenv("DATASET_MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()

    oversized = b"a" * (1024 * 1024 + 1)
    response = client.post(
        "/upload/dataset",
        files={"file": ("sample.csv", oversized, "text/csv")},
    )
    assert response.status_code == 413
    assert "size limit" in response.json()["detail"].lower()


def test_context_upload_rejects_oversized_file_with_413(monkeypatch) -> None:
    monkeypatch.setenv("CONTEXT_MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()

    oversized = b"a" * (1024 * 1024 + 1)
    response = client.post(
        "/upload/context",
        files={"file": ("context.txt", oversized, "text/plain")},
    )
    assert response.status_code == 413
    assert "size limit" in response.json()["detail"].lower()


def test_dataset_upload_rejects_when_row_count_exceeds_limit(monkeypatch) -> None:
    monkeypatch.setenv("DATASET_MAX_ROWS", "1")
    get_settings.cache_clear()

    csv_content = "date,revenue\n2025-01-01,100\n2025-01-02,120\n"
    response = client.post(
        "/upload/dataset",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 400
    assert "maximum row count" in response.json()["detail"].lower()


def test_dataset_upload_rejects_when_column_count_exceeds_limit(monkeypatch) -> None:
    monkeypatch.setenv("DATASET_MAX_COLUMNS", "2")
    get_settings.cache_clear()

    csv_content = "date,revenue,segment\n2025-01-01,100,A\n"
    response = client.post(
        "/upload/dataset",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 400
    assert "maximum column count" in response.json()["detail"].lower()

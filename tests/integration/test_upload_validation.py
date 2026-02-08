from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_upload_dataset_rejects_non_csv_file() -> None:
    response = client.post(
        "/upload/dataset",
        files={"file": ("dataset.txt", "a,b\n1,2\n", "text/plain")},
    )
    assert response.status_code == 400
    assert "CSV" in response.json()["detail"]


def test_upload_dataset_rejects_missing_header() -> None:
    response = client.post(
        "/upload/dataset",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400
    assert "missing header" in response.json()["detail"].lower()


def test_upload_dataset_rejects_csv_without_rows() -> None:
    response = client.post(
        "/upload/dataset",
        files={"file": ("headers_only.csv", "date,revenue\n", "text/csv")},
    )
    assert response.status_code == 400
    assert "no data rows" in response.json()["detail"].lower()

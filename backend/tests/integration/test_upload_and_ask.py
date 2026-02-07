from fastapi.testclient import TestClient

from backend.src.main import app


client = TestClient(app)


def test_upload_dataset_then_ask_returns_sql() -> None:
    csv_content = "date,segment,revenue\n2025-01-01,A,100\n2025-01-02,A,120\n2025-01-08,A,90\n2025-01-09,B,140\n"
    upload = client.post(
        "/upload/dataset",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )

    assert upload.status_code == 200
    payload = upload.json()
    assert payload["rows"] == 4

    ask = client.post(
        "/ask",
        json={"question": "Why did revenue change last week?"},
    )

    assert ask.status_code == 200
    body = ask.json()
    assert body["needs_clarification"] is False
    assert body["answer"] is not None
    assert len(body["answer"]["sql"]) > 0
    assert "confidence" in body["answer"]
    assert "cost" in body["answer"]

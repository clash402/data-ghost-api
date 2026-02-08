from fastapi.testclient import TestClient

from backend.src.db.session import get_connection
from backend.src.main import app


client = TestClient(app)


def _reset_dataset_state() -> None:
    with get_connection() as conn:
        tables = conn.execute("SELECT table_name FROM dataset_meta").fetchall()
        for table in tables:
            conn.execute(f'DROP TABLE IF EXISTS "{table["table_name"]}"')
        conn.execute("DELETE FROM dataset_meta")


def test_upload_dataset_then_ask_returns_sql() -> None:
    _reset_dataset_state()
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

    ask_common = client.post(
        "/ask",
        json={"question": "What is the most common segment in the dataset?"},
    )

    assert ask_common.status_code == 200
    common_body = ask_common.json()
    assert common_body["answer"] is not None
    assert len(common_body["answer"]["sql"]) > 0
    assert "common" in common_body["answer"]["sql"][0]["label"].lower()


def test_dataset_summary_returns_not_ready_when_empty() -> None:
    _reset_dataset_state()
    response = client.get("/dataset/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["dataset_uploaded"] is False
    assert "message" in body

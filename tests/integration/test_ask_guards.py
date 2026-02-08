from __future__ import annotations

import json

from fastapi.testclient import TestClient

from src.db.session import get_connection
from src.main import app


client = TestClient(app)


def _upload_ambiguous_dataset() -> None:
    csv_content = (
        "order_date,event_date,revenue,profit,segment\n"
        "2025-01-01,2025-01-02,100,25,A\n"
        "2025-01-08,2025-01-09,80,20,A\n"
        "2025-01-15,2025-01-16,90,24,B\n"
    )
    response = client.post(
        "/upload/dataset",
        files={"file": ("ambiguous.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200


def test_ask_without_dataset_returns_dataset_required_and_logs_request() -> None:
    response = client.post("/ask", json={"question": "Why did revenue drop last week?"})
    assert response.status_code == 200

    body = response.json()
    assert body["needs_clarification"] is False
    assert body["answer"] is not None
    assert body["answer"]["headline"] == "Dataset required"
    assert body["answer"]["sql"] == []

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT question, status, models_json, response_json
            FROM requests
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert row["question"] == "Why did revenue drop last week?"
    assert row["status"] == "completed"
    assert len(json.loads(row["models_json"])) >= 1

    logged_response = json.loads(row["response_json"])
    assert logged_response["needs_clarification"] is False
    assert logged_response["answer"]["headline"] == "Dataset required"


def test_ask_ambiguous_question_requests_metric_and_time_clarifications() -> None:
    _upload_ambiguous_dataset()
    response = client.post("/ask", json={"question": "Why did performance change last week?"})
    assert response.status_code == 200

    body = response.json()
    assert body["needs_clarification"] is True
    assert body["answer"] is None

    questions = {item["key"]: item for item in body["clarification_questions"]}
    assert "metric" in questions
    assert "time_column" in questions
    assert set(questions["metric"]["options"]) >= {"revenue", "profit"}
    assert set(questions["time_column"]["options"]) >= {"order_date", "event_date"}

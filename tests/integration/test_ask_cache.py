from __future__ import annotations

from fastapi.testclient import TestClient

from src.db.session import get_connection
from src.main import app

client = TestClient(app)


def test_repeat_ask_uses_cache_and_skips_additional_llm_cost() -> None:
    csv_content = "date,revenue\n2025-01-01,100\n2025-01-02,120\n"
    upload = client.post(
        "/upload/dataset",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    assert upload.status_code == 200

    first = client.post("/ask", json={"question": "How many rows are in this dataset?"})
    assert first.status_code == 200

    with get_connection() as conn:
        first_cost_rows = conn.execute("SELECT COUNT(*) AS count FROM cost_ledger").fetchone()
    assert first_cost_rows is not None
    first_count = first_cost_rows["count"]
    assert first_count > 0

    second = client.post("/ask", json={"question": "How many rows are in this dataset?"})
    assert second.status_code == 200
    assert second.json() == first.json()

    with get_connection() as conn:
        second_cost_rows = conn.execute("SELECT COUNT(*) AS count FROM cost_ledger").fetchone()
    assert second_cost_rows is not None
    assert second_cost_rows["count"] == first_count

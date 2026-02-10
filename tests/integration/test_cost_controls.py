from __future__ import annotations

from fastapi.testclient import TestClient

from src.core.settings import get_settings
from src.main import app

client = TestClient(app)


def _upload_simple_dataset() -> None:
    csv_content = "date,revenue\n2025-01-01,100\n2025-01-02,120\n"
    response = client.post(
        "/upload/dataset",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200


def test_ask_returns_429_when_request_budget_would_be_exceeded(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MAX_USD_PER_REQUEST", "0.00000001")
    monkeypatch.setenv("LLM_MAX_USD_PER_DAY", "10")
    get_settings.cache_clear()

    _upload_simple_dataset()

    response = client.post("/ask", json={"question": "How many rows are in this dataset?"})
    assert response.status_code == 429
    assert "per-request budget exceeded" in response.json()["detail"].lower()


def test_ask_returns_429_when_daily_budget_would_be_exceeded(monkeypatch) -> None:
    monkeypatch.setenv("LLM_MAX_USD_PER_REQUEST", "10")
    monkeypatch.setenv("LLM_MAX_USD_PER_DAY", "0.00000001")
    get_settings.cache_clear()

    _upload_simple_dataset()

    response = client.post("/ask", json={"question": "How many rows are in this dataset?"})
    assert response.status_code == 429
    assert "daily budget exceeded" in response.json()["detail"].lower()


def test_ask_returns_503_when_llm_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "false")
    get_settings.cache_clear()

    _upload_simple_dataset()

    response = client.post("/ask", json={"question": "How many rows are in this dataset?"})
    assert response.status_code == 503
    assert "llm calls are disabled" in response.json()["detail"].lower()

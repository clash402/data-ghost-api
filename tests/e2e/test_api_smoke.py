from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
import pytest

from src.db.session import get_connection


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, process: subprocess.Popen[str], timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None

    while time.time() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=1)
            raise RuntimeError(
                f"uvicorn exited early with code {process.returncode}\nstdout:\n{stdout}\nstderr:\n{stderr}"
            )

        try:
            response = httpx.get(f"{base_url}/health", timeout=0.5)
            if response.status_code == 200:
                return
        except Exception as exc:  # pragma: no cover - best effort capture for startup loops
            last_error = exc

        time.sleep(0.1)

    raise RuntimeError(f"Timed out waiting for API server to start. Last error: {last_error}")


@pytest.fixture
def live_server() -> str:
    try:
        port = _find_free_port()
    except PermissionError:
        pytest.skip("Socket binding is not permitted in this environment.")
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)

    process: subprocess.Popen[str] = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    _wait_for_server(base_url, process)
    try:
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_health_and_root_contract(live_server: str) -> None:
    health = httpx.get(f"{live_server}/health", headers={"X-Request-Id": "e2e-health"}, timeout=5)
    assert health.status_code == 200
    assert health.headers["x-request-id"] == "e2e-health"

    health_body = health.json()
    assert health_body["status"] == "ok"
    assert health_body["app"] == "data-ghost-api"

    root = httpx.get(f"{live_server}/", timeout=5)
    assert root.status_code == 200
    assert root.json() == {"message": "Data Ghost API"}


def test_full_journey_upload_ask_and_summary(live_server: str) -> None:
    csv_content = "date,segment,revenue\n2025-01-01,A,100\n2025-01-02,A,120\n2025-01-08,B,80\n"

    upload = httpx.post(
        f"{live_server}/upload/dataset",
        files={"file": ("smoke.csv", csv_content, "text/csv")},
        timeout=10,
    )
    assert upload.status_code == 200
    assert "x-request-id" in upload.headers

    ask = httpx.post(
        f"{live_server}/ask",
        json={"question": "Why did revenue change last week?"},
        timeout=10,
    )
    assert ask.status_code == 200
    ask_body = ask.json()
    assert ask_body["needs_clarification"] is False
    assert ask_body["answer"] is not None
    assert len(ask_body["answer"]["sql"]) > 0

    summary = httpx.get(f"{live_server}/dataset/summary", timeout=5)
    assert summary.status_code == 200
    summary_body = summary.json()
    assert summary_body["dataset_uploaded"] is True
    assert summary_body["rows"] == 3

    with get_connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS count FROM requests").fetchone()["count"]
    assert count >= 1


def test_clarification_flow_with_followup_answer(live_server: str) -> None:
    csv_content = (
        "order_date,event_date,revenue,profit,segment\n"
        "2025-01-01,2025-01-02,100,25,A\n"
        "2025-01-08,2025-01-09,80,20,A\n"
        "2025-01-15,2025-01-16,90,24,B\n"
    )
    upload = httpx.post(
        f"{live_server}/upload/dataset",
        files={"file": ("clarify.csv", csv_content, "text/csv")},
        timeout=10,
    )
    assert upload.status_code == 200

    first_ask = httpx.post(
        f"{live_server}/ask",
        json={"question": "Why did performance change last week?"},
        timeout=10,
    )
    assert first_ask.status_code == 200

    first_body = first_ask.json()
    assert first_body["needs_clarification"] is True
    assert first_body["answer"] is None
    keys = {item["key"] for item in first_body["clarification_questions"]}
    assert {"metric", "time_column"}.issubset(keys)

    follow_up = httpx.post(
        f"{live_server}/ask",
        json={
            "question": "Why did performance change last week?",
            "conversation_id": first_body["conversation_id"],
            "clarifications": {"metric": "revenue", "time_column": "order_date"},
        },
        timeout=10,
    )
    assert follow_up.status_code == 200

    follow_up_body = follow_up.json()
    assert follow_up_body["conversation_id"] == first_body["conversation_id"]
    assert follow_up_body["needs_clarification"] is False
    assert follow_up_body["answer"] is not None
    assert len(follow_up_body["answer"]["sql"]) > 0

from __future__ import annotations

from contextlib import contextmanager
import sqlite3

import pytest

from src.services.sql.executor import (
    SqlExecutionError,
    _enforce_limit,
    execute_query_plan,
    execute_safe_query,
)


def test_enforce_limit_adds_limit_when_missing() -> None:
    sql = "SELECT 1"
    assert _enforce_limit(sql, 25) == "SELECT 1 LIMIT 25"


def test_enforce_limit_keeps_existing_limit() -> None:
    sql = "SELECT 1 LIMIT 5"
    assert _enforce_limit(sql, 25) == "SELECT 1 LIMIT 5"


def test_execute_query_plan_enforces_budget() -> None:
    plan = [{"sql": "SELECT 1"} for _ in range(11)]
    with pytest.raises(SqlExecutionError, match="Query budget exceeded"):
        execute_query_plan(plan)


def test_execute_safe_query_maps_interrupted_to_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    class _InterruptedConnection:
        def set_progress_handler(self, *_args, **_kwargs) -> None:
            return None

        def execute(self, _sql: str):
            raise sqlite3.OperationalError("interrupted")

    @contextmanager
    def _fake_connection():
        yield _InterruptedConnection()

    monkeypatch.setattr("src.services.sql.executor.get_connection", _fake_connection)

    with pytest.raises(SqlExecutionError, match="Query timed out"):
        execute_safe_query("SELECT 1")

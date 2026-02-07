from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from backend.src.core.settings import get_settings
from backend.src.db.session import get_connection
from backend.src.services.sql.validator import validate_safe_select


@dataclass
class QueryExecution:
    sql: str
    rows: list[dict[str, Any]]


class SqlExecutionError(Exception):
    pass


def _enforce_limit(sql: str, limit: int) -> str:
    cleaned = sql.strip().rstrip(";")
    if "LIMIT" in cleaned.upper():
        return cleaned
    return f"{cleaned} LIMIT {limit}"


def execute_safe_query(sql: str) -> list[dict[str, Any]]:
    settings = get_settings()
    validation = validate_safe_select(sql)
    if not validation.is_valid:
        raise SqlExecutionError(validation.reason or "Unsafe SQL")

    bounded_sql = _enforce_limit(sql, settings.query_max_rows)

    with get_connection() as conn:
        start = time.monotonic()

        def progress_handler() -> int:
            elapsed = time.monotonic() - start
            if elapsed > settings.query_timeout_seconds:
                return 1
            return 0

        conn.set_progress_handler(progress_handler, 1000)
        try:
            cursor = conn.execute(bounded_sql)
            rows = cursor.fetchall()
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc).lower():
                raise SqlExecutionError("Query timed out") from exc
            raise SqlExecutionError(str(exc)) from exc
        finally:
            conn.set_progress_handler(None, 0)

    return [dict(row) for row in rows]


def execute_query_plan(plan: list[dict[str, str]]) -> list[QueryExecution]:
    settings = get_settings()
    if len(plan) > settings.query_max_per_request:
        raise SqlExecutionError("Query budget exceeded")

    output: list[QueryExecution] = []
    for item in plan:
        sql = item["sql"]
        rows = execute_safe_query(sql)
        output.append(QueryExecution(sql=sql, rows=rows))
    return output

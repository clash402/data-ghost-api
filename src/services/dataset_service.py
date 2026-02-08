from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.db.session import get_connection
from src.storage.repositories import get_dataset_meta, upsert_dataset_meta
from src.utils.strings import slugify_identifier
from src.utils.time import utc_now_iso


@dataclass
class DatasetSummary:
    dataset_id: str
    name: str
    table_name: str
    rows: int
    columns: list[str]
    schema: dict[str, str]
    sample_rows: list[dict[str, Any]]
    created_at: datetime


def _infer_column_type(values: list[str]) -> str:
    non_empty = [v for v in values if v not in ("", None)]
    if not non_empty:
        return "TEXT"

    is_int = True
    is_float = True
    for value in non_empty:
        try:
            int(value)
        except ValueError:
            is_int = False

        try:
            float(value)
        except ValueError:
            is_float = False

    if is_int:
        return "INTEGER"
    if is_float:
        return "REAL"
    return "TEXT"


def _dedupe_columns(columns: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    output: list[str] = []
    for column in columns:
        count = seen.get(column, 0)
        if count == 0:
            output.append(column)
        else:
            output.append(f"{column}_{count + 1}")
        seen[column] = count + 1
    return output


def _normalize_row(row: dict[str, str], schema: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        value = value.strip() if isinstance(value, str) else value
        if value == "":
            normalized[key] = None
            continue

        kind = schema[key]
        if kind == "INTEGER":
            normalized[key] = int(value)
        elif kind == "REAL":
            normalized[key] = float(value)
        else:
            normalized[key] = value
    return normalized


def ingest_csv(filename: str, content: bytes) -> DatasetSummary:
    decoded = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    if reader.fieldnames is None:
        raise ValueError("CSV is missing header row")

    columns = _dedupe_columns([slugify_identifier(name) for name in reader.fieldnames])
    header_mapping = dict(zip(reader.fieldnames, columns, strict=False))

    raw_rows: list[dict[str, str]] = []
    for row in reader:
        mapped = {header_mapping[k]: (v or "") for k, v in row.items() if k is not None}
        raw_rows.append(mapped)

    if not raw_rows:
        raise ValueError("CSV has no data rows")

    values_by_column = {col: [row.get(col, "") for row in raw_rows] for col in columns}
    schema = {col: _infer_column_type(values) for col, values in values_by_column.items()}
    normalized_rows = [_normalize_row(row, schema) for row in raw_rows]

    dataset_id = str(uuid.uuid4())
    table_name = f"data_{dataset_id.replace('-', '')[:12]}"

    previous = get_dataset_meta()
    with get_connection() as conn:
        if previous:
            conn.execute(f'DROP TABLE IF EXISTS "{previous["table_name"]}"')

        column_ddl = ", ".join(f'"{col}" {kind}' for col, kind in schema.items())
        conn.execute(f'CREATE TABLE "{table_name}" ({column_ddl})')

        placeholders = ", ".join("?" for _ in columns)
        insert_sql = f'INSERT INTO "{table_name}" ({", ".join(f"\"{c}\"" for c in columns)}) VALUES ({placeholders})'
        conn.executemany(insert_sql, ([row.get(col) for col in columns] for row in normalized_rows))

    created_at = utc_now_iso()
    upsert_dataset_meta(
        dataset_id=dataset_id,
        name=filename,
        table_name=table_name,
        rows=len(normalized_rows),
        columns=columns,
        schema=schema,
        created_at=created_at,
    )

    return DatasetSummary(
        dataset_id=dataset_id,
        name=filename,
        table_name=table_name,
        rows=len(normalized_rows),
        columns=columns,
        schema=schema,
        sample_rows=normalized_rows[:5],
        created_at=datetime.fromisoformat(created_at),
    )


def get_dataset_summary() -> DatasetSummary:
    meta = get_dataset_meta()
    if meta is None:
        raise ValueError("No dataset uploaded")

    with get_connection() as conn:
        rows = conn.execute(f'SELECT * FROM "{meta["table_name"]}" LIMIT 5').fetchall()

    sample_rows = [dict(row) for row in rows]
    return DatasetSummary(
        dataset_id=meta["dataset_id"],
        name=meta["name"],
        table_name=meta["table_name"],
        rows=meta["rows"],
        columns=meta["columns"],
        schema=meta["schema"],
        sample_rows=sample_rows,
        created_at=meta["created_at"],
    )

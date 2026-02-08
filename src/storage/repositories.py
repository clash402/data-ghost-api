from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from src.db.session import get_connection


def upsert_dataset_meta(
    dataset_id: str,
    name: str,
    table_name: str,
    rows: int,
    columns: list[str],
    schema: dict[str, str],
    created_at: str,
) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM dataset_meta")
        conn.execute(
            """
            INSERT INTO dataset_meta(dataset_id, name, table_name, rows, columns_json, schema_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                name,
                table_name,
                rows,
                json.dumps(columns),
                json.dumps(schema),
                created_at,
            ),
        )


def get_dataset_meta() -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT dataset_id, name, table_name, rows, columns_json, schema_json, created_at FROM dataset_meta LIMIT 1"
        ).fetchone()
        if row is None:
            return None

        return {
            "dataset_id": row["dataset_id"],
            "name": row["name"],
            "table_name": row["table_name"],
            "rows": row["rows"],
            "columns": json.loads(row["columns_json"]),
            "schema": json.loads(row["schema_json"]),
            "created_at": datetime.fromisoformat(row["created_at"]),
        }


def insert_docs_meta(doc_id: str, filename: str, content_type: str | None, chunks: int, created_at: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO docs_meta(doc_id, filename, content_type, chunks, created_at)
            VALUES(?, ?, ?, ?, ?)
            """,
            (doc_id, filename, content_type, chunks, created_at),
        )


def insert_vector_chunk(
    doc_id: str,
    chunk_index: int,
    content: str,
    embedding: list[float],
    created_at: str,
) -> str:
    chunk_id = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO vector_chunks(chunk_id, doc_id, chunk_index, content, embedding_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (chunk_id, doc_id, chunk_index, content, json.dumps(embedding), created_at),
        )
    return chunk_id


def list_vector_chunks() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT vc.chunk_id, vc.doc_id, vc.chunk_index, vc.content, vc.embedding_json, dm.filename
            FROM vector_chunks vc
            JOIN docs_meta dm ON dm.doc_id = vc.doc_id
            ORDER BY vc.created_at DESC
            """
        ).fetchall()

    return [
        {
            "chunk_id": row["chunk_id"],
            "doc_id": row["doc_id"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "embedding": json.loads(row["embedding_json"]),
            "filename": row["filename"],
        }
        for row in rows
    ]


def insert_request_log(
    request_id: str,
    conversation_id: str,
    question: str,
    models: list[str],
    prompt_tokens: int,
    completion_tokens: int,
    usd_cost: float,
    status: str,
    diagnostics: list[dict[str, Any]],
    response: dict[str, Any] | None,
    created_at: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO requests(
                request_id,
                conversation_id,
                question,
                models_json,
                prompt_tokens,
                completion_tokens,
                usd_cost,
                status,
                diagnostics_json,
                response_json,
                created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                conversation_id,
                question,
                json.dumps(models),
                prompt_tokens,
                completion_tokens,
                usd_cost,
                status,
                json.dumps(diagnostics),
                json.dumps(response) if response is not None else None,
                created_at,
            ),
        )


def insert_cost_ledger(
    ledger_id: str,
    request_id: str | None,
    app: str,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    usd: float,
    created_at: str,
    metadata: dict[str, Any],
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO cost_ledger(
                id, request_id, app, provider, model, prompt_tokens,
                completion_tokens, usd, created_at, metadata_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ledger_id,
                request_id,
                app,
                provider,
                model,
                prompt_tokens,
                completion_tokens,
                usd,
                created_at,
                json.dumps(metadata),
            ),
        )

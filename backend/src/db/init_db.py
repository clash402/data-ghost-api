from __future__ import annotations

from backend.src.db.session import get_connection


DDL = [
    """
    CREATE TABLE IF NOT EXISTS dataset_meta (
        dataset_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        table_name TEXT NOT NULL,
        rows INTEGER NOT NULL,
        columns_json TEXT NOT NULL,
        schema_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS docs_meta (
        doc_id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        content_type TEXT,
        chunks INTEGER NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS vector_chunks (
        chunk_id TEXT PRIMARY KEY,
        doc_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (doc_id) REFERENCES docs_meta(doc_id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS requests (
        request_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        question TEXT NOT NULL,
        models_json TEXT NOT NULL,
        prompt_tokens INTEGER NOT NULL,
        completion_tokens INTEGER NOT NULL,
        usd_cost REAL NOT NULL,
        status TEXT NOT NULL,
        diagnostics_json TEXT NOT NULL,
        response_json TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cost_ledger (
        id TEXT PRIMARY KEY,
        request_id TEXT,
        app TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT NOT NULL,
        prompt_tokens INTEGER NOT NULL,
        completion_tokens INTEGER NOT NULL,
        usd REAL NOT NULL,
        created_at TEXT NOT NULL,
        metadata_json TEXT NOT NULL
    )
    """,
]


def init_db() -> None:
    with get_connection() as conn:
        for ddl in DDL:
            conn.execute(ddl)

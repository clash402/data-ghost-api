from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from backend.src.core.settings import get_settings


def _configure_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    settings = get_settings()
    conn = sqlite3.connect(Path(settings.db_path))
    _configure_connection(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_connection_no_context() -> sqlite3.Connection:
    settings = get_settings()
    conn = sqlite3.connect(Path(settings.db_path))
    _configure_connection(conn)
    return conn

from __future__ import annotations

import os
from pathlib import Path
import tempfile

import pytest

# Force deterministic offline behavior for all tests before app modules import settings.
_RUNTIME_DIR = Path(tempfile.gettempdir()) / f"data_ghost_api_pytest_{os.getpid()}"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["LLM_DEFAULT_MODEL"] = "mock-default"
os.environ["LLM_CHEAP_MODEL"] = "mock-cheap"
os.environ["LLM_EXPENSIVE_MODEL"] = "mock-expensive"
os.environ["DATA_DIR"] = str(_RUNTIME_DIR / "data")
os.environ["DOCS_DIR"] = str(_RUNTIME_DIR / "docs")
os.environ["DB_PATH"] = str(_RUNTIME_DIR / "data_ghost_test.db")


@pytest.fixture(scope="session", autouse=True)
def _init_test_environment() -> None:
    from src.core.settings import get_settings
    from src.db.init_db import init_db

    _RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    get_settings.cache_clear()
    init_db()


@pytest.fixture(autouse=True)
def _reset_database_state() -> None:
    from src.db.session import get_connection

    with get_connection() as conn:
        dataset_tables = conn.execute("SELECT table_name FROM dataset_meta").fetchall()
        for row in dataset_tables:
            conn.execute(f'DROP TABLE IF EXISTS "{row["table_name"]}"')

        conn.execute("DELETE FROM vector_chunks")
        conn.execute("DELETE FROM docs_meta")
        conn.execute("DELETE FROM requests")
        conn.execute("DELETE FROM cost_ledger")
        conn.execute("DELETE FROM dataset_meta")

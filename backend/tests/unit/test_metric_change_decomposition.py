import sqlite3

from backend.src.services.analytics.patterns.metric_change_decomposition import (
    build_metric_change_decomposition,
)


def test_metric_change_decomposition_query_executes() -> None:
    plan = build_metric_change_decomposition(
        table_name="dataset",
        columns=["date", "segment", "revenue"],
        schema={"date": "TEXT", "segment": "TEXT", "revenue": "REAL"},
        intent={"metric": "revenue", "time_column": "date", "top_n": 3},
    )

    assert len(plan.queries) == 1
    sql = plan.queries[0]["query"]

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE dataset (date TEXT, segment TEXT, revenue REAL)")
    conn.executemany(
        "INSERT INTO dataset(date, segment, revenue) VALUES (?, ?, ?)",
        [
            ("2025-01-01", "A", 10),
            ("2025-01-02", "A", 10),
            ("2025-01-08", "A", 20),
            ("2025-01-09", "A", 20),
            ("2025-01-01", "B", 50),
            ("2025-01-08", "B", 40),
        ],
    )

    rows = conn.execute(sql).fetchall()
    assert len(rows) > 0
    assert "segment" in rows[0].keys()
    assert "contribution" in rows[0].keys()

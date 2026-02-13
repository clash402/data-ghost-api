from __future__ import annotations

from src.services.dataset_service import ingest_csv


def test_ingest_csv_normalizes_and_dedupes_dirty_headers() -> None:
    csv_content = ("Revenue $,Revenue $, User Name \n" "1,2,Alice\n" "3,, Bob \n").encode("utf-8")

    summary = ingest_csv("dirty_headers.csv", csv_content)

    assert summary.columns == ["revenue", "revenue_2", "user_name"]
    assert summary.schema == {"revenue": "INTEGER", "revenue_2": "INTEGER", "user_name": "TEXT"}
    assert summary.sample_rows[0]["revenue"] == 1
    assert summary.sample_rows[1]["revenue_2"] is None
    assert summary.sample_rows[1]["user_name"] == "Bob"


def test_ingest_csv_infers_types_and_converts_blanks_to_null() -> None:
    csv_content = ("amount,ratio\n" "10,1.5\n" ",2.0\n").encode("utf-8")

    summary = ingest_csv("types.csv", csv_content)

    assert summary.schema["amount"] == "INTEGER"
    assert summary.schema["ratio"] == "REAL"
    assert summary.sample_rows[0]["amount"] == 10
    assert summary.sample_rows[0]["ratio"] == 1.5
    assert summary.sample_rows[1]["amount"] is None
    assert summary.sample_rows[1]["ratio"] == 2.0

from backend.src.services.analytics.dynamic_planner import build_heuristic_queries
from backend.src.services.sql.validator import validate_safe_select


def test_most_common_text_column_uses_frequency_query() -> None:
    dataset_meta = {
        "table_name": "dataset",
        "columns": ["name", "job", "age"],
        "schema": {"name": "TEXT", "job": "TEXT", "age": "INTEGER"},
    }

    planned = build_heuristic_queries("What is the most common job in the dataset?", dataset_meta)

    assert len(planned) == 1
    query = planned[0]
    assert query["pattern"] == "heuristic_frequency"
    assert '"job"' in query["sql"]

    validation = validate_safe_select(query["sql"])
    assert validation.is_valid is True

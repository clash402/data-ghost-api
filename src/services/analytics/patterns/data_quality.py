from __future__ import annotations

from src.services.analytics.helpers import pick_time_column
from src.services.analytics.patterns.types import PatternPlan


def build_data_quality_checks(
    table_name: str,
    columns: list[str],
    schema: dict[str, str],
    intent: dict,
) -> PatternPlan:
    plan = PatternPlan(name="data_quality_checks")

    missing_terms = []
    for column in columns:
        if schema.get(column) == "TEXT":
            missing_terms.append(
                f'SUM(CASE WHEN "{column}" IS NULL OR TRIM("{column}") = \"\" THEN 1 ELSE 0 END) AS missing_{column}'
            )
        else:
            missing_terms.append(f'SUM(CASE WHEN "{column}" IS NULL THEN 1 ELSE 0 END) AS missing_{column}')

    if not missing_terms:
        plan.diagnostics.append({"code": "EMPTY_SCHEMA", "message": "No columns available for quality checks"})
        return plan

    summary_sql = f'''
SELECT
  COUNT(*) AS total_rows,
  {', '.join(missing_terms)}
FROM "{table_name}"
'''.strip()

    plan.queries.append({"label": "Data quality missingness", "query": summary_sql})

    if len(columns) >= 2:
        duplicate_sql = f'''
SELECT
  "{columns[0]}" AS key_1,
  "{columns[1]}" AS key_2,
  COUNT(*) AS duplicate_count
FROM "{table_name}"
GROUP BY "{columns[0]}", "{columns[1]}"
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC
LIMIT 20
'''.strip()
        plan.queries.append({"label": "Data quality duplicate keys", "query": duplicate_sql})

    time_col = pick_time_column(columns)
    if time_col:
        coverage_sql = f'''
SELECT
  MIN(DATE("{time_col}")) AS min_date,
  MAX(DATE("{time_col}")) AS max_date,
  COUNT(DISTINCT DATE("{time_col}")) AS distinct_days
FROM "{table_name}"
'''.strip()
        plan.queries.append({"label": "Data quality time coverage", "query": coverage_sql})

    return plan

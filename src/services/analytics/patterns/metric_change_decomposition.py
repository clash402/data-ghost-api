from __future__ import annotations

from src.services.analytics.helpers import infer_top_n, pick_dimension_columns, pick_metric_column, pick_time_column
from src.services.analytics.patterns.types import PatternPlan


def build_metric_change_decomposition(
    table_name: str,
    columns: list[str],
    schema: dict[str, str],
    intent: dict,
) -> PatternPlan:
    metric = pick_metric_column(schema, intent.get("metric"))
    time_col = pick_time_column(columns, intent.get("time_column"))
    dimensions = pick_dimension_columns(schema, exclude={time_col} if time_col else set())
    top_n = infer_top_n(intent)

    plan = PatternPlan(name="metric_change_decomposition")
    if not metric:
        plan.diagnostics.append({"code": "MISSING_METRIC", "message": "No numeric metric column found"})
        return plan
    if not time_col:
        plan.diagnostics.append({"code": "MISSING_TIME_COLUMN", "message": "No time-like column found"})
        return plan
    if not dimensions:
        plan.diagnostics.append({"code": "MISSING_DIMENSION", "message": "No segment dimension available"})
        return plan

    dimension = dimensions[0]
    sql = f'''
WITH max_date AS (
  SELECT MAX(DATE("{time_col}")) AS max_dt FROM "{table_name}"
),
windowed AS (
  SELECT
    COALESCE(CAST("{dimension}" AS TEXT), '(unknown)') AS segment,
    CASE
      WHEN DATE("{time_col}") > DATE((SELECT max_dt FROM max_date), '-6 day') THEN 'current'
      WHEN DATE("{time_col}") > DATE((SELECT max_dt FROM max_date), '-13 day') THEN 'prior'
      ELSE NULL
    END AS period,
    SUM(CAST("{metric}" AS REAL)) AS metric_sum
  FROM "{table_name}"
  WHERE DATE("{time_col}") > DATE((SELECT max_dt FROM max_date), '-13 day')
  GROUP BY segment, period
),
pivoted AS (
  SELECT
    segment,
    SUM(CASE WHEN period = 'current' THEN metric_sum ELSE 0 END) AS current_value,
    SUM(CASE WHEN period = 'prior' THEN metric_sum ELSE 0 END) AS prior_value
  FROM windowed
  GROUP BY segment
)
SELECT
  segment,
  current_value,
  prior_value,
  (current_value - prior_value) AS contribution
FROM pivoted
ORDER BY ABS(contribution) DESC
LIMIT {top_n}
'''.strip()

    plan.queries.append(
        {
            "label": "Metric change decomposition",
            "query": sql,
        }
    )
    return plan

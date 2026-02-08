from __future__ import annotations

from src.services.analytics.helpers import infer_top_n, pick_dimension_columns, pick_metric_column, pick_time_column
from src.services.analytics.patterns.types import PatternPlan


def build_segment_contribution(
    table_name: str,
    columns: list[str],
    schema: dict[str, str],
    intent: dict,
) -> PatternPlan:
    metric = pick_metric_column(schema, intent.get("metric"))
    time_col = pick_time_column(columns, intent.get("time_column"))
    dimensions = pick_dimension_columns(schema, exclude={time_col} if time_col else set())
    top_n = infer_top_n(intent)

    plan = PatternPlan(name="segment_contribution")
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
seg AS (
  SELECT
    segment,
    SUM(CASE WHEN period = 'current' THEN metric_sum ELSE 0 END) AS current_value,
    SUM(CASE WHEN period = 'prior' THEN metric_sum ELSE 0 END) AS prior_value,
    SUM(CASE WHEN period = 'current' THEN metric_sum ELSE 0 END) - SUM(CASE WHEN period = 'prior' THEN metric_sum ELSE 0 END) AS delta
  FROM windowed
  GROUP BY segment
),
tot AS (
  SELECT SUM(delta) AS total_delta FROM seg
)
SELECT
  seg.segment,
  seg.delta,
  CASE
    WHEN tot.total_delta = 0 OR tot.total_delta IS NULL THEN 0
    ELSE seg.delta / tot.total_delta
  END AS contribution_share
FROM seg, tot
ORDER BY ABS(seg.delta) DESC
LIMIT {top_n}
'''.strip()

    plan.queries.append(
        {
            "label": "Segment contribution analysis",
            "query": sql,
        }
    )
    return plan

from __future__ import annotations

from src.services.analytics.helpers import pick_metric_column, pick_time_column
from src.services.analytics.patterns.types import PatternPlan


def build_trend_break_detection(
    table_name: str,
    columns: list[str],
    schema: dict[str, str],
    intent: dict,
) -> PatternPlan:
    metric = pick_metric_column(schema, intent.get("metric"))
    time_col = pick_time_column(columns, intent.get("time_column"))

    plan = PatternPlan(name="trend_break_detection")
    if not metric:
        plan.diagnostics.append(
            {"code": "MISSING_METRIC", "message": "No numeric metric column found"}
        )
        return plan
    if not time_col:
        plan.diagnostics.append(
            {"code": "MISSING_TIME_COLUMN", "message": "No time-like column found"}
        )
        return plan

    signal_sql = f"""
WITH daily AS (
  SELECT DATE("{time_col}") AS dt, SUM(CAST("{metric}" AS REAL)) AS metric_value
  FROM "{table_name}"
  GROUP BY dt
),
ranked AS (
  SELECT dt, metric_value, ROW_NUMBER() OVER (ORDER BY dt DESC) AS rn
  FROM daily
),
recent AS (
  SELECT metric_value FROM ranked WHERE rn <= 7
),
baseline AS (
  SELECT metric_value FROM ranked WHERE rn > 7 AND rn <= 28
)
SELECT
  (SELECT AVG(metric_value) FROM recent) AS recent_avg,
  (SELECT AVG(metric_value) FROM baseline) AS baseline_avg,
  (SELECT AVG(metric_value) FROM recent) - (SELECT AVG(metric_value) FROM baseline) AS avg_delta,
  CASE
    WHEN (SELECT AVG(metric_value) FROM baseline) IS NULL THEN 'insufficient'
    WHEN ABS((SELECT AVG(metric_value) FROM recent) - (SELECT AVG(metric_value) FROM baseline)) >= 0.15 * ABS((SELECT AVG(metric_value) FROM baseline)) THEN 'trend_break'
    ELSE 'stable'
  END AS trend_signal
""".strip()

    series_sql = f"""
SELECT
  DATE("{time_col}") AS x,
  SUM(CAST("{metric}" AS REAL)) AS y
FROM "{table_name}"
GROUP BY x
ORDER BY x DESC
LIMIT 30
""".strip()

    plan.queries.append({"label": "Trend break detection", "query": signal_sql})
    plan.queries.append({"label": "Trend series", "query": series_sql})
    return plan

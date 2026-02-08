from __future__ import annotations

from backend.src.services.analytics.helpers import pick_metric_column, pick_time_column
from backend.src.services.analytics.patterns.types import PatternPlan


def build_anomaly_noise_check(
    table_name: str,
    columns: list[str],
    schema: dict[str, str],
    intent: dict,
) -> PatternPlan:
    metric = pick_metric_column(schema, intent.get("metric"))
    time_col = pick_time_column(columns, intent.get("time_column"))

    plan = PatternPlan(name="anomaly_noise_check")
    if not metric:
        plan.diagnostics.append({"code": "MISSING_METRIC", "message": "No numeric metric column found"})
        return plan
    if not time_col:
        plan.diagnostics.append({"code": "MISSING_TIME_COLUMN", "message": "No time-like column found"})
        return plan

    sql = f'''
WITH daily AS (
  SELECT DATE("{time_col}") AS dt, SUM(CAST("{metric}" AS REAL)) AS metric_value
  FROM "{table_name}"
  GROUP BY dt
  ORDER BY dt
),
deltas AS (
  SELECT dt, metric_value - LAG(metric_value) OVER (ORDER BY dt) AS delta
  FROM daily
),
stats AS (
  SELECT AVG(ABS(delta)) AS avg_abs_delta
  FROM deltas
  WHERE delta IS NOT NULL AND dt < (SELECT MAX(dt) FROM deltas)
),
latest AS (
  SELECT dt, delta
  FROM deltas
  WHERE dt = (SELECT MAX(dt) FROM deltas)
)
SELECT
  latest.dt,
  latest.delta AS latest_delta,
  stats.avg_abs_delta,
  CASE
    WHEN stats.avg_abs_delta IS NULL OR stats.avg_abs_delta = 0 THEN 'insufficient'
    WHEN ABS(latest.delta) >= 2 * stats.avg_abs_delta THEN 'likely_anomaly'
    ELSE 'likely_noise'
  END AS signal
FROM latest, stats
'''.strip()

    plan.queries.append({"label": "Anomaly vs noise", "query": sql})
    return plan

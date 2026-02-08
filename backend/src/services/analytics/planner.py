from __future__ import annotations

from backend.src.services.analytics.patterns.anomaly_noise import build_anomaly_noise_check
from backend.src.services.analytics.patterns.data_quality import build_data_quality_checks
from backend.src.services.analytics.patterns.metric_change_decomposition import build_metric_change_decomposition
from backend.src.services.analytics.patterns.segment_contribution import build_segment_contribution
from backend.src.services.analytics.patterns.trend_break import build_trend_break_detection


def plan_analyses(dataset_meta: dict, intent: dict) -> tuple[list[dict[str, str]], list[dict[str, str]], list[str]]:
    table_name = dataset_meta["table_name"]
    columns = dataset_meta["columns"]
    schema = dataset_meta["schema"]

    keyword_text = (intent.get("raw_question") or "").lower()
    request_quality = any(token in keyword_text for token in ["quality", "missing", "duplicate"])

    builders = [
        build_metric_change_decomposition,
        build_segment_contribution,
        build_anomaly_noise_check,
        build_trend_break_detection,
        build_data_quality_checks,
    ]

    if request_quality:
        builders = [build_data_quality_checks]

    planned_queries: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []
    selected_patterns: list[str] = []

    for build in builders:
        planned = build(table_name=table_name, columns=columns, schema=schema, intent=intent)
        selected_patterns.append(planned.name)
        diagnostics.extend(planned.diagnostics)
        for query in planned.queries:
            planned_queries.append({
                "label": query["label"],
                "sql": query["query"],
                "pattern": planned.name,
            })

    return planned_queries, diagnostics, selected_patterns

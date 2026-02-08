from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from src.llm.router import ModelRouter, try_parse_json
from src.services.analytics.helpers import pick_metric_column, pick_time_column
from src.services.analytics.planner import plan_analyses
from src.services.sql.validator import validate_safe_select, validate_sql_references

WORD_RE = re.compile(r"[a-zA-Z0-9_]+")


@dataclass
class PlannerCost:
    model: str
    prompt_tokens: int
    completion_tokens: int
    usd: float


def _tokenize(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text.lower())}


def _mentioned_columns(question: str, columns: list[str]) -> list[str]:
    lowered = question.lower()
    return [column for column in columns if column.lower() in lowered]


def _build_frequency_query(table_name: str, column: str, limit: int = 20) -> dict[str, str]:
    sql = f'''
SELECT
  COALESCE(CAST("{column}" AS TEXT), '(null)') AS value,
  COUNT(*) AS frequency
FROM "{table_name}"
GROUP BY value
ORDER BY frequency DESC, value ASC
LIMIT {limit}
'''.strip()
    return {
        "label": f"Most common values for {column}",
        "sql": sql,
        "pattern": "heuristic_frequency",
    }


def _build_numeric_aggregate_query(table_name: str, column: str, aggregate: str) -> dict[str, str]:
    fn = aggregate.upper()
    sql = f'SELECT {fn}(CAST("{column}" AS REAL)) AS value FROM "{table_name}"'
    return {
        "label": f"{fn} for {column}",
        "sql": sql,
        "pattern": "heuristic_numeric",
    }


def build_heuristic_queries(question: str, dataset_meta: dict[str, Any]) -> list[dict[str, str]]:
    table_name = dataset_meta["table_name"]
    columns = dataset_meta["columns"]
    schema = dataset_meta["schema"]

    tokens = _tokenize(question)
    mentioned = _mentioned_columns(question, columns)

    text_columns = [column for column, kind in schema.items() if kind == "TEXT"]
    numeric_columns = [column for column, kind in schema.items() if kind in {"INTEGER", "REAL"}]

    frequency_intents = {
        "common",
        "frequent",
        "frequency",
        "popular",
        "mode",
        "top",
    }
    if tokens.intersection(frequency_intents):
        target = next((column for column in mentioned if column in text_columns), None)
        if target is None and len(text_columns) == 1:
            target = text_columns[0]
        if target is not None:
            return [_build_frequency_query(table_name, target)]

    agg_map = {
        "average": "avg",
        "mean": "avg",
        "sum": "sum",
        "total": "sum",
        "max": "max",
        "highest": "max",
        "min": "min",
        "lowest": "min",
    }
    requested_agg = next((agg for token, agg in agg_map.items() if token in tokens), None)
    if requested_agg:
        target = next((column for column in mentioned if column in numeric_columns), None)
        if target is None and len(numeric_columns) == 1:
            target = numeric_columns[0]
        if target is not None:
            return [_build_numeric_aggregate_query(table_name, target, requested_agg)]

    if "count" in tokens or ("how" in tokens and "many" in tokens):
        sql = f'SELECT COUNT(*) AS row_count FROM "{table_name}"'
        return [
            {
                "label": "Row count",
                "sql": sql,
                "pattern": "heuristic_count",
            }
        ]

    return []


def _question_needs_advanced_planning(question: str) -> bool:
    lowered = question.lower()
    advanced_markers = [
        " by ",
        " over ",
        " trend",
        "compare",
        "versus",
        " vs ",
        "breakdown",
        "why",
        "driver",
    ]
    return any(marker in lowered for marker in advanced_markers)


def _build_llm_prompt_payload(question: str, dataset_meta: dict[str, Any], clarifications: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": question,
        "table_name": dataset_meta["table_name"],
        "columns": dataset_meta["columns"],
        "schema": dataset_meta["schema"],
        "clarifications": clarifications,
    }


def _extract_llm_queries(parsed: dict[str, Any]) -> list[dict[str, str]]:
    raw_queries = parsed.get("queries")
    if not isinstance(raw_queries, list):
        return []

    output: list[dict[str, str]] = []
    for item in raw_queries:
        if not isinstance(item, dict):
            continue
        sql = str(item.get("sql", "")).strip()
        if not sql:
            continue
        label = str(item.get("label") or item.get("purpose") or "Generated analysis")
        output.append({"label": label, "sql": sql, "pattern": "llm_dynamic"})
    return output


def _dedupe_queries(queries: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    output: list[dict[str, str]] = []
    for query in queries:
        normalized = " ".join(query["sql"].split()).strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(query)
    return output


def _validate_queries(
    queries: list[dict[str, str]],
    *,
    table_name: str,
    columns: list[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    valid: list[dict[str, str]] = []
    diagnostics: list[dict[str, str]] = []

    for query in queries:
        safe = validate_safe_select(query["sql"])
        if not safe.is_valid:
            diagnostics.append(
                {
                    "code": "UNSAFE_SQL_PLAN",
                    "message": f"{query['label']}: {safe.reason}",
                }
            )
            continue

        refs = validate_sql_references(query["sql"], table_name=table_name, allowed_columns=columns)
        if not refs.is_valid:
            diagnostics.append(
                {
                    "code": "INVALID_SQL_REFERENCES",
                    "message": f"{query['label']}: {refs.reason}",
                }
            )
            continue

        valid.append(query)

    return valid, diagnostics


def _include_prebuilt_patterns(question: str) -> bool:
    lowered = question.lower()
    markers = [
        "change",
        "trend",
        "drop",
        "increase",
        "decrease",
        "anomaly",
        "noise",
        "driver",
        "quality",
        "missing",
        "duplicate",
    ]
    return any(marker in lowered for marker in markers)


def build_hybrid_query_plan(
    *,
    router: ModelRouter,
    request_id: str,
    question: str,
    dataset_meta: dict[str, Any],
    clarifications: dict[str, Any],
    intent: dict[str, Any],
    max_queries: int,
) -> tuple[list[dict[str, str]], list[dict[str, str]], PlannerCost | None]:
    diagnostics: list[dict[str, str]] = []
    planned: list[dict[str, str]] = []
    planner_cost: PlannerCost | None = None

    heuristic_queries = build_heuristic_queries(question, dataset_meta)
    planned.extend(heuristic_queries)

    if _include_prebuilt_patterns(question):
        normalized_intent = dict(intent)
        if not normalized_intent.get("metric"):
            normalized_intent["metric"] = pick_metric_column(dataset_meta["schema"], clarifications.get("metric"))
        if not normalized_intent.get("time_column"):
            normalized_intent["time_column"] = pick_time_column(dataset_meta["columns"], clarifications.get("time_column"))
        pattern_queries, pattern_diagnostics, _ = plan_analyses(dataset_meta, normalized_intent)
        planned.extend(pattern_queries)
        diagnostics.extend(pattern_diagnostics)

    should_use_llm = _question_needs_advanced_planning(question) or not planned
    if should_use_llm:
        llm = router.call(
            request_id=request_id,
            app="data-ghost-api",
            task="plan_sql_queries",
            system_prompt=(
                "You are a SQL planning assistant for SQLite. Given a user question and a table schema, "
                "return JSON: {\"queries\":[{\"label\":string,\"sql\":string}]}. "
                "Rules: use ONLY SELECT/CTE statements; use ONLY provided table and columns; "
                "prefer 1-3 queries; include aggregation/grouping when needed; quote identifiers with double quotes; "
                "for raw rows include LIMIT <= 200."
            ),
            user_prompt=json.dumps(_build_llm_prompt_payload(question, dataset_meta, clarifications)),
            prefer_expensive=False,
        )
        planner_cost = PlannerCost(
            model=llm.model,
            prompt_tokens=llm.prompt_tokens,
            completion_tokens=llm.completion_tokens,
            usd=llm.usd,
        )

        parsed = try_parse_json(llm.text)
        llm_queries = _extract_llm_queries(parsed)
        if not llm_queries:
            diagnostics.append(
                {
                    "code": "LLM_PLAN_EMPTY",
                    "message": "Dynamic SQL planner returned no usable queries.",
                }
            )
        planned.extend(llm_queries)

    planned = _dedupe_queries(planned)
    planned = planned[:max_queries]

    valid, plan_diagnostics = _validate_queries(
        planned,
        table_name=dataset_meta["table_name"],
        columns=dataset_meta["columns"],
    )
    diagnostics.extend(plan_diagnostics)

    if not valid:
        diagnostics.append(
            {
                "code": "NO_VALID_SQL_PLAN",
                "message": "Unable to produce a safe SQL plan for this question and schema.",
            }
        )

    return valid, diagnostics, planner_cost

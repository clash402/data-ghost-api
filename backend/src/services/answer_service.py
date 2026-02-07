from __future__ import annotations

import json
from typing import Any

from backend.src.llm.router import ModelRouter, try_parse_json


def build_drivers(executed_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for result in executed_results:
        label = result.get("label", "").lower()
        if "decomposition" in label or "contribution" in label:
            rows = result.get("rows", [])[:5]
            output = []
            for row in rows:
                output.append(
                    {
                        "name": str(row.get("segment", row.get("name", "segment"))),
                        "contribution": float(row.get("contribution", row.get("delta", 0.0)) or 0.0),
                        "evidence": row,
                    }
                )
            if output:
                return output

    return []


def build_charts(executed_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    charts: list[dict[str, Any]] = []

    for result in executed_results:
        if result.get("label") == "Trend series":
            points = [{"x": row.get("x"), "y": float(row.get("y", 0.0) or 0.0)} for row in result.get("rows", [])]
            if points:
                charts.append({"kind": "line", "title": "Metric trend (latest 30 periods)", "data": list(reversed(points))})

    if charts:
        return charts

    for result in executed_results:
        rows = result.get("rows", [])
        if not rows:
            continue
        first = rows[0]
        x_key = next((k for k in first.keys() if k in {"segment", "x", "dt", "date"}), None)
        y_key = next((k for k in first.keys() if k in {"contribution", "delta", "y", "metric_value"}), None)
        if x_key and y_key:
            charts.append(
                {
                    "kind": "line",
                    "title": f"{result['label']} signal",
                    "data": [{"x": row.get(x_key), "y": float(row.get(y_key, 0.0) or 0.0)} for row in rows[:30]],
                }
            )
            break
    return charts


def synthesize_narrative(
    *,
    router: ModelRouter,
    request_id: str,
    question: str,
    executed_results: list[dict[str, Any]],
    diagnostics: list[dict[str, str]],
    confidence: dict[str, Any],
    context_citations: list[dict[str, Any]],
) -> tuple[str, str, dict[str, int | float | str]]:
    if not executed_results:
        return (
            "Insufficient evidence",
            "No SQL query produced usable results. Upload a richer dataset or clarify metric/timeframe.",
            {"model": "none", "prompt_tokens": 0, "completion_tokens": 0, "usd": 0.0},
        )

    synthesis_input = {
        "question": question,
        "top_results": executed_results[:3],
        "diagnostics": diagnostics,
        "confidence": confidence,
        "context": context_citations[:3],
    }

    llm = router.call(
        request_id=request_id,
        app="data-ghost-api",
        task="synthesize_explanation",
        system_prompt=(
            "You are a data analyst assistant. Only summarize what is supported by SQL results. "
            "If evidence is partial, say that explicitly. Return JSON with headline and narrative."
        ),
        user_prompt=json.dumps(synthesis_input),
        prefer_expensive=True,
    )
    parsed = try_parse_json(llm.text)
    headline = str(parsed.get("headline") or "Analysis summary")
    narrative = str(parsed.get("narrative") or parsed.get("summary") or "SQL results were executed and summarized.")

    return (
        headline,
        narrative,
        {
            "model": llm.model,
            "prompt_tokens": llm.prompt_tokens,
            "completion_tokens": llm.completion_tokens,
            "usd": llm.usd,
        },
    )

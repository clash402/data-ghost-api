from __future__ import annotations

from typing import Any


def validate_results(
    *,
    planned_count: int,
    executed_results: list[dict[str, Any]],
    execution_errors: list[dict[str, str]],
    prior_diagnostics: list[dict[str, str]],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    diagnostics = list(prior_diagnostics)
    diagnostics.extend(execution_errors)

    executed_count = len(executed_results)
    non_empty = sum(1 for item in executed_results if item.get("rows"))

    if planned_count == 0:
        diagnostics.append({"code": "NO_ANALYSIS_PLAN", "message": "No runnable analyses were produced"})
        return {
            "level": "insufficient",
            "reasons": ["No analysis plan could be generated from current dataset/question."],
        }, diagnostics

    if executed_count == 0:
        diagnostics.append({"code": "NO_QUERY_RESULTS", "message": "All planned analyses failed to execute"})
        return {
            "level": "insufficient",
            "reasons": ["No query executed successfully. Fix dataset schema or question specificity."],
        }, diagnostics

    success_rate = executed_count / planned_count
    if non_empty == 0:
        diagnostics.append({"code": "EMPTY_RESULTS", "message": "Queries ran but returned empty result sets"})
        return {
            "level": "low",
            "reasons": ["Queries returned no rows; conclusions are weak."],
        }, diagnostics

    partial_failure_codes = {
        "MISSING_METRIC",
        "MISSING_TIME_COLUMN",
        "MISSING_DIMENSION",
        "SQL_EXECUTION_ERROR",
        "QUERY_BUDGET_EXCEEDED",
        "EMPTY_RESULTS",
    }
    has_partial_failure = any(item.get("code") in partial_failure_codes for item in diagnostics)

    if has_partial_failure:
        return {
            "level": "insufficient",
            "reasons": ["Partial validation failure detected; use results as directional evidence only."],
        }, diagnostics

    if execution_errors:
        return {
            "level": "insufficient",
            "reasons": ["Some planned analyses failed validation/execution; treat findings as partial."],
        }, diagnostics

    if success_rate >= 0.8 and not execution_errors:
        return {
            "level": "high",
            "reasons": ["Most planned analyses executed successfully with non-empty results."],
        }, diagnostics

    if success_rate >= 0.5:
        return {
            "level": "medium",
            "reasons": ["Some analyses executed; some failed or were incomplete."],
        }, diagnostics

    return {
        "level": "insufficient",
        "reasons": ["Too many analysis steps failed; provide clarifications or cleaner data."],
    }, diagnostics

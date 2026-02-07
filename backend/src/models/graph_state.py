from __future__ import annotations

from typing import Any, Literal, NotRequired, TypedDict


class PlannedAnalysis(TypedDict):
    name: str
    description: str
    sql_label: str
    sql: str


class ExecutedResult(TypedDict):
    label: str
    sql: str
    rows: list[dict[str, Any]]


class ValidationOutcome(TypedDict):
    pass_rate: float
    confidence_level: Literal["high", "medium", "low", "insufficient"]
    diagnostics: list[dict[str, str]]


class ContextCitation(TypedDict):
    doc_id: str
    filename: str
    chunk_id: str
    score: float
    snippet: str


class CostTrace(TypedDict):
    models: list[str]
    prompt_tokens: int
    completion_tokens: int
    usd: float


class AgentState(TypedDict):
    request_id: str
    conversation_id: str
    question: str
    clarifications: dict[str, Any]
    needs_clarification: bool
    clarification_questions: list[dict[str, Any]]
    intent: dict[str, Any]
    dataset_meta: dict[str, Any]
    planned_analyses: list[PlannedAnalysis]
    executed_results: list[ExecutedResult]
    validation: ValidationOutcome
    context_citations: list[ContextCitation]
    answer: dict[str, Any]
    diagnostics: list[dict[str, str]]
    confidence: dict[str, Any]
    cost_trace: CostTrace
    status: NotRequired[str]

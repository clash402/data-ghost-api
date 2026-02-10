from __future__ import annotations

import uuid
from typing import Any

from src.core.settings import get_settings
from src.llm.router import ModelRouter, try_parse_json
from src.models.graph_state import AgentState
from src.services.analytics.dynamic_planner import build_hybrid_query_plan
from src.services.analytics.validator import validate_results
from src.services.answer_service import build_charts, build_drivers, synthesize_narrative
from src.services.context_service import retrieve_context
from src.services.sql.executor import SqlExecutionError, execute_safe_query
from src.storage.repositories import get_dataset_meta

try:
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover - fallback in environments without langgraph
    END = "__end__"
    StateGraph = None


def _base_cost_trace() -> dict[str, Any]:
    return {
        "models": [],
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "usd": 0.0,
    }


def _add_cost(state: AgentState, model: str, prompt_tokens: int, completion_tokens: int, usd: float) -> None:
    cost = state["cost_trace"]
    if model not in cost["models"]:
        cost["models"].append(model)
    cost["prompt_tokens"] += prompt_tokens
    cost["completion_tokens"] += completion_tokens
    cost["usd"] += usd


def _extract_mentions(question: str, columns: list[str]) -> dict[str, str]:
    lowered = question.lower()
    for col in columns:
        if col.lower() in lowered:
            return {"column_mention": col}
    return {}


def parse_intent_node(state: AgentState) -> AgentState:
    router = ModelRouter()
    existing_intent = dict(state.get("intent") or {})
    llm = router.call(
        request_id=state["request_id"],
        app="data-ghost-api",
        task="parse_intent",
        system_prompt=(
            "Extract analysis intent from the question. Return JSON with metric, timeframe, dimensions, top_n."
        ),
        user_prompt=state["question"],
        prefer_expensive=False,
    )
    parsed = try_parse_json(llm.text)
    parsed.update(existing_intent)
    parsed["raw_question"] = state["question"]
    state["intent"] = parsed
    _add_cost(state, llm.model, llm.prompt_tokens, llm.completion_tokens, llm.usd)
    return state


def check_dataset_ready_node(state: AgentState) -> AgentState:
    dataset = get_dataset_meta()
    if dataset is None:
        state["diagnostics"].append(
            {
                "code": "DATASET_NOT_READY",
                "message": "Upload a CSV dataset first using POST /upload/dataset.",
            }
        )
        state["status"] = "dataset_not_ready"
        state["dataset_meta"] = {}
        return state

    state["dataset_meta"] = dataset
    state["status"] = "ok"
    return state


def decide_need_clarification_node(state: AgentState) -> AgentState:
    if state.get("status") == "dataset_not_ready":
        state["needs_clarification"] = False
        return state

    dataset_meta = state["dataset_meta"]
    question = state["question"].lower()
    clarifications = state.get("clarifications", {}) or {}

    numeric_columns = [k for k, v in dataset_meta["schema"].items() if v in {"INTEGER", "REAL"}]
    mentioned_metric = next((c for c in numeric_columns if c.lower() in question), None)
    selected_metric = clarifications.get("metric") or mentioned_metric

    time_columns = [
        c
        for c in dataset_meta["columns"]
        if any(token in c.lower() for token in ["date", "time", "week", "day", "month", "year"])
    ]
    selected_time = clarifications.get("time_column") or next(
        (c for c in time_columns if c.lower() in question), None
    )
    if len(time_columns) == 1 and not selected_time:
        selected_time = time_columns[0]

    state["intent"].update(_extract_mentions(state["question"], dataset_meta["columns"]))

    questions: list[dict[str, Any]] = []
    asks_numeric_metric = any(
        token in question
        for token in ["average", "mean", "sum", "total", "median", "trend", "change", "increase", "decrease", "drop"]
    )
    if asks_numeric_metric and not selected_metric and len(numeric_columns) > 1:
        questions.append(
            {
                "key": "metric",
                "type": "select",
                "prompt": "Which metric should be analyzed?",
                "options": numeric_columns,
            }
        )

    asks_change = any(token in question for token in ["change", "trend", "drop", "increase", "decrease", "week", "month"])
    if asks_change and not selected_time and len(time_columns) > 1:
        questions.append(
            {
                "key": "time_column",
                "type": "select",
                "prompt": "Which column should be treated as time?",
                "options": time_columns,
            }
        )

    state["needs_clarification"] = len(questions) > 0
    state["clarification_questions"] = questions
    if selected_metric:
        state["intent"]["metric"] = selected_metric
    if selected_time:
        state["intent"]["time_column"] = selected_time

    return state


def plan_analyses_node(state: AgentState) -> AgentState:
    router = ModelRouter()
    planned_queries, diagnostics, planner_cost = build_hybrid_query_plan(
        router=router,
        request_id=state["request_id"],
        question=state["question"],
        dataset_meta=state["dataset_meta"],
        clarifications=state["clarifications"],
        intent=state["intent"],
        max_queries=get_settings().query_max_per_request,
    )
    if planner_cost is not None:
        _add_cost(
            state,
            planner_cost.model,
            planner_cost.prompt_tokens,
            planner_cost.completion_tokens,
            planner_cost.usd,
        )

    state["planned_analyses"] = [
        {
            "name": item["pattern"],
            "description": item["label"],
            "sql_label": item["label"],
            "sql": item["sql"],
        }
        for item in planned_queries
    ]
    state["diagnostics"].extend(diagnostics)
    return state


def execute_queries_node(state: AgentState) -> AgentState:
    executed: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    settings = get_settings()
    planned = state["planned_analyses"]

    if len(planned) > settings.query_max_per_request:
        errors.append(
            {
                "code": "QUERY_BUDGET_EXCEEDED",
                "message": f"Planned {len(planned)} queries, budget is {settings.query_max_per_request}. Trimming plan.",
            }
        )
        planned = planned[: settings.query_max_per_request]
        state["planned_analyses"] = planned

    for item in planned:
        try:
            rows = execute_safe_query(item["sql"])
            executed.append({"label": item["sql_label"], "sql": item["sql"], "rows": rows})
        except SqlExecutionError as exc:
            errors.append(
                {
                    "code": "SQL_EXECUTION_ERROR",
                    "message": f"{item['sql_label']}: {exc}",
                }
            )

    state["executed_results"] = executed
    if errors:
        state.setdefault("execution_errors", errors)
    return state


def validate_results_node(state: AgentState) -> AgentState:
    execution_errors = state.get("execution_errors", [])
    confidence, diagnostics = validate_results(
        planned_count=len(state["planned_analyses"]),
        executed_results=state["executed_results"],
        execution_errors=execution_errors,
        prior_diagnostics=state["diagnostics"],
    )
    state["confidence"] = confidence
    state["diagnostics"] = diagnostics
    return state


def retrieve_context_node(state: AgentState) -> AgentState:
    state["context_citations"] = retrieve_context(state["question"], top_k=5)
    return state


def synthesize_explanation_node(state: AgentState) -> AgentState:
    router = ModelRouter()
    headline, narrative, final_cost = synthesize_narrative(
        router=router,
        request_id=state["request_id"],
        question=state["question"],
        executed_results=state["executed_results"],
        diagnostics=state["diagnostics"],
        confidence=state["confidence"],
        context_citations=state["context_citations"],
    )
    _add_cost(
        state,
        str(final_cost["model"]),
        int(final_cost["prompt_tokens"]),
        int(final_cost["completion_tokens"]),
        float(final_cost["usd"]),
    )

    drivers = build_drivers(state["executed_results"])
    charts = build_charts(state["executed_results"])

    sql_artifacts = [
        {
            "label": result["label"],
            "query": result["sql"],
        }
        for result in state["executed_results"]
    ]

    state["answer"] = {
        "headline": headline,
        "narrative": narrative,
        "drivers": drivers,
        "charts": charts,
        "sql": sql_artifacts,
        "confidence": state["confidence"],
        "diagnostics": state["diagnostics"],
        "cost": {
            "model": ",".join(state["cost_trace"]["models"]),
            "prompt_tokens": state["cost_trace"]["prompt_tokens"],
            "completion_tokens": state["cost_trace"]["completion_tokens"],
            "usd": round(state["cost_trace"]["usd"], 8),
        },
        "context_citations": state["context_citations"],
    }
    return state


def finalize_response_node(state: AgentState) -> AgentState:
    if state.get("needs_clarification"):
        state["answer"] = {}
        return state

    if state.get("status") == "dataset_not_ready":
        state["confidence"] = {
            "level": "insufficient",
            "reasons": ["No dataset available."],
        }
        state["answer"] = {
            "headline": "Dataset required",
            "narrative": "Upload a CSV dataset using POST /upload/dataset before asking analysis questions.",
            "drivers": [],
            "charts": [],
            "sql": [],
            "confidence": state["confidence"],
            "diagnostics": state["diagnostics"],
            "cost": {
                "model": ",".join(state["cost_trace"]["models"]),
                "prompt_tokens": state["cost_trace"]["prompt_tokens"],
                "completion_tokens": state["cost_trace"]["completion_tokens"],
                "usd": round(state["cost_trace"]["usd"], 8),
            },
        }

    return state


def _should_continue(state: AgentState) -> str:
    if state.get("status") == "dataset_not_ready":
        return "needs_clarification"
    if state.get("needs_clarification"):
        return "needs_clarification"
    return "continue"


def _fallback_run(initial_state: AgentState) -> AgentState:
    state = check_dataset_ready_node(initial_state)
    state = decide_need_clarification_node(state)
    if state.get("status") == "dataset_not_ready" or state.get("needs_clarification"):
        return finalize_response_node(state)

    state = parse_intent_node(state)
    state = plan_analyses_node(state)
    state = execute_queries_node(state)
    state = validate_results_node(state)
    state = retrieve_context_node(state)
    state = synthesize_explanation_node(state)
    return finalize_response_node(state)


def build_ask_graph():
    if StateGraph is None:
        return None

    graph = StateGraph(AgentState)
    graph.add_node("parse_intent", parse_intent_node)
    graph.add_node("check_dataset_ready", check_dataset_ready_node)
    graph.add_node("decide_need_clarification", decide_need_clarification_node)
    graph.add_node("plan_analyses", plan_analyses_node)
    graph.add_node("execute_queries", execute_queries_node)
    graph.add_node("validate_results", validate_results_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("synthesize_explanation", synthesize_explanation_node)
    graph.add_node("finalize_response", finalize_response_node)

    graph.set_entry_point("check_dataset_ready")
    graph.add_edge("check_dataset_ready", "decide_need_clarification")
    graph.add_conditional_edges(
        "decide_need_clarification",
        _should_continue,
        {
            "needs_clarification": "finalize_response",
            "continue": "parse_intent",
        },
    )
    graph.add_edge("parse_intent", "plan_analyses")
    graph.add_edge("plan_analyses", "execute_queries")
    graph.add_edge("execute_queries", "validate_results")
    graph.add_edge("validate_results", "retrieve_context")
    graph.add_edge("retrieve_context", "synthesize_explanation")
    graph.add_edge("synthesize_explanation", "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


def run_ask_pipeline(
    question: str,
    conversation_id: str | None,
    clarifications: dict[str, Any] | None,
    request_id: str | None = None,
) -> AgentState:
    state: AgentState = {
        "request_id": request_id or str(uuid.uuid4()),
        "conversation_id": conversation_id or str(uuid.uuid4()),
        "question": question,
        "clarifications": clarifications or {},
        "needs_clarification": False,
        "clarification_questions": [],
        "intent": {},
        "dataset_meta": {},
        "planned_analyses": [],
        "executed_results": [],
        "validation": {
            "pass_rate": 0.0,
            "confidence_level": "insufficient",
            "diagnostics": [],
        },
        "context_citations": [],
        "answer": {},
        "diagnostics": [],
        "confidence": {"level": "insufficient", "reasons": []},
        "cost_trace": _base_cost_trace(),
    }

    app = build_ask_graph()
    if app is None:
        return _fallback_run(state)

    result = app.invoke(state)
    return result

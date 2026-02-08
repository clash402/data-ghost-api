from __future__ import annotations

from typing import Any

from src.storage.repositories import insert_request_log
from src.utils.time import utc_now_iso


def log_ask_request(
    *,
    request_id: str,
    conversation_id: str,
    question: str,
    cost_trace: dict[str, Any],
    status: str,
    diagnostics: list[dict[str, Any]],
    response: dict[str, Any] | None,
) -> None:
    insert_request_log(
        request_id=request_id,
        conversation_id=conversation_id,
        question=question,
        models=cost_trace.get("models", []),
        prompt_tokens=int(cost_trace.get("prompt_tokens", 0)),
        completion_tokens=int(cost_trace.get("completion_tokens", 0)),
        usd_cost=float(cost_trace.get("usd", 0.0)),
        status=status,
        diagnostics=diagnostics,
        response=response,
        created_at=utc_now_iso(),
    )

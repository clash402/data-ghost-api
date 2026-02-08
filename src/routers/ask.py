from __future__ import annotations

from fastapi import APIRouter, Request

from src.agents.ask_graph import run_ask_pipeline
from src.schemas.api import AskRequest, AskResponse
from src.services.request_log_service import log_ask_request

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, request: Request) -> AskResponse:
    result = run_ask_pipeline(
        question=payload.question,
        conversation_id=payload.conversation_id,
        clarifications=payload.clarifications,
        request_id=getattr(request.state, "request_id", None),
    )

    needs_clarification = bool(result.get("needs_clarification"))

    status = "needs_clarification" if needs_clarification else "completed"
    response_answer = None if needs_clarification else result.get("answer")

    response = AskResponse(
        conversation_id=result["conversation_id"],
        needs_clarification=needs_clarification,
        clarification_questions=result.get("clarification_questions", []),
        answer=response_answer,
    )

    log_ask_request(
        request_id=result["request_id"],
        conversation_id=result["conversation_id"],
        question=payload.question,
        cost_trace=result.get("cost_trace", {}),
        status=status,
        diagnostics=result.get("diagnostics", []),
        response=response.model_dump(mode="json"),
    )

    return response

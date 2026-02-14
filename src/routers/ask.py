from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Request

from src.agents.ask_graph import run_ask_pipeline
from src.core.logging import get_logger
from src.core.settings import get_settings
from src.llm.router import LlmBudgetExceededError, LlmDisabledError, LlmProviderError
from src.schemas.api import AskRequest, AskResponse
from src.services.ask_cache_service import (
    build_ask_cache_key,
    get_cached_ask_response,
    set_cached_ask_response,
)
from src.services.rate_limit_service import (
    RateLimitExceededError,
    enforce_rate_limit,
    get_request_client_ip,
)
from src.services.request_log_service import log_ask_request
from src.storage.repositories import get_dataset_meta

router = APIRouter(tags=["ask"])
logger = get_logger(__name__)


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, request: Request) -> AskResponse:
    settings = get_settings()
    client_ip = get_request_client_ip(request)
    try:
        enforce_rate_limit(
            bucket="ask_per_minute",
            key=client_ip,
            limit=settings.ask_rate_limit_per_minute,
            window_seconds=60,
        )
        enforce_rate_limit(
            bucket="ask_per_hour",
            key=client_ip,
            limit=settings.ask_rate_limit_per_hour,
            window_seconds=3600,
        )
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    dataset_meta = get_dataset_meta()
    cache_key = build_ask_cache_key(
        question=payload.question,
        dataset_id=dataset_meta["dataset_id"] if dataset_meta else None,
        clarifications=payload.clarifications,
    )
    cached_response = get_cached_ask_response(cache_key)
    if cached_response is not None:
        return AskResponse.model_validate(cached_response)

    try:
        result = run_ask_pipeline(
            question=payload.question,
            conversation_id=payload.conversation_id,
            clarifications=payload.clarifications,
            request_id=request_id,
        )
    except LlmBudgetExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except LlmDisabledError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LlmProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error during ask pipeline", extra={"request_id": request_id})
        raise HTTPException(
            status_code=500, detail="Internal error while processing question."
        ) from exc

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

    if not needs_clarification and response.answer is not None:
        set_cached_ask_response(
            cache_key=cache_key,
            payload=response.model_dump(mode="json"),
            ttl_seconds=settings.ask_cache_ttl_seconds,
        )

    return response

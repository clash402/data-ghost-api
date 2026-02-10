from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from src.core.settings import get_settings
from src.schemas.api import VoiceSpeakRequest, VoiceTranscribeResponse
from src.services.rate_limit_service import (
    RateLimitExceededError,
    enforce_rate_limit,
    get_request_client_ip,
)
from src.services.voice_service import (
    VoiceConfigError,
    VoiceProviderError,
    VoiceValidationError,
    synthesize_voice,
    transcribe_voice_upload,
)

router = APIRouter(tags=["voice"])


@router.post("/voice/transcribe", response_model=VoiceTranscribeResponse)
async def voice_transcribe(
    request: Request,
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> VoiceTranscribeResponse:
    settings = get_settings()
    client_ip = get_request_client_ip(request)
    try:
        enforce_rate_limit(
            bucket="voice_per_minute",
            key=client_ip,
            limit=settings.voice_rate_limit_per_minute,
            window_seconds=60,
        )
        enforce_rate_limit(
            bucket="voice_per_hour",
            key=client_ip,
            limit=settings.voice_rate_limit_per_hour,
            window_seconds=3600,
        )
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    content = await file.read()

    try:
        return transcribe_voice_upload(
            filename=file.filename,
            content_type=file.content_type,
            content=content,
            language=language,
        )
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except VoiceConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VoiceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/voice/speak")
def voice_speak(payload: VoiceSpeakRequest, request: Request) -> StreamingResponse:
    settings = get_settings()
    client_ip = get_request_client_ip(request)
    try:
        enforce_rate_limit(
            bucket="voice_per_minute",
            key=client_ip,
            limit=settings.voice_rate_limit_per_minute,
            window_seconds=60,
        )
        enforce_rate_limit(
            bucket="voice_per_hour",
            key=client_ip,
            limit=settings.voice_rate_limit_per_hour,
            window_seconds=3600,
        )
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc

    try:
        audio_bytes = synthesize_voice(text=payload.text, voice_id=payload.voice_id)
    except VoiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except VoiceConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VoiceProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="data-ghost-response.mp3"'},
    )

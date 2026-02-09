from __future__ import annotations

import io

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.schemas.api import VoiceSpeakRequest, VoiceTranscribeResponse
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
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
) -> VoiceTranscribeResponse:
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
def voice_speak(payload: VoiceSpeakRequest) -> StreamingResponse:
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

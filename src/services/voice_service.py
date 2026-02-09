from __future__ import annotations

from pathlib import Path

from src.core.settings import get_settings
from src.integrations.elevenlabs_speech import synthesize_speech
from src.integrations.openai_speech import transcribe_audio
from src.schemas.api import VoiceTranscribeResponse

_ALLOWED_AUDIO_MIME_TYPES = {
    "audio/webm",
    "audio/mp4",
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
}

_ALLOWED_AUDIO_EXTENSIONS = {
    ".webm",
    ".mp4",
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
}


class VoiceValidationError(Exception):
    pass


class VoiceConfigError(Exception):
    pass


class VoiceProviderError(Exception):
    pass


def _extract_provider_error_detail(exc: Exception) -> str:
    details: list[str] = []

    try:
        from elevenlabs.core.api_error import ApiError as ElevenLabsApiError
    except Exception:  # pragma: no cover - optional dependency import
        ElevenLabsApiError = None

    if ElevenLabsApiError and isinstance(exc, ElevenLabsApiError):
        status_code = getattr(exc, "status_code", None)
        if status_code is not None:
            details.append(f"status={status_code}")

        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            detail = body.get("detail")
            if isinstance(detail, dict):
                code = detail.get("status") or detail.get("code")
                message = detail.get("message")
                if code:
                    details.append(str(code))
                if message:
                    details.append(str(message))
            elif isinstance(detail, str) and detail:
                details.append(detail)

            message = body.get("message")
            if isinstance(message, str) and message:
                details.append(message)

    try:
        from openai import APIError as OpenAIApiError
        from openai import APIStatusError as OpenAIApiStatusError
    except Exception:  # pragma: no cover - optional dependency import
        OpenAIApiError = None
        OpenAIApiStatusError = None

    if OpenAIApiError and isinstance(exc, OpenAIApiError):
        if OpenAIApiStatusError and isinstance(exc, OpenAIApiStatusError):
            status_code = getattr(exc, "status_code", None)
            if status_code is not None:
                details.append(f"status={status_code}")

        message = getattr(exc, "message", None)
        if isinstance(message, str) and message:
            details.append(message)
        elif str(exc):
            details.append(str(exc))

    if not details and str(exc):
        details.append(str(exc))

    collapsed = "; ".join(
        item.replace("\n", " ").strip() for item in details if item and item.strip()
    )
    return collapsed[:240]


def _normalize_mime_type(content_type: str | None) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _validate_audio_upload(
    filename: str | None, content_type: str | None, content: bytes, max_upload_mb: int
) -> None:
    if not filename:
        raise VoiceValidationError("Audio file is required")

    if not content:
        raise VoiceValidationError("Audio file is empty")

    max_upload_bytes = max_upload_mb * 1024 * 1024
    if len(content) > max_upload_bytes:
        raise VoiceValidationError(f"Audio file exceeds max size of {max_upload_mb} MB")

    extension = Path(filename).suffix.lower()
    mime_type = _normalize_mime_type(content_type)

    if extension not in _ALLOWED_AUDIO_EXTENSIONS and mime_type not in _ALLOWED_AUDIO_MIME_TYPES:
        raise VoiceValidationError(
            "Unsupported audio file type. Use webm, mp4, mp3, wav, ogg, or m4a"
        )


def _normalize_text(text: str, max_chars: int) -> str:
    normalized = text.strip()
    if not normalized:
        raise VoiceValidationError("Text is required")

    if len(normalized) > max_chars:
        raise VoiceValidationError(f"Text exceeds max length of {max_chars} characters")

    return normalized


def transcribe_voice_upload(
    *,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    language: str | None,
) -> VoiceTranscribeResponse:
    settings = get_settings()

    _validate_audio_upload(filename, content_type, content, settings.voice_max_upload_mb)

    if not settings.llm_openai_api_key:
        raise VoiceConfigError(
            "Voice transcription is unavailable because OPENAI_API_KEY is not configured"
        )

    normalized_language = language.strip() if language else None

    try:
        return transcribe_audio(
            filename=filename or "audio.webm",
            content=content,
            language=normalized_language,
            model=settings.openai_stt_model,
            api_key=settings.llm_openai_api_key,
        )
    except Exception as exc:
        detail = _extract_provider_error_detail(exc)
        raise VoiceProviderError(f"Voice transcription provider request failed ({detail})") from exc


def synthesize_voice(*, text: str, voice_id: str | None) -> bytes:
    settings = get_settings()
    normalized_text = _normalize_text(text, settings.voice_max_tts_chars)

    if not settings.elevenlabs_api_key:
        raise VoiceConfigError(
            "Voice synthesis is unavailable because ELEVENLABS_API_KEY is not configured"
        )

    selected_voice_id = (voice_id or settings.elevenlabs_voice_id or "").strip()
    if not selected_voice_id:
        raise VoiceConfigError(
            "Voice synthesis is unavailable because ELEVENLABS_VOICE_ID is not configured"
        )

    try:
        return synthesize_speech(
            text=normalized_text,
            voice_id=selected_voice_id,
            model_id=settings.elevenlabs_model_id,
            output_format=settings.elevenlabs_output_format,
            api_key=settings.elevenlabs_api_key,
        )
    except Exception as exc:
        detail = _extract_provider_error_detail(exc)
        raise VoiceProviderError(f"Voice synthesis provider request failed ({detail})") from exc

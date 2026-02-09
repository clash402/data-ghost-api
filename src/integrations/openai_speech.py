from __future__ import annotations

import io

from src.schemas.api import VoiceTranscribeResponse


def _build_openai_client(api_key: str):
    try:
        from openai import OpenAI
    except Exception as exc:  # pragma: no cover - runtime dependency check
        raise RuntimeError("OpenAI SDK is not installed") from exc

    return OpenAI(api_key=api_key)


def transcribe_audio(
    *,
    filename: str,
    content: bytes,
    language: str | None,
    model: str,
    api_key: str,
) -> VoiceTranscribeResponse:
    file_obj = io.BytesIO(content)
    file_obj.name = filename

    client = _build_openai_client(api_key)
    params: dict[str, str | io.BytesIO] = {"model": model, "file": file_obj}
    if language:
        params["language"] = language

    result = client.audio.transcriptions.create(**params)

    text = getattr(result, "text", None)
    if text is None and isinstance(result, dict):
        text = result.get("text")

    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("OpenAI transcription returned an empty response")

    return VoiceTranscribeResponse(text=text.strip(), provider="openai", model=model)

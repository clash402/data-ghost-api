from __future__ import annotations


def _build_elevenlabs_client(api_key: str):
    try:
        from elevenlabs.client import ElevenLabs
    except Exception as exc:  # pragma: no cover - runtime dependency check
        raise RuntimeError("ElevenLabs SDK is not installed") from exc

    return ElevenLabs(api_key=api_key)


def _coerce_audio_to_bytes(audio: bytes | bytearray | str | object) -> bytes:
    if isinstance(audio, bytes):
        return audio
    if isinstance(audio, bytearray):
        return bytes(audio)

    if hasattr(audio, "__iter__"):
        chunks: list[bytes] = []
        for chunk in audio:  # type: ignore[operator]
            if isinstance(chunk, bytes):
                chunks.append(chunk)
            elif isinstance(chunk, bytearray):
                chunks.append(bytes(chunk))
        return b"".join(chunks)

    return b""


def synthesize_speech(
    *,
    text: str,
    voice_id: str,
    model_id: str,
    output_format: str,
    api_key: str,
) -> bytes:
    client = _build_elevenlabs_client(api_key)
    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=model_id,
        output_format=output_format,
    )
    audio_bytes = _coerce_audio_to_bytes(audio)
    if not audio_bytes:
        raise RuntimeError("ElevenLabs returned empty audio")
    return audio_bytes

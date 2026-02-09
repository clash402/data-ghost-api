from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.core.settings import get_settings
from src.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_transcribe_success_with_mocked_openai_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    class _FakeTranscriptions:
        def create(self, **kwargs):
            assert kwargs["model"] == "gpt-4o-mini-transcribe"
            assert kwargs["language"] == "en"
            return type("Result", (), {"text": "Transcribed text"})()

    class _FakeAudio:
        transcriptions = _FakeTranscriptions()

    class _FakeOpenAIClient:
        audio = _FakeAudio()

    monkeypatch.setattr(
        "src.integrations.openai_speech._build_openai_client",
        lambda api_key: _FakeOpenAIClient(),
    )

    response = client.post(
        "/voice/transcribe",
        files={"file": ("sample.webm", b"dummy-audio", "audio/webm")},
        data={"language": "en"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Transcribed text",
        "provider": "openai",
        "model": "gpt-4o-mini-transcribe",
    }


def test_transcribe_rejects_unsupported_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    response = client.post(
        "/voice/transcribe",
        files={"file": ("notes.txt", b"not-audio", "text/plain")},
    )

    assert response.status_code == 400
    assert "unsupported" in response.json()["detail"].lower()


def test_transcribe_rejects_oversized_upload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("VOICE_MAX_UPLOAD_MB", "1")

    response = client.post(
        "/voice/transcribe",
        files={"file": ("sample.webm", b"a" * (1024 * 1024 + 1), "audio/webm")},
    )

    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"].lower()


def test_transcribe_returns_503_when_openai_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")

    response = client.post(
        "/voice/transcribe",
        files={"file": ("sample.webm", b"dummy-audio", "audio/webm")},
    )

    assert response.status_code == 503
    assert "openai_api_key" in response.json()["detail"].lower()


def test_speak_success_returns_audio_mpeg_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_123")

    class _FakeTextToSpeech:
        def convert(self, **kwargs):
            assert kwargs["voice_id"] == "voice_123"
            assert kwargs["model_id"] == "eleven_multilingual_v2"
            return [b"audio-", b"bytes"]

    class _FakeElevenLabsClient:
        text_to_speech = _FakeTextToSpeech()

    monkeypatch.setattr(
        "src.integrations.elevenlabs_speech._build_elevenlabs_client",
        lambda api_key: _FakeElevenLabsClient(),
    )

    response = client.post("/voice/speak", json={"text": "hello from data ghost"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert response.headers["content-disposition"] == 'inline; filename="data-ghost-response.mp3"'
    assert response.content == b"audio-bytes"


def test_speak_rejects_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_123")

    response = client.post("/voice/speak", json={"text": "   "})

    assert response.status_code == 400
    assert "text is required" in response.json()["detail"].lower()


def test_speak_rejects_oversized_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_123")
    monkeypatch.setenv("VOICE_MAX_TTS_CHARS", "5")

    response = client.post("/voice/speak", json={"text": "012345"})

    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"].lower()


def test_speak_returns_503_when_elevenlabs_config_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_123")

    response = client.post("/voice/speak", json={"text": "hello"})

    assert response.status_code == 503
    assert "elevenlabs_api_key" in response.json()["detail"].lower()


def test_speak_maps_provider_error_to_502(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_123")

    class _FailingTextToSpeech:
        def convert(self, **kwargs):
            raise RuntimeError("provider down")

    class _FailingElevenLabsClient:
        text_to_speech = _FailingTextToSpeech()

    monkeypatch.setattr(
        "src.integrations.elevenlabs_speech._build_elevenlabs_client",
        lambda api_key: _FailingElevenLabsClient(),
    )

    response = client.post("/voice/speak", json={"text": "hello"})

    assert response.status_code == 502
    assert "provider" in response.json()["detail"].lower()

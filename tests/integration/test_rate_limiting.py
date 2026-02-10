from __future__ import annotations

from fastapi.testclient import TestClient

from src.core.settings import get_settings
from src.main import app

client = TestClient(app)


def _upload_simple_dataset() -> None:
    csv_content = "date,revenue\n2025-01-01,100\n2025-01-02,120\n"
    response = client.post(
        "/upload/dataset",
        files={"file": ("sample.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200


def test_ask_rate_limit_returns_429_on_second_request(monkeypatch) -> None:
    monkeypatch.setenv("ASK_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("ASK_RATE_LIMIT_PER_HOUR", "10")
    get_settings.cache_clear()

    _upload_simple_dataset()

    first = client.post("/ask", json={"question": "How many rows are in this dataset?"})
    second = client.post("/ask", json={"question": "How many rows are in this dataset?"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert "rate limit exceeded" in second.json()["detail"].lower()


def test_voice_transcribe_rate_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("VOICE_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("VOICE_RATE_LIMIT_PER_HOUR", "10")
    get_settings.cache_clear()

    class _FakeTranscriptions:
        def create(self, **kwargs):
            return type("Result", (), {"text": "Transcribed text"})()

    class _FakeAudio:
        transcriptions = _FakeTranscriptions()

    class _FakeOpenAIClient:
        audio = _FakeAudio()

    monkeypatch.setattr(
        "src.integrations.openai_speech._build_openai_client",
        lambda api_key: _FakeOpenAIClient(),
    )

    first = client.post(
        "/voice/transcribe",
        files={"file": ("sample.webm", b"dummy-audio", "audio/webm")},
    )
    second = client.post(
        "/voice/transcribe",
        files={"file": ("sample.webm", b"dummy-audio", "audio/webm")},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert "rate limit exceeded" in second.json()["detail"].lower()


def test_voice_speak_rate_limit_returns_429(monkeypatch) -> None:
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-elevenlabs-key")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "voice_123")
    monkeypatch.setenv("VOICE_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("VOICE_RATE_LIMIT_PER_HOUR", "10")
    get_settings.cache_clear()

    class _FakeTextToSpeech:
        def convert(self, **kwargs):
            return [b"audio", b"bytes"]

    class _FakeElevenLabsClient:
        text_to_speech = _FakeTextToSpeech()

    monkeypatch.setattr(
        "src.integrations.elevenlabs_speech._build_elevenlabs_client",
        lambda api_key: _FakeElevenLabsClient(),
    )

    first = client.post("/voice/speak", json={"text": "hello"})
    second = client.post("/voice/speak", json={"text": "hello again"})

    assert first.status_code == 200
    assert second.status_code == 429
    assert "rate limit exceeded" in second.json()["detail"].lower()

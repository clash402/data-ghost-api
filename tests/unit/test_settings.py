from __future__ import annotations

from src.core.settings import Settings


def test_cors_allow_origins_normalizes_csv_input() -> None:
    settings = Settings(
        CORS_ALLOW_ORIGINS="https://data-ghost-web.vercel.app/, https://Data-Ghost-Web.vercel.app/path"
    )
    assert settings.cors_allow_origins == [
        "https://data-ghost-web.vercel.app",
        "https://data-ghost-web.vercel.app",
    ]


def test_cors_allow_origins_normalizes_json_list_input() -> None:
    settings = Settings(
        CORS_ALLOW_ORIGINS='["https://data-ghost-web.vercel.app/","https://preview.vercel.app/path"]'
    )
    assert settings.cors_allow_origins == [
        "https://data-ghost-web.vercel.app",
        "https://preview.vercel.app",
    ]

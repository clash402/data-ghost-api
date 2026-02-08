from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.logging import configure_logging
from src.core.middleware import RequestIdMiddleware
from src.core.settings import get_settings
from src.db.init_db import init_db
from src.routers.ask import router as ask_router
from src.routers.dataset import router as dataset_router
from src.routers.health import router as health_router
from src.routers.upload import router as upload_router

settings = get_settings()
configure_logging()
init_db()

app = FastAPI(title=settings.app_name)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Data Ghost API"}


app.include_router(health_router)
app.include_router(upload_router)
app.include_router(dataset_router)
app.include_router(ask_router)

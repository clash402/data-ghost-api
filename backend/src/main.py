from __future__ import annotations

from fastapi import FastAPI

from backend.src.core.logging import configure_logging
from backend.src.core.middleware import RequestIdMiddleware
from backend.src.core.settings import get_settings
from backend.src.db.init_db import init_db
from backend.src.routers.ask import router as ask_router
from backend.src.routers.dataset import router as dataset_router
from backend.src.routers.health import router as health_router
from backend.src.routers.upload import router as upload_router

settings = get_settings()
configure_logging()
init_db()

app = FastAPI(title=settings.app_name)
app.add_middleware(RequestIdMiddleware)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Data Ghost API"}


app.include_router(health_router)
app.include_router(upload_router)
app.include_router(dataset_router)
app.include_router(ask_router)

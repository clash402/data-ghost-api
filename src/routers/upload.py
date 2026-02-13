from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.core.settings import get_settings
from src.schemas.api import ContextUploadResponse, DatasetUploadResponse
from src.services.context_service import ingest_context_doc
from src.services.dataset_service import ingest_csv

router = APIRouter(prefix="/upload", tags=["upload"])

_READ_CHUNK_BYTES = 1024 * 1024


async def _read_limited_upload(file: UploadFile, *, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413, detail="Uploaded file exceeds the configured size limit"
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/dataset", response_model=DatasetUploadResponse)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetUploadResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Dataset upload requires a CSV file")

    settings = get_settings()
    content = await _read_limited_upload(
        file, max_bytes=settings.dataset_max_upload_mb * 1024 * 1024
    )
    try:
        summary = ingest_csv(file.filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DatasetUploadResponse(
        dataset_id=summary.dataset_id,
        table_name=summary.table_name,
        rows=summary.rows,
        columns=summary.columns,
        schema_=summary.schema,
    )


@router.post("/context", response_model=ContextUploadResponse)
async def upload_context(file: UploadFile = File(...)) -> ContextUploadResponse:
    settings = get_settings()
    content = await _read_limited_upload(
        file, max_bytes=settings.context_max_upload_mb * 1024 * 1024
    )
    try:
        result = ingest_context_doc(file.filename, file.content_type, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ContextUploadResponse(
        doc_id=result.doc_id,
        filename=result.filename,
        chunks=result.chunks,
        created_at=result.created_at,
    )

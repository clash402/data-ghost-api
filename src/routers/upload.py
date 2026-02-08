from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.schemas.api import ContextUploadResponse, DatasetUploadResponse
from src.services.context_service import ingest_context_doc
from src.services.dataset_service import ingest_csv

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/dataset", response_model=DatasetUploadResponse)
async def upload_dataset(file: UploadFile = File(...)) -> DatasetUploadResponse:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Dataset upload requires a CSV file")

    content = await file.read()
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
    content = await file.read()
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

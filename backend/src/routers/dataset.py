from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.src.schemas.api import DatasetSummaryResponse
from backend.src.services.dataset_service import get_dataset_summary

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/summary", response_model=DatasetSummaryResponse)
def dataset_summary() -> DatasetSummaryResponse:
    try:
        summary = get_dataset_summary()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DatasetSummaryResponse(
        dataset_id=summary.dataset_id,
        name=summary.name,
        table_name=summary.table_name,
        rows=summary.rows,
        columns=summary.columns,
        schema_=summary.schema,
        sample_rows=summary.sample_rows,
        created_at=summary.created_at,
    )

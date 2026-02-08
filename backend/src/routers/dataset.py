from __future__ import annotations

from fastapi import APIRouter

from backend.src.schemas.api import DatasetSummaryNotReadyResponse, DatasetSummaryResponse
from backend.src.services.dataset_service import get_dataset_summary

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/summary", response_model=DatasetSummaryResponse | DatasetSummaryNotReadyResponse)
def dataset_summary() -> DatasetSummaryResponse | DatasetSummaryNotReadyResponse:
    try:
        summary = get_dataset_summary()
    except ValueError:
        return DatasetSummaryNotReadyResponse()

    return DatasetSummaryResponse(
        dataset_uploaded=True,
        dataset_id=summary.dataset_id,
        name=summary.name,
        table_name=summary.table_name,
        rows=summary.rows,
        columns=summary.columns,
        schema_=summary.schema,
        sample_rows=summary.sample_rows,
        created_at=summary.created_at,
    )

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Diagnostic(BaseModel):
    code: str
    message: str


class Confidence(BaseModel):
    level: str
    reasons: list[str] = Field(default_factory=list)


class Driver(BaseModel):
    name: str
    contribution: float
    evidence: dict[str, Any] = Field(default_factory=dict)


class ChartPoint(BaseModel):
    x: Any
    y: float


class Chart(BaseModel):
    kind: str
    title: str
    data: list[ChartPoint] = Field(default_factory=list)


class SqlArtifact(BaseModel):
    label: str
    query: str


class CostSummary(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    usd: float


class AnswerPayload(BaseModel):
    headline: str
    narrative: str
    drivers: list[Driver] = Field(default_factory=list)
    charts: list[Chart] = Field(default_factory=list)
    sql: list[SqlArtifact] = Field(default_factory=list)
    confidence: Confidence
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    cost: CostSummary


class ClarificationQuestion(BaseModel):
    key: str
    type: str
    prompt: str
    options: list[str] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    clarifications: dict[str, Any] | None = None


class AskResponse(BaseModel):
    conversation_id: str
    needs_clarification: bool
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    answer: AnswerPayload | None = None


class VoiceSpeakRequest(BaseModel):
    text: str
    voice_id: str | None = None


class VoiceTranscribeResponse(BaseModel):
    text: str
    provider: str = "openai"
    model: str


class DatasetSummaryResponse(BaseModel):
    dataset_uploaded: bool = True
    dataset_id: str
    name: str
    table_name: str
    rows: int
    columns: list[str]
    schema_: dict[str, str] = Field(serialization_alias="schema")
    sample_rows: list[dict[str, Any]]
    created_at: datetime


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    table_name: str
    rows: int
    columns: list[str]
    schema_: dict[str, str] = Field(serialization_alias="schema")


class DatasetSummaryNotReadyResponse(BaseModel):
    dataset_uploaded: bool = False
    message: str = "No dataset uploaded yet. Upload a CSV via POST /upload/dataset."


class ContextUploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks: int
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    app: str
    env: str


class RequestRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_id: str
    conversation_id: str
    question: str
    models: list[str]
    prompt_tokens: int
    completion_tokens: int
    usd_cost: float
    status: str
    diagnostics: list[dict[str, Any]]
    response: dict[str, Any] | None
    created_at: datetime

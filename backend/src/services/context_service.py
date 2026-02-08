from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.src.services.rag.chunker import chunk_text
from backend.src.services.rag.embedder import cosine_similarity, embed_text
from backend.src.storage.repositories import (
    insert_docs_meta,
    insert_vector_chunk,
    list_vector_chunks,
)
from backend.src.utils.time import utc_now_iso


@dataclass
class ContextDocSummary:
    doc_id: str
    filename: str
    chunks: int
    created_at: datetime


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise ValueError("PDF support requires pypdf dependency") from exc

    reader = PdfReader(io.BytesIO(content))
    extracted = []
    for page in reader.pages:
        extracted.append(page.extract_text() or "")
    return "\n".join(extracted)


def _extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf_text(content)
    if lower.endswith((".txt", ".md", ".csv")):
        return content.decode("utf-8-sig")
    raise ValueError("Unsupported context file type. Use PDF, TXT, or MD")


def ingest_context_doc(filename: str, content_type: str | None, content: bytes) -> ContextDocSummary:
    text = _extract_text(filename, content)
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("Document is empty after extraction")

    created_at = utc_now_iso()
    doc_id = str(uuid.uuid4())
    insert_docs_meta(doc_id=doc_id, filename=filename, content_type=content_type, chunks=len(chunks), created_at=created_at)

    for idx, chunk in enumerate(chunks):
        embedding = embed_text(chunk)
        insert_vector_chunk(doc_id=doc_id, chunk_index=idx, content=chunk, embedding=embedding, created_at=created_at)

    return ContextDocSummary(
        doc_id=doc_id,
        filename=filename,
        chunks=len(chunks),
        created_at=datetime.fromisoformat(created_at),
    )


def retrieve_context(question: str, top_k: int = 5) -> list[dict[str, str | float]]:
    query_embedding = embed_text(question)
    candidates = list_vector_chunks()
    scored = []
    for chunk in candidates:
        score = cosine_similarity(query_embedding, chunk["embedding"])
        scored.append(
            {
                "doc_id": chunk["doc_id"],
                "filename": chunk["filename"],
                "chunk_id": chunk["chunk_id"],
                "snippet": chunk["content"][:300],
                "score": score,
            }
        )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]

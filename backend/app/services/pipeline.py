"""Document processing pipeline.

Stages: validation -> extraction -> chunking -> classification -> summary ->
structured extraction -> embeddings -> indexing. Each stage updates the job
record so the UI can show real progress; any failure marks document + job as
failed with the technical error stored (shown only to authorized users).

Reprocessing is idempotent: derived artifacts (text, chunks, embeddings,
classification, summary, extractions) are deleted and rebuilt.
"""
import datetime as dt
import json
import logging
import time

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.ai.base import AIProviderError
from app.ai.factory import get_provider
from app.ai.schemas import EXTRACTION_MODELS, SCHEMA_BY_CATEGORY
from app.models import (
    Classification,
    Document,
    DocumentChunk,
    DocumentText,
    Embedding,
    ExtractedField,
    ProcessingJob,
    Summary,
)
from app.services import vectors
from app.services.chunking import chunk_text
from app.services.extraction import ExtractionError, extract_text
from app.services.storage import get_storage

logger = logging.getLogger("app.pipeline")


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


class PipelineError(Exception):
    def __init__(self, stage: str, message: str):
        self.stage = stage
        super().__init__(message)


def _set_stage(db: Session, job: ProcessingJob, stage: str) -> None:
    job.stage = stage
    db.commit()


def _clear_derived(db: Session, document_id: int) -> None:
    """Remove all derived artifacts so reprocessing starts clean (idempotent)."""
    chunk_ids = [c.id for c in db.query(DocumentChunk.id).filter_by(document_id=document_id)]
    if chunk_ids:
        db.execute(delete(Embedding).where(Embedding.chunk_id.in_(chunk_ids)))
    db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    db.execute(delete(DocumentText).where(DocumentText.document_id == document_id))
    db.execute(delete(Classification).where(Classification.document_id == document_id))
    db.execute(delete(Summary).where(Summary.document_id == document_id))
    db.execute(delete(ExtractedField).where(ExtractedField.document_id == document_id))
    db.commit()


def run_pipeline(db: Session, job: ProcessingJob) -> None:
    """Execute all stages for one job. Raises PipelineError on failure."""
    provider = get_provider()
    document: Document = db.get(Document, job.document_id)
    if document is None:
        raise PipelineError("validation", "El documento ya no existe")

    document.status = "processing"
    document.error_message = ""
    db.commit()

    _clear_derived(db, document.id)

    # --- validation + read from storage -------------------------------------
    _set_stage(db, job, "validation")
    storage = get_storage()
    if not storage.exists(document.storage_key):
        raise PipelineError("validation", "El archivo fisico no existe en el almacenamiento")
    content = storage.read(document.storage_key)

    # --- text extraction -----------------------------------------------------
    _set_stage(db, job, "extraction")
    try:
        full_text, page_count, page_offsets = extract_text(content, document.file_type)
    except ExtractionError as exc:
        raise PipelineError("extraction", str(exc))
    document.page_count = page_count
    db.add(DocumentText(document_id=document.id, content=full_text, char_count=len(full_text)))
    db.commit()

    # --- chunking ------------------------------------------------------------
    _set_stage(db, job, "chunking")
    chunk_dicts = chunk_text(full_text, page_offsets)
    if not chunk_dicts:
        raise PipelineError("chunking", "No se generaron fragmentos de texto")
    chunk_rows = []
    for c in chunk_dicts:
        row = DocumentChunk(
            document_id=document.id,
            chunk_index=c["index"],
            content=c["content"],
            page_number=c["page_number"],
            start_char=c["start_char"],
            end_char=c["end_char"],
        )
        db.add(row)
        chunk_rows.append(row)
    db.commit()

    # --- classification ------------------------------------------------------
    _set_stage(db, job, "classification")
    try:
        result = provider.classify(full_text)
    except AIProviderError as exc:
        raise PipelineError("classification", f"Fallo del proveedor de IA: {exc}")
    db.add(
        Classification(
            document_id=document.id,
            predicted_category=result.category,
            confidence=result.confidence,
            model=provider.chat_model_name,
        )
    )
    db.commit()

    # --- summary -------------------------------------------------------------
    _set_stage(db, job, "summary")
    try:
        summary_text = provider.summarize(full_text)
    except AIProviderError as exc:
        raise PipelineError("summary", f"Fallo del proveedor de IA: {exc}")
    db.add(Summary(document_id=document.id, content=summary_text, model=provider.chat_model_name))
    db.commit()

    # --- structured extraction ----------------------------------------------
    _set_stage(db, job, "structured_extraction")
    schema_name = SCHEMA_BY_CATEGORY.get(result.category)
    if schema_name:
        try:
            raw = provider.extract(full_text, schema_name)
            validated = EXTRACTION_MODELS[schema_name](**raw)  # Pydantic validation
        except AIProviderError as exc:
            raise PipelineError("structured_extraction", f"Fallo del proveedor de IA: {exc}")
        except Exception as exc:
            raise PipelineError("structured_extraction", f"Salida estructurada invalida: {exc}")
        db.add(
            ExtractedField(
                document_id=document.id,
                schema_name=schema_name,
                data=json.dumps(validated.model_dump(), ensure_ascii=False),
                model=provider.chat_model_name,
            )
        )
        db.commit()

    # --- embeddings ----------------------------------------------------------
    _set_stage(db, job, "embeddings")
    texts = [c.content for c in chunk_rows]
    try:
        vecs = provider.embed(texts)
    except AIProviderError as exc:
        raise PipelineError("embeddings", f"Fallo del proveedor de IA: {exc}")
    for chunk_row, vec in zip(chunk_rows, vecs):
        db.add(
            Embedding(
                chunk_id=chunk_row.id,
                model=provider.embedding_model_name,
                dim=len(vec),
                vector=vectors.to_bytes(vec),
            )
        )
    db.commit()

    # --- done ----------------------------------------------------------------
    _set_stage(db, job, "indexing")
    document.status = "completed"
    document.error_message = ""
    db.commit()


def execute_job(db: Session, job_id: int) -> bool:
    """Run one queued job with attempt bookkeeping. Returns True on success."""
    job: ProcessingJob = db.get(ProcessingJob, job_id)
    if job is None or job.status not in ("queued", "running"):
        return False
    job.status = "running"
    job.attempt += 1
    job.started_at = utcnow()
    job.error_message = ""
    db.commit()

    started = time.monotonic()
    try:
        run_pipeline(db, job)
        job.status = "completed"
        job.finished_at = utcnow()
        job.duration_ms = int((time.monotonic() - started) * 1000)
        db.commit()
        logger.info(
            "Pipeline completado", extra={"event": "job_completed", "job_id": job.id,
                                          "document_id": job.document_id,
                                          "latency_ms": job.duration_ms},
        )
        return True
    except PipelineError as exc:
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        job.stage = exc.stage
        job.error_message = str(exc)
        job.finished_at = utcnow()
        job.duration_ms = int((time.monotonic() - started) * 1000)
        document = db.get(Document, job.document_id)
        if job.attempt < job.max_attempts:
            job.status = "queued"  # retry
            if document:
                document.status = "queued"
        else:
            job.status = "failed"
            if document:
                document.status = "failed"
                document.error_message = f"[{exc.stage}] {exc}"
        db.commit()
        logger.warning(
            "Pipeline fallido en etapa %s: %s", exc.stage, exc,
            extra={"event": "job_failed", "job_id": job.id, "document_id": job.document_id},
        )
        return False
    except Exception as exc:  # unexpected error: fail hard, keep detail in log/db
        db.rollback()
        job = db.get(ProcessingJob, job_id)
        job.status = "failed"
        job.error_message = f"Error inesperado: {exc}"
        job.finished_at = utcnow()
        document = db.get(Document, job.document_id)
        if document:
            document.status = "failed"
            document.error_message = f"Error inesperado: {exc}"
        db.commit()
        logger.exception("Error inesperado en pipeline", extra={"job_id": job_id})
        return False


def enqueue_document(db: Session, document: Document, max_attempts: int = None) -> ProcessingJob:
    """Create a queued full-pipeline job for a document."""
    from app.core.config import get_settings

    job = ProcessingJob(
        document_id=document.id,
        job_type="full_pipeline",
        status="queued",
        max_attempts=max_attempts or get_settings().JOB_MAX_ATTEMPTS,
    )
    document.status = "queued"
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

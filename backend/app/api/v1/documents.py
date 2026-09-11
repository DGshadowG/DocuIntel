"""Document endpoints: upload, list/filter, detail, download, delete, retry."""
import json
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import client_ip, get_current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.db.session import get_db
from app.models import (
    Classification,
    Document,
    DocumentChunk,
    ProcessingJob,
    User,
)
from app.schemas.api import (
    CategoryCorrection,
    ClassificationOut,
    DocumentDetail,
    DocumentOut,
    ExtractionOut,
    JobOut,
    Page,
    SummaryOut,
    UploadResult,
)
from app.services import audit
from app.services.extraction import MIME_BY_TYPE, detect_file_type, sanitize_filename
from app.services.permissions import accessible_repository_ids, get_repository_or_403
from app.services.pipeline import enqueue_document
from app.services.storage import get_storage

router = APIRouter(prefix="/documents", tags=["Documentos"])


def _doc_out(doc: Document) -> DocumentOut:
    out = DocumentOut.model_validate(doc)
    out.uploader_name = doc.uploader.full_name if doc.uploader else ""
    if doc.classification:
        out.category = doc.classification.effective_category
    return out


def _get_document_or_403(db: Session, document_id: int, user: User) -> Document:
    doc = (
        db.query(Document)
        .options(joinedload(Document.classification), joinedload(Document.uploader))
        .filter(Document.id == document_id)
        .first()
    )
    if doc is None:
        raise AppError(404, "not_found", "El documento no existe")
    get_repository_or_403(db, doc.repository_id, user)
    return doc


# ------------------------------------------------------------------ upload
@router.post(
    "/upload", response_model=List[UploadResult], status_code=201,
    summary="Cargar uno o varios documentos (PDF, DOCX, TXT)",
)
def upload_documents(
    request: Request,
    repository_id: int = Query(..., description="Repositorio destino"),
    files: List[UploadFile] = File(..., description="Uno o varios archivos"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    get_repository_or_403(db, repository_id, user, write=True)
    if not files:
        raise AppError(400, "no_files", "Debe adjuntar al menos un archivo")
    if len(files) > 20:
        raise AppError(400, "too_many_files", "Maximo 20 archivos por carga")

    storage = get_storage()
    results: List[UploadResult] = []
    for upload in files:
        raw_name = upload.filename or "documento"
        content = upload.file.read()
        if len(content) == 0:
            raise AppError(400, "empty_file", f"El archivo '{raw_name}' esta vacio")
        if len(content) > settings.max_upload_bytes:
            raise AppError(
                413, "file_too_large",
                f"El archivo '{raw_name}' supera el limite de {settings.MAX_UPLOAD_MB} MB",
            )
        safe_name = sanitize_filename(raw_name)
        file_type = detect_file_type(safe_name, content)  # raises AppError on invalid type/content
        storage_key = storage.save(content, file_type)
        doc = Document(
            repository_id=repository_id,
            uploaded_by=user.id,
            original_filename=safe_name,
            storage_key=storage_key,
            file_type=file_type,
            mime_type=MIME_BY_TYPE[file_type],
            size_bytes=len(content),
            status="pending",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        job = enqueue_document(db, doc)
        audit.record(db, "upload_document", user_id=user.id, entity_type="document",
                     entity_id=doc.id, detail=safe_name, ip_address=client_ip(request))
        results.append(UploadResult(document=_doc_out(doc), job_id=job.id))
    return results


# ------------------------------------------------------------------ list
@router.get("", response_model=Page[DocumentOut], summary="Listar documentos con filtros")
def list_documents(
    repository_id: Optional[int] = None,
    status: Optional[str] = Query(None, pattern="^(pending|queued|processing|completed|failed)$"),
    category: Optional[str] = Query(None, pattern="^(financiero|legal|talento_humano|otro)$"),
    file_type: Optional[str] = Query(None, pattern="^(pdf|docx|txt)$"),
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if repository_id is not None:
        get_repository_or_403(db, repository_id, user)
        repo_ids = [repository_id]
    else:
        repo_ids = accessible_repository_ids(db, user)
    if not repo_ids:
        return Page(items=[], total=0, page=page, page_size=page_size, pages=0)

    query = (
        db.query(Document)
        .options(joinedload(Document.classification), joinedload(Document.uploader))
        .filter(Document.repository_id.in_(repo_ids))
    )
    if status:
        query = query.filter(Document.status == status)
    if file_type:
        query = query.filter(Document.file_type == file_type)
    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if category:
        query = query.join(Classification, Classification.document_id == Document.id).filter(
            or_(
                Classification.manual_category == category,
                (Classification.manual_category.is_(None)) & (Classification.predicted_category == category),
            )
        )
    total = query.count()
    docs = (
        query.order_by(Document.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return Page(
        items=[_doc_out(d) for d in docs],
        total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 0,
    )


# ------------------------------------------------------------------ detail
@router.get("/{document_id}", response_model=DocumentDetail, summary="Detalle del documento")
def get_document(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    doc = _get_document_or_403(db, document_id, user)
    detail = DocumentDetail.model_validate(_doc_out(doc).model_dump())
    if doc.classification:
        c = doc.classification
        detail.classification = ClassificationOut(
            predicted_category=c.predicted_category, confidence=c.confidence, model=c.model,
            manual_category=c.manual_category, effective_category=c.effective_category,
            corrected_at=c.corrected_at,
        )
    if doc.summary:
        detail.summary = SummaryOut.model_validate(doc.summary)
    detail.extractions = [
        ExtractionOut(schema_name=e.schema_name, data=json.loads(e.data), model=e.model, created_at=e.created_at)
        for e in doc.extracted_fields
    ]
    detail.chunk_count = (
        db.query(func.count(DocumentChunk.id)).filter(DocumentChunk.document_id == doc.id).scalar() or 0
    )
    if doc.text:
        detail.text_preview = doc.text.content[:3000]
    return detail


@router.get("/{document_id}/content", summary="Texto completo extraido")
def get_document_content(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    doc = _get_document_or_403(db, document_id, user)
    if not doc.text:
        raise AppError(404, "no_text", "El documento aun no tiene texto extraido")
    return {"document_id": doc.id, "char_count": doc.text.char_count, "content": doc.text.content}


# ------------------------------------------------------------------ download
@router.get("/{document_id}/download", summary="Descargar archivo original")
def download_document(
    document_id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    doc = _get_document_or_403(db, document_id, user)
    storage = get_storage()
    if not storage.exists(doc.storage_key):
        raise AppError(410, "file_missing", "El archivo fisico ya no esta disponible")
    content = storage.read(doc.storage_key)
    audit.record(db, "download_document", user_id=user.id, entity_type="document",
                 entity_id=doc.id, ip_address=client_ip(request))
    # RFC 5987 filename* for names with non-ASCII characters
    from urllib.parse import quote
    disposition = f"attachment; filename*=UTF-8''{quote(doc.original_filename)}"
    return Response(
        content=content,
        media_type=doc.mime_type,
        headers={"Content-Disposition": disposition},
    )


# ------------------------------------------------------------------ delete
@router.delete("/{document_id}", status_code=204, summary="Eliminar documento")
def delete_document(
    document_id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    doc = _get_document_or_403(db, document_id, user)
    storage = get_storage()
    try:
        storage.delete(doc.storage_key)
    except Exception:
        pass
    name = doc.original_filename
    db.delete(doc)  # cascades to text, chunks, embeddings, jobs, results
    db.commit()
    audit.record(db, "delete_document", user_id=user.id, entity_type="document",
                 entity_id=document_id, detail=name, ip_address=client_ip(request))
    return None


# ------------------------------------------------------------------ reprocess / jobs
@router.post("/{document_id}/reprocess", response_model=JobOut, status_code=202,
             summary="Reintentar / reprocesar documento")
def reprocess_document(
    document_id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    doc = _get_document_or_403(db, document_id, user)
    active = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == doc.id, ProcessingJob.status.in_(["queued", "running"]))
        .first()
    )
    if active:
        raise AppError(409, "already_processing", "El documento ya tiene un procesamiento en curso")
    job = enqueue_document(db, doc)
    audit.record(db, "reprocess_document", user_id=user.id, entity_type="document",
                 entity_id=doc.id, ip_address=client_ip(request))
    return job


@router.get("/{document_id}/jobs", response_model=List[JobOut], summary="Historial de procesamientos")
def document_jobs(
    document_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    doc = _get_document_or_403(db, document_id, user)
    return (
        db.query(ProcessingJob)
        .filter(ProcessingJob.document_id == doc.id)
        .order_by(ProcessingJob.created_at.desc())
        .all()
    )


# ------------------------------------------------------------------ category correction
@router.patch("/{document_id}/category", response_model=ClassificationOut,
              summary="Corregir manualmente la categoria")
def correct_category(
    document_id: int, payload: CategoryCorrection, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    import datetime as dt

    doc = _get_document_or_403(db, document_id, user)
    if doc.classification is None:
        raise AppError(409, "not_classified", "El documento aun no ha sido clasificado")
    c = doc.classification
    c.manual_category = payload.category
    c.corrected_by = user.id
    c.corrected_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(c)
    audit.record(db, "correct_category", user_id=user.id, entity_type="document",
                 entity_id=doc.id, detail=payload.category, ip_address=client_ip(request))
    return ClassificationOut(
        predicted_category=c.predicted_category, confidence=c.confidence, model=c.model,
        manual_category=c.manual_category, effective_category=c.effective_category,
        corrected_at=c.corrected_at,
    )

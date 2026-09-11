"""Textual and semantic search endpoints (permission-scoped)."""
import math
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.ai.base import AIProviderError
from app.ai.factory import get_provider
from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models import Classification, Document, DocumentChunk, User
from app.schemas.api import SearchHit, SearchResponse
from app.services import vectors
from app.services.permissions import accessible_repository_ids, get_repository_or_403

router = APIRouter(prefix="/search", tags=["Busqueda"])


def _scope_repo_ids(db: Session, user: User, repository_id: Optional[int]) -> List[int]:
    if repository_id is not None:
        get_repository_or_403(db, repository_id, user)
        return [repository_id]
    return accessible_repository_ids(db, user)


def _category_of(doc: Document) -> Optional[str]:
    return doc.classification.effective_category if doc.classification else None


def _apply_filters(query, category, file_type, status):
    if file_type:
        query = query.filter(Document.file_type == file_type)
    if status:
        query = query.filter(Document.status == status)
    if category:
        query = query.join(Classification, Classification.document_id == Document.id).filter(
            or_(
                Classification.manual_category == category,
                (Classification.manual_category.is_(None)) & (Classification.predicted_category == category),
            )
        )
    return query


def _highlight(content: str, terms: List[str], width: int = 260) -> str:
    """Return a snippet around the first match with **term** highlighting."""
    lower = content.lower()
    pos = -1
    for term in terms:
        pos = lower.find(term.lower())
        if pos >= 0:
            break
    if pos < 0:
        snippet = content[:width]
    else:
        start = max(0, pos - width // 3)
        snippet = ("…" if start > 0 else "") + content[start:start + width] + ("…" if start + width < len(content) else "")
    for term in terms:
        snippet = re.sub(f"({re.escape(term)})", r"**\1**", snippet, flags=re.IGNORECASE)
    return snippet


@router.get("/text", response_model=SearchResponse, summary="Busqueda textual por contenido y metadatos")
def text_search(
    q: str = Query(..., min_length=2, max_length=200),
    repository_id: Optional[int] = None,
    category: Optional[str] = Query(None, pattern="^(financiero|legal|talento_humano|otro)$"),
    file_type: Optional[str] = Query(None, pattern="^(pdf|docx|txt)$"),
    status: Optional[str] = Query(None, pattern="^(pending|queued|processing|completed|failed)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo_ids = _scope_repo_ids(db, user, repository_id)
    if not repo_ids:
        return SearchResponse(query=q, mode="text", total=0, page=page, page_size=page_size, hits=[])

    terms = [t for t in q.split() if len(t) >= 2][:6] or [q]

    chunk_query = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .options(joinedload(Document.repository), joinedload(Document.classification))
        .filter(Document.repository_id.in_(repo_ids))
    )
    chunk_query = _apply_filters(chunk_query, category, file_type, status)
    for term in terms:
        chunk_query = chunk_query.filter(
            or_(DocumentChunk.content.ilike(f"%{term}%"), Document.original_filename.ilike(f"%{term}%"))
        )
    # Keep only the best chunk per document to avoid duplicate listings
    rows = chunk_query.order_by(DocumentChunk.document_id, DocumentChunk.chunk_index).all()
    best_by_doc = {}
    for chunk, doc in rows:
        occurrences = sum(chunk.content.lower().count(t.lower()) for t in terms)
        current = best_by_doc.get(doc.id)
        if current is None or occurrences > current[2]:
            best_by_doc[doc.id] = (chunk, doc, occurrences)

    # Also match documents by filename alone (metadata search)
    name_query = (
        db.query(Document)
        .options(joinedload(Document.repository), joinedload(Document.classification))
        .filter(Document.repository_id.in_(repo_ids))
    )
    name_query = _apply_filters(name_query, category, file_type, status)
    for term in terms:
        name_query = name_query.filter(Document.original_filename.ilike(f"%{term}%"))
    for doc in name_query.all():
        if doc.id not in best_by_doc:
            best_by_doc[doc.id] = (None, doc, 1)

    ranked = sorted(best_by_doc.values(), key=lambda x: x[2], reverse=True)
    total = len(ranked)
    page_rows = ranked[(page - 1) * page_size: page * page_size]
    hits = []
    for chunk, doc, occurrences in page_rows:
        hits.append(
            SearchHit(
                document_id=doc.id,
                document_name=doc.original_filename,
                repository_id=doc.repository_id,
                repository_name=doc.repository.name if doc.repository else "",
                file_type=doc.file_type,
                category=_category_of(doc),
                page_number=chunk.page_number if chunk else 1,
                chunk_id=chunk.id if chunk else None,
                snippet=_highlight(chunk.content, terms) if chunk else doc.original_filename,
                score=float(occurrences),
            )
        )
    return SearchResponse(query=q, mode="text", total=total, page=page, page_size=page_size, hits=hits)


@router.get("/semantic", response_model=SearchResponse, summary="Busqueda semantica por embeddings")
def semantic_search(
    q: str = Query(..., min_length=2, max_length=500),
    repository_id: Optional[int] = None,
    category: Optional[str] = Query(None, pattern="^(financiero|legal|talento_humano|otro)$"),
    file_type: Optional[str] = Query(None, pattern="^(pdf|docx|txt)$"),
    top_k: int = Query(10, ge=1, le=30),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo_ids = _scope_repo_ids(db, user, repository_id)
    if not repo_ids:
        return SearchResponse(query=q, mode="semantic", total=0, page=1, page_size=top_k, hits=[])

    provider = get_provider()
    try:
        query_vec = provider.embed([q])[0]
    except AIProviderError as exc:
        raise AppError(503, "ai_unavailable", f"El proveedor de IA no esta disponible: {exc}")

    # Optional filters reduce the candidate document set before vector scan
    doc_ids = None
    if category or file_type:
        candidates = db.query(Document.id).filter(Document.repository_id.in_(repo_ids))
        candidates = _apply_filters(candidates, category, file_type, None)
        doc_ids = [d.id for d in candidates.all()]
        if not doc_ids:
            return SearchResponse(query=q, mode="semantic", total=0, page=1, page_size=top_k, hits=[])

    results = vectors.semantic_search(db, query_vec, repo_ids, top_k=top_k, document_ids=doc_ids)
    hits = []
    for chunk, doc, similarity in results:
        db.refresh(doc)
        hits.append(
            SearchHit(
                document_id=doc.id,
                document_name=doc.original_filename,
                repository_id=doc.repository_id,
                repository_name=doc.repository.name if doc.repository else "",
                file_type=doc.file_type,
                category=_category_of(doc),
                page_number=chunk.page_number,
                chunk_id=chunk.id,
                snippet=chunk.content[:300],
                score=round(similarity, 4),
            )
        )
    return SearchResponse(query=q, mode="semantic", total=len(hits), page=1, page_size=top_k, hits=hits)

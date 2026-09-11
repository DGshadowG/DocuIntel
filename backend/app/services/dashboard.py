"""Dashboard indicators computed with real SQL aggregates, scoped to the
repositories the requesting user can access."""
import datetime as dt
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Classification, Document, ProcessingJob, Repository


def build_dashboard(db: Session, repository_ids: List[int]) -> dict:
    empty = {
        "total_repositories": 0,
        "total_documents": 0,
        "by_category": {},
        "by_format": {},
        "by_status": {},
        "processed_count": 0,
        "failed_count": 0,
        "avg_processing_ms": None,
        "recent_documents": [],
        "recent_errors": [],
        "uploads_last_14_days": [],
    }
    if not repository_ids:
        return empty

    doc_filter = Document.repository_id.in_(repository_ids)

    total_repositories = (
        db.query(func.count(Repository.id)).filter(Repository.id.in_(repository_ids)).scalar() or 0
    )
    total_documents = db.query(func.count(Document.id)).filter(doc_filter).scalar() or 0

    by_status = dict(
        db.query(Document.status, func.count(Document.id)).filter(doc_filter).group_by(Document.status).all()
    )
    by_format = dict(
        db.query(Document.file_type, func.count(Document.id)).filter(doc_filter).group_by(Document.file_type).all()
    )
    category_col = func.coalesce(Classification.manual_category, Classification.predicted_category)
    by_category = dict(
        db.query(category_col, func.count(Classification.id))
        .join(Document, Classification.document_id == Document.id)
        .filter(doc_filter)
        .group_by(category_col)
        .all()
    )

    avg_ms = (
        db.query(func.avg(ProcessingJob.duration_ms))
        .join(Document, ProcessingJob.document_id == Document.id)
        .filter(doc_filter, ProcessingJob.status == "completed", ProcessingJob.duration_ms > 0)
        .scalar()
    )

    recent_documents = [
        {
            "id": d.id,
            "filename": d.original_filename,
            "status": d.status,
            "file_type": d.file_type,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in db.query(Document).filter(doc_filter).order_by(Document.created_at.desc()).limit(8)
    ]
    recent_errors = [
        {
            "id": d.id,
            "filename": d.original_filename,
            "error_message": d.error_message[:300],
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
        }
        for d in db.query(Document)
        .filter(doc_filter, Document.status == "failed")
        .order_by(Document.updated_at.desc())
        .limit(5)
    ]

    # Upload trend, last 14 days (dates computed in Python for cross-DB support)
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=13)
    counts = {}
    for d in db.query(Document.created_at).filter(doc_filter).all():
        created = d[0]
        if created is None:
            continue
        day = created.date()
        if day >= start:
            counts[day.isoformat()] = counts.get(day.isoformat(), 0) + 1
    uploads = [
        {"date": (start + dt.timedelta(days=i)).isoformat(),
         "count": counts.get((start + dt.timedelta(days=i)).isoformat(), 0)}
        for i in range(14)
    ]

    return {
        "total_repositories": total_repositories,
        "total_documents": total_documents,
        "by_category": by_category,
        "by_format": by_format,
        "by_status": by_status,
        "processed_count": by_status.get("completed", 0),
        "failed_count": by_status.get("failed", 0),
        "avg_processing_ms": round(avg_ms) if avg_ms else None,
        "recent_documents": recent_documents,
        "recent_errors": recent_errors,
        "uploads_last_14_days": uploads,
    }

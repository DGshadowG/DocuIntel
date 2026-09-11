"""Audit log listing (admins only)."""
import math
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import AuditLog, User
from app.schemas.api import AuditLogOut, Page

router = APIRouter(prefix="/audit-logs", tags=["Auditoria"])


@router.get("", response_model=Page[AuditLogOut], summary="Registro de auditoria (admin)")
def list_audit_logs(
    action: Optional[str] = Query(None, max_length=60),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = db.query(AuditLog).options(joinedload(AuditLog.user))
    if action:
        query = query.filter(AuditLog.action == action)
    total = query.count()
    rows = (
        query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for row in rows:
        item = AuditLogOut.model_validate(row)
        item.user_email = row.user.email if row.user else ""
        items.append(item)
    return Page(items=items, total=total, page=page, page_size=page_size,
                pages=math.ceil(total / page_size) if total else 0)

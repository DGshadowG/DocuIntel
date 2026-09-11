"""Audit trail helper."""
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    entity_type: str = "",
    entity_id: Optional[int] = None,
    detail: str = "",
    ip_address: str = "",
    commit: bool = True,
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail[:1000],
            ip_address=ip_address[:45],
        )
    )
    if commit:
        db.commit()

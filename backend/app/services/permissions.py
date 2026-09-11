"""Repository access control: owner / member / admin rules in one place."""
from typing import List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import Repository, RepositoryMember, User


def accessible_repository_ids(db: Session, user: User) -> List[int]:
    """IDs of repositories the user can read (admin sees all)."""
    if user.role == "admin":
        return [r.id for r in db.query(Repository.id).all()]
    rows = (
        db.query(Repository.id)
        .outerjoin(RepositoryMember, RepositoryMember.repository_id == Repository.id)
        .filter(or_(Repository.owner_id == user.id, RepositoryMember.user_id == user.id))
        .distinct()
        .all()
    )
    return [r.id for r in rows]


def get_repository_or_403(db: Session, repository_id: int, user: User, write: bool = False) -> Repository:
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise AppError(404, "not_found", "El repositorio no existe")
    if user.role == "admin":
        return repo
    if repo.owner_id == user.id:
        return repo
    membership = (
        db.query(RepositoryMember)
        .filter_by(repository_id=repository_id, user_id=user.id)
        .first()
    )
    if membership is None:
        raise AppError(403, "forbidden", "No tiene acceso a este repositorio")
    if write and membership.role not in ("owner", "member"):
        raise AppError(403, "forbidden", "No tiene permisos de escritura en este repositorio")
    return repo


def require_owner_or_admin(db: Session, repo: Repository, user: User) -> None:
    if user.role != "admin" and repo.owner_id != user.id:
        raise AppError(403, "forbidden", "Solo el propietario o un administrador puede realizar esta accion")

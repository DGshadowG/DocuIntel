"""Repository CRUD, members and statistics."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models import Classification, Document, Repository, RepositoryMember, User
from app.schemas.api import (
    MemberAdd,
    MemberOut,
    RepositoryCreate,
    RepositoryOut,
    RepositoryStats,
    RepositoryUpdate,
)
from app.services import audit
from app.services.permissions import (
    accessible_repository_ids,
    get_repository_or_403,
    require_owner_or_admin,
)
from app.services.storage import get_storage

router = APIRouter(prefix="/repositories", tags=["Repositorios"])


def _to_out(db: Session, repo: Repository) -> RepositoryOut:
    count = db.query(func.count(Document.id)).filter(Document.repository_id == repo.id).scalar() or 0
    out = RepositoryOut.model_validate(repo)
    out.document_count = count
    out.owner_name = repo.owner.full_name if repo.owner else ""
    return out


@router.get("", response_model=list[RepositoryOut], summary="Listar repositorios accesibles")
def list_repositories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ids = accessible_repository_ids(db, user)
    repos = db.query(Repository).filter(Repository.id.in_(ids)).order_by(Repository.created_at.desc()).all() if ids else []
    return [_to_out(db, r) for r in repos]


@router.post("", response_model=RepositoryOut, status_code=201, summary="Crear repositorio")
def create_repository(
    payload: RepositoryCreate, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    repo = Repository(name=payload.name.strip(), description=payload.description.strip(), owner_id=user.id)
    db.add(repo)
    db.flush()
    db.add(RepositoryMember(repository_id=repo.id, user_id=user.id, role="owner"))
    db.commit()
    db.refresh(repo)
    audit.record(db, "create_repository", user_id=user.id, entity_type="repository",
                 entity_id=repo.id, detail=repo.name, ip_address=client_ip(request))
    return _to_out(db, repo)


@router.get("/{repository_id}", response_model=RepositoryOut, summary="Consultar repositorio")
def get_repository(
    repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    repo = get_repository_or_403(db, repository_id, user)
    return _to_out(db, repo)


@router.patch("/{repository_id}", response_model=RepositoryOut, summary="Editar repositorio")
def update_repository(
    repository_id: int, payload: RepositoryUpdate, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    repo = get_repository_or_403(db, repository_id, user)
    require_owner_or_admin(db, repo, user)
    if payload.name is not None:
        repo.name = payload.name.strip()
    if payload.description is not None:
        repo.description = payload.description.strip()
    db.commit()
    db.refresh(repo)
    audit.record(db, "update_repository", user_id=user.id, entity_type="repository",
                 entity_id=repo.id, ip_address=client_ip(request))
    return _to_out(db, repo)


@router.delete("/{repository_id}", status_code=204, summary="Eliminar repositorio")
def delete_repository(
    repository_id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    repo = get_repository_or_403(db, repository_id, user)
    require_owner_or_admin(db, repo, user)
    # Remove physical files first, then cascade-delete rows
    storage = get_storage()
    for doc in db.query(Document).filter(Document.repository_id == repo.id).all():
        try:
            storage.delete(doc.storage_key)
        except Exception:
            pass  # DB cleanup proceeds; orphan files are handled by maintenance script
    name = repo.name
    db.delete(repo)
    db.commit()
    audit.record(db, "delete_repository", user_id=user.id, entity_type="repository",
                 entity_id=repository_id, detail=name, ip_address=client_ip(request))
    return None


@router.get("/{repository_id}/stats", response_model=RepositoryStats, summary="Estadisticas del repositorio")
def repository_stats(
    repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_repository_or_403(db, repository_id, user)
    doc_filter = Document.repository_id == repository_id
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
    return RepositoryStats(
        document_count=db.query(func.count(Document.id)).filter(doc_filter).scalar() or 0,
        by_status=by_status,
        by_category=by_category,
        by_format=by_format,
        total_size_bytes=db.query(func.coalesce(func.sum(Document.size_bytes), 0)).filter(doc_filter).scalar(),
    )


@router.get("/{repository_id}/members", response_model=list[MemberOut], summary="Listar miembros")
def list_members(
    repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_repository_or_403(db, repository_id, user)
    members = (
        db.query(RepositoryMember).filter(RepositoryMember.repository_id == repository_id).all()
    )
    return [
        MemberOut(id=m.id, user_id=m.user_id, email=m.user.email, full_name=m.user.full_name, role=m.role)
        for m in members
    ]


@router.post("/{repository_id}/members", response_model=MemberOut, status_code=201, summary="Agregar miembro")
def add_member(
    repository_id: int, payload: MemberAdd, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    repo = get_repository_or_403(db, repository_id, user)
    require_owner_or_admin(db, repo, user)
    target = db.query(User).filter(User.email == payload.email.lower()).first()
    if target is None:
        raise AppError(404, "not_found", "No existe un usuario con ese correo")
    existing = (
        db.query(RepositoryMember)
        .filter_by(repository_id=repository_id, user_id=target.id)
        .first()
    )
    if existing:
        raise AppError(409, "duplicate_member", "El usuario ya es miembro del repositorio")
    member = RepositoryMember(repository_id=repository_id, user_id=target.id, role=payload.role)
    db.add(member)
    db.commit()
    db.refresh(member)
    audit.record(db, "add_member", user_id=user.id, entity_type="repository",
                 entity_id=repository_id, detail=target.email, ip_address=client_ip(request))
    return MemberOut(id=member.id, user_id=target.id, email=target.email,
                     full_name=target.full_name, role=member.role)


@router.delete("/{repository_id}/members/{member_id}", status_code=204, summary="Quitar miembro")
def remove_member(
    repository_id: int, member_id: int, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    repo = get_repository_or_403(db, repository_id, user)
    require_owner_or_admin(db, repo, user)
    member = db.get(RepositoryMember, member_id)
    if member is None or member.repository_id != repository_id:
        raise AppError(404, "not_found", "El miembro no existe en este repositorio")
    if member.user_id == repo.owner_id:
        raise AppError(400, "invalid_operation", "No se puede quitar al propietario del repositorio")
    db.delete(member)
    db.commit()
    audit.record(db, "remove_member", user_id=user.id, entity_type="repository",
                 entity_id=repository_id, ip_address=client_ip(request))
    return None

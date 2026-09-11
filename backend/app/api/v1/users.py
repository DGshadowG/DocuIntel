"""User administration (admin only, except profile reads)."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, require_admin
from app.core.errors import AppError
from app.core.security import hash_password
from app.db.session import get_db
from app.models import User
from app.schemas.api import UserCreate, UserOut, UserUpdate
from app.services import audit

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("", response_model=list[UserOut], summary="Listar usuarios (admin)")
def list_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=201, summary="Crear usuario (admin)")
def create_user(
    payload: UserCreate, request: Request,
    db: Session = Depends(get_db), admin: User = Depends(require_admin),
):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise AppError(409, "duplicate_email", "Ya existe un usuario con ese correo")
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.record(db, "create_user", user_id=admin.id, entity_type="user",
                 entity_id=user.id, ip_address=client_ip(request))
    return user


@router.patch("/{user_id}", response_model=UserOut, summary="Actualizar usuario (admin)")
def update_user(
    user_id: int, payload: UserUpdate, request: Request,
    db: Session = Depends(get_db), admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "not_found", "El usuario no existe")
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        if user.id == admin.id and payload.is_active is False:
            raise AppError(400, "invalid_operation", "No puede desactivar su propia cuenta")
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    audit.record(db, "update_user", user_id=admin.id, entity_type="user",
                 entity_id=user.id, ip_address=client_ip(request))
    return user

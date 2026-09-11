"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_current_user
from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas.api import LoginRequest, TokenResponse, UserOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesion")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        audit.record(db, "login_failed", detail=f"email={payload.email}", ip_address=client_ip(request))
        raise AppError(401, "invalid_credentials", "Correo o contrasena incorrectos")
    if not user.is_active:
        raise AppError(403, "inactive_user", "El usuario esta inactivo")
    token = create_access_token(subject=str(user.id), role=user.role)
    audit.record(db, "login", user_id=user.id, ip_address=client_ip(request))
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout", summary="Cerrar sesion")
def logout(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # JWT is stateless: the client discards the token. We record the event for audit.
    audit.record(db, "logout", user_id=user.id, ip_address=client_ip(request))
    return {"detail": "Sesion cerrada correctamente"}


@router.get("/me", response_model=UserOut, summary="Usuario actual")
def me(user: User = Depends(get_current_user)):
    return user

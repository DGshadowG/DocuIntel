"""FastAPI dependencies: current user resolution and role guards."""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(401, "unauthorized", "Se requiere autenticacion")
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise AppError(401, "unauthorized", "Token invalido o expirado")
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AppError(401, "unauthorized", "Usuario inexistente o inactivo")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(403, "forbidden", "Se requiere rol de administrador")
    return user


def client_ip(request: Request) -> str:
    return request.client.host if request.client else ""

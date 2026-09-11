"""Dashboard indicators endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.services.dashboard import build_dashboard
from app.services.permissions import accessible_repository_ids

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", summary="Indicadores del dashboard (segun repositorios accesibles)")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo_ids = accessible_repository_ids(db, user)
    return build_dashboard(db, repo_ids)

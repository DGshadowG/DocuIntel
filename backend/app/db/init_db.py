"""Reproducible seed: admin + standard user + demo repository.

Run:  python -m app.db.init_db
Idempotent — running it twice does not duplicate data. Credentials come from
SEED_* variables in .env (never hardcoded in application code).
"""
import logging

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Repository, RepositoryMember, User

logger = logging.getLogger("app.seed")


def ensure_user(db: Session, email: str, full_name: str, password: str, role: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if user is None:
        user = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[seed] Usuario creado: {email} (rol {role})")
    else:
        print(f"[seed] Usuario ya existe: {email}")
    return user


def ensure_repository(db: Session, name: str, description: str, owner: User) -> Repository:
    repo = db.query(Repository).filter(Repository.name == name, Repository.owner_id == owner.id).first()
    if repo is None:
        repo = Repository(name=name, description=description, owner_id=owner.id)
        db.add(repo)
        db.flush()
        db.add(RepositoryMember(repository_id=repo.id, user_id=owner.id, role="owner"))
        db.commit()
        db.refresh(repo)
        print(f"[seed] Repositorio creado: {name}")
    else:
        print(f"[seed] Repositorio ya existe: {name}")
    return repo


def seed() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        admin = ensure_user(
            db, settings.SEED_ADMIN_EMAIL, "Administrador del Sistema",
            settings.SEED_ADMIN_PASSWORD, "admin",
        )
        user = ensure_user(
            db, settings.SEED_USER_EMAIL, "Usuario Estandar",
            settings.SEED_USER_PASSWORD, "user",
        )
        repo = ensure_repository(
            db, "Documentos Corporativos",
            "Repositorio de demostracion con facturas, contratos y hojas de vida sinteticas.",
            admin,
        )
        # The standard user is a member of the demo repository
        existing = (
            db.query(RepositoryMember)
            .filter_by(repository_id=repo.id, user_id=user.id)
            .first()
        )
        if existing is None:
            db.add(RepositoryMember(repository_id=repo.id, user_id=user.id, role="member"))
            db.commit()
            print("[seed] Usuario estandar agregado como miembro del repositorio demo")
        print("[seed] Seed completado correctamente")
    finally:
        db.close()


if __name__ == "__main__":
    seed()

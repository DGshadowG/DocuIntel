"""Test fixtures: isolated SQLite DB + temp storage + deterministic AI provider.

Each test session gets a fresh database file and storage directory under a
pytest tmp dir, so tests never touch development data and are fully repeatable.
"""
import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Configure environment BEFORE importing app modules (settings are cached).
_TMP = Path(os.environ.get("PYTEST_TMP", "")) if os.environ.get("PYTEST_TMP") else None


@pytest.fixture(scope="session")
def test_env(tmp_path_factory):
    base = tmp_path_factory.mktemp("docuintel")
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = f"sqlite:///{(base / 'test.db').as_posix()}"
    os.environ["STORAGE_DIR"] = str(base / "storage")
    os.environ["AI_PROVIDER"] = "deterministic"
    os.environ["WORKER_EMBEDDED"] = "false"
    os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-not-production"
    os.environ["MAX_UPLOAD_MB"] = "5"
    os.environ["RAG_MIN_SIMILARITY"] = "0.15"

    from app.core.config import get_settings
    get_settings.cache_clear()

    import app.db.session as session_module
    session_module.engine = session_module._build_engine()
    session_module.SessionLocal.configure(bind=session_module.engine)

    from app.ai.factory import reset_provider_cache
    from app.services.storage import reset_storage_cache
    reset_provider_cache()
    reset_storage_cache()

    from app.db.base import Base
    import app.models  # noqa: F401
    Base.metadata.create_all(session_module.engine)
    return base


@pytest.fixture(scope="session")
def client(test_env):
    from fastapi.testclient import TestClient
    from app.main import create_app

    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def db_session(test_env):
    from app.db.session import SessionLocal
    db = SessionLocal()
    yield db
    db.close()


def _ensure_user(email: str, password: str, role: str, full_name: str):
    from app.core.security import hash_password
    from app.db.session import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(email=email, full_name=full_name,
                        password_hash=hash_password(password), role=role)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user.id
    finally:
        db.close()


@pytest.fixture(scope="session")
def admin_token(client, test_env):
    _ensure_user("admin@test-docuintel.co", "AdminTest123!", "admin", "Admin Pruebas")
    resp = client.post("/api/v1/auth/login",
                       json={"email": "admin@test-docuintel.co", "password": "AdminTest123!"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def user_token(client, test_env):
    _ensure_user("user@test-docuintel.co", "UserTest123!", "user", "Usuario Pruebas")
    resp = client.post("/api/v1/auth/login",
                       json={"email": "user@test-docuintel.co", "password": "UserTest123!"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def other_user_token(client, test_env):
    _ensure_user("otro@test-docuintel.co", "OtroTest123!", "user", "Otro Usuario")
    resp = client.post("/api/v1/auth/login",
                       json={"email": "otro@test-docuintel.co", "password": "OtroTest123!"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def make_repo(client, user_token):
    """Factory: create a repository owned by the standard user."""
    created = []

    def _make(name: str):
        resp = client.post("/api/v1/repositories", headers=auth(user_token),
                           json={"name": name, "description": "Repositorio de prueba"})
        assert resp.status_code == 201, resp.text
        repo = resp.json()
        created.append(repo["id"])
        return repo

    yield _make


def run_pending_jobs():
    """Synchronously drain the job queue (worker is disabled in tests)."""
    from app.worker.runner import process_one
    for _ in range(50):
        if not process_one():
            break


# --------------------------------------------------------------- sample files
SAMPLES_DIR = BACKEND_DIR.parent / "sample_documents"


def sample_file(name: str) -> bytes:
    return (SAMPLES_DIR / name).read_bytes()


def make_txt(content: str = "Contenido de prueba para el documento de texto plano. " * 5) -> bytes:
    return content.encode("utf-8")

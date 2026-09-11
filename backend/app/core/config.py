"""Application settings loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository root (backend/app/core/config.py -> 3 levels up = backend, 4 = root)
BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    APP_NAME: str = "Sistema Inteligente de Gestion y Analisis Documental"
    APP_ENV: str = "development"  # development | production | test
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # --- Security ---
    SECRET_KEY: str = "CHANGE_ME_generate_a_long_random_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database ---
    # SQLite by default (fully local dev). For PostgreSQL use e.g.:
    # postgresql+psycopg2://user:pass@localhost:5432/docuintel
    DATABASE_URL: str = f"sqlite:///{(PROJECT_ROOT / 'database' / 'docuintel.db').as_posix()}"

    # --- File storage ---
    STORAGE_BACKEND: str = "local"  # local | s3
    STORAGE_DIR: str = str(PROJECT_ROOT / "storage")
    MAX_UPLOAD_MB: int = 20
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt"

    # --- Worker ---
    WORKER_EMBEDDED: bool = True          # run job worker thread inside the API process
    WORKER_POLL_SECONDS: float = 1.0
    JOB_MAX_ATTEMPTS: int = 3

    # --- AI provider ---
    # deterministic | openai | ollama
    AI_PROVIDER: str = "deterministic"
    AI_CHAT_MODEL: str = "gpt-4o-mini"
    AI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    AI_EMBEDDING_DIM: int = 384
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.1"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    AI_TIMEOUT_SECONDS: float = 60.0

    # --- RAG ---
    CHUNK_SIZE: int = 1200          # characters per chunk
    CHUNK_OVERLAP: int = 200        # characters of overlap
    RAG_TOP_K: int = 6
    RAG_MIN_SIMILARITY: float = 0.15  # below this -> "insufficient evidence"

    # --- Seed admin (used only by the seed script, never hardcoded in app) ---
    SEED_ADMIN_EMAIL: str = "admin@docuintel.co"
    SEED_ADMIN_PASSWORD: str = "Admin123!"
    SEED_USER_EMAIL: str = "usuario@docuintel.co"
    SEED_USER_PASSWORD: str = "Usuario123!"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> List[str]:
        return [e.strip().lower() for e in self.ALLOWED_EXTENSIONS.split(",") if e.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()

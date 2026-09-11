"""File storage abstraction.

`LocalStorage` keeps binaries on disk under STORAGE_DIR using server-generated
UUID keys — the original filename is never used as a path component, which
removes any path-traversal surface. An S3/MinIO adapter can implement the same
interface for production (STORAGE_BACKEND=s3, documented in the deploy manual).
"""
import abc
import uuid
from pathlib import Path

from app.core.config import get_settings


class Storage(abc.ABC):
    @abc.abstractmethod
    def save(self, content: bytes, extension: str) -> str:
        """Persist bytes, return an opaque storage key."""

    @abc.abstractmethod
    def read(self, key: str) -> bytes: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalStorage(Storage):
    def __init__(self, base_dir: str = None):
        self.base = Path(base_dir or get_settings().STORAGE_DIR)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Keys are server-generated (uuid.ext); resolve and confine to base dir.
        path = (self.base / key).resolve()
        if self.base.resolve() not in path.parents:
            raise ValueError("Clave de almacenamiento invalida")
        return path

    def save(self, content: bytes, extension: str) -> str:
        key = f"{uuid.uuid4().hex}.{extension.lower().lstrip('.')}"
        self._path(key).write_bytes(content)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


_storage = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        backend = get_settings().STORAGE_BACKEND
        if backend == "local":
            _storage = LocalStorage()
        else:
            raise ValueError(
                f"STORAGE_BACKEND='{backend}' no implementado en este despliegue. Use 'local'."
            )
    return _storage


def reset_storage_cache() -> None:
    global _storage
    _storage = None

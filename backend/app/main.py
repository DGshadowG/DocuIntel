"""FastAPI application entry point."""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import audit as audit_router
from app.api.v1 import auth, chat, dashboard, documents, repositories, search, users
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, correlation_id_var, new_correlation_id

logger = logging.getLogger("app.http")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging("DEBUG" if settings.DEBUG else "INFO")
    if settings.WORKER_EMBEDDED and settings.APP_ENV != "test":
        from app.worker.runner import start_embedded_worker, stop_embedded_worker

        start_embedded_worker()
        yield
        stop_embedded_worker()
    else:
        yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "API del Sistema Inteligente de Gestion y Analisis Documental. "
            "Gestiona repositorios y documentos (PDF, DOCX, TXT), los procesa con IA "
            "(clasificacion, resumen, extraccion estructurada, embeddings) y permite "
            "busqueda textual/semantica y consulta RAG con citas."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id") or new_correlation_id()
        correlation_id_var.set(correlation_id)
        started = time.monotonic()
        response = await call_next(request)
        latency_ms = int((time.monotonic() - started) * 1000)
        response.headers["X-Correlation-Id"] = correlation_id
        if request.url.path.startswith("/api"):
            logger.info(
                "%s %s -> %s", request.method, request.url.path, response.status_code,
                extra={"event": "http_request", "method": request.method, "path": request.url.path,
                       "status_code": response.status_code, "latency_ms": latency_ms},
            )
        return response

    register_exception_handlers(app)

    prefix = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(repositories.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(dashboard.router, prefix=prefix)
    app.include_router(audit_router.router, prefix=prefix)

    @app.get("/health", tags=["Salud"], summary="Health check")
    def health():
        from sqlalchemy import text

        from app.db.session import engine

        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            db_ok = False
        return {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "ai_provider": settings.AI_PROVIDER,
            "version": "1.0.0",
        }

    return app


app = create_app()

"""Job worker.

A database-backed queue (`processing_jobs`) polled by a worker loop. Two modes:
- Embedded thread inside the API process (WORKER_EMBEDDED=true, default) —
  zero extra infrastructure, ideal for development and small deployments.
- Standalone process: `python -m app.worker.runner` — for production, where it
  can be scaled independently (see ADR-004; Celery/Redis was rejected because
  the target environment has no Redis available and this queue is transactional
  with the rest of the data).
"""
import logging
import threading
import time

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import ProcessingJob
from app.services.pipeline import execute_job

logger = logging.getLogger("app.worker")

_stop_event = threading.Event()
_thread = None


def claim_next_job_id():
    """Atomically claim the oldest queued job (mark it running)."""
    db = SessionLocal()
    try:
        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.status == "queued")
            .order_by(ProcessingJob.created_at.asc(), ProcessingJob.id.asc())
            .first()
        )
        if job is None:
            return None
        return job.id
    finally:
        db.close()


def process_one() -> bool:
    """Process a single queued job if any. Returns True if a job ran."""
    job_id = claim_next_job_id()
    if job_id is None:
        return False
    db = SessionLocal()
    try:
        execute_job(db, job_id)
        return True
    finally:
        db.close()


def worker_loop(poll_seconds: float = None, stop_event: threading.Event = None) -> None:
    settings = get_settings()
    poll = poll_seconds or settings.WORKER_POLL_SECONDS
    stop = stop_event or _stop_event
    logger.info("Worker de procesamiento iniciado", extra={"event": "worker_started"})
    while not stop.is_set():
        try:
            ran = process_one()
        except Exception:
            logger.exception("Error no controlado en el worker")
            ran = False
        if not ran:
            stop.wait(poll)
    logger.info("Worker de procesamiento detenido", extra={"event": "worker_stopped"})


def start_embedded_worker() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()
    _thread = threading.Thread(target=worker_loop, name="pipeline-worker", daemon=True)
    _thread.start()


def stop_embedded_worker() -> None:
    _stop_event.set()
    if _thread:
        _thread.join(timeout=5)


if __name__ == "__main__":
    from app.core.logging import configure_logging

    configure_logging()
    worker_loop()

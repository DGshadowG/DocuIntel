"""RAG (Retrieval-Augmented Generation) service.

Flow: embed question -> filter chunks by user-accessible repository ->
top-K cosine retrieval -> build labeled context blocks -> provider answers
using ONLY that context -> persist message + citations + metrics.
"""
import logging
import time
from typing import List, Optional

from sqlalchemy.orm import Session

from app.ai.base import AIProviderError
from app.ai.factory import get_provider
from app.core.config import get_settings
from app.models import Citation, Conversation, Message
from app.services import vectors

logger = logging.getLogger("app.rag")


def ask(
    db: Session,
    conversation: Conversation,
    question: str,
    repository_ids: List[int],
    document_ids: Optional[List[int]] = None,
) -> Message:
    """Answer a question over the conversation's repository. Persists both the
    user message and the assistant message (with citations) and returns the
    assistant message."""
    settings = get_settings()
    provider = get_provider()
    started = time.monotonic()

    db.add(Message(conversation_id=conversation.id, role="user", content=question))
    db.commit()

    try:
        query_vec = provider.embed([question])[0]
        hits = vectors.semantic_search(
            db, query_vec, repository_ids, top_k=settings.RAG_TOP_K, document_ids=document_ids
        )
        relevant = [h for h in hits if h[2] >= settings.RAG_MIN_SIMILARITY]

        if not relevant:
            answer_text = (
                "No se encontro evidencia suficiente en los documentos para responder esta pregunta."
            )
            grounded = False
            citations_data = []
        else:
            blocks = []
            citations_data = []
            for i, (chunk, document, similarity) in enumerate(relevant, start=1):
                blocks.append(
                    f"[Fuente {i}] {document.original_filename} (pag. {chunk.page_number}):\n{chunk.content}"
                )
                citations_data.append((chunk, document, similarity))
            result = provider.rag_answer(question, blocks)
            answer_text = result.answer
            grounded = result.grounded
            if not grounded:
                citations_data = []
    except AIProviderError as exc:
        logger.warning("Fallo del proveedor de IA en RAG: %s", exc, extra={"event": "rag_provider_error"})
        raise

    latency_ms = int((time.monotonic() - started) * 1000)
    assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer_text,
        model=provider.chat_model_name,
        latency_ms=latency_ms,
        chunk_count=len(citations_data),
        grounded=grounded,
    )
    db.add(assistant)
    db.flush()
    for chunk, document, similarity in citations_data:
        db.add(
            Citation(
                message_id=assistant.id,
                document_id=document.id,
                chunk_id=chunk.id,
                snippet=chunk.content[:400],
                similarity=round(similarity, 4),
                page_number=chunk.page_number,
            )
        )
    conversation.updated_at = assistant.created_at
    db.commit()
    db.refresh(assistant)
    logger.info(
        "Pregunta RAG respondida",
        extra={"event": "rag_answer", "latency_ms": latency_ms},
    )
    return assistant

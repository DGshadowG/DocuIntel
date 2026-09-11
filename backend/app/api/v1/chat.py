"""Conversations and RAG question answering."""
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.ai.base import AIProviderError
from app.api.deps import client_ip, get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models import Citation, Conversation, Message, User
from app.schemas.api import (
    AskRequest,
    CitationOut,
    ConversationCreate,
    ConversationDetail,
    ConversationOut,
    MessageOut,
)
from app.services import audit, rag
from app.services.permissions import get_repository_or_403

router = APIRouter(prefix="/conversations", tags=["Consulta documental (RAG)"])


def _message_out(db: Session, message: Message) -> MessageOut:
    out = MessageOut.model_validate(message)
    citations = (
        db.query(Citation).options(joinedload(Citation.document))
        .filter(Citation.message_id == message.id).all()
    )
    out.citations = []
    for c in citations:
        citation = CitationOut.model_validate(c)
        citation.document_name = c.document.original_filename if c.document else ""
        out.citations.append(citation)
    return out


def _get_conversation_or_403(db: Session, conversation_id: int, user: User) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        raise AppError(404, "not_found", "La conversacion no existe")
    if conv.user_id != user.id and user.role != "admin":
        raise AppError(403, "forbidden", "No tiene acceso a esta conversacion")
    get_repository_or_403(db, conv.repository_id, user)
    return conv


@router.get("", response_model=List[ConversationOut], summary="Listar mis conversaciones")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.post("", response_model=ConversationOut, status_code=201, summary="Crear conversacion")
def create_conversation(
    payload: ConversationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    get_repository_or_403(db, payload.repository_id, user)
    conv = Conversation(
        repository_id=payload.repository_id,
        user_id=user.id,
        title=(payload.title or "Nueva conversacion").strip(),
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/{conversation_id}", response_model=ConversationDetail, summary="Historial de la conversacion")
def get_conversation(
    conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    conv = _get_conversation_or_403(db, conversation_id, user)
    detail = ConversationDetail.model_validate(conv)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    detail.messages = [_message_out(db, m) for m in messages]
    return detail


@router.delete("/{conversation_id}", status_code=204, summary="Eliminar conversacion")
def delete_conversation(
    conversation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    conv = _get_conversation_or_403(db, conversation_id, user)
    db.delete(conv)
    db.commit()
    return None


@router.post("/{conversation_id}/ask", response_model=MessageOut,
             summary="Preguntar sobre los documentos del repositorio")
def ask_question(
    conversation_id: int, payload: AskRequest, request: Request,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    conv = _get_conversation_or_403(db, conversation_id, user)
    try:
        assistant = rag.ask(db, conv, payload.question.strip(), [conv.repository_id])
    except AIProviderError as exc:
        raise AppError(503, "ai_unavailable", f"El proveedor de IA no esta disponible: {exc}")
    # First question becomes the conversation title
    if conv.title == "Nueva conversacion":
        conv.title = payload.question.strip()[:200]
        db.commit()
    audit.record(db, "rag_question", user_id=user.id, entity_type="conversation",
                 entity_id=conv.id, ip_address=client_ip(request))
    return _message_out(db, assistant)
